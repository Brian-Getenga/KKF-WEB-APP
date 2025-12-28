from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from decimal import Decimal
import requests
import base64
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import (
    Product, Cart, CartItem, Order, OrderItem, Category,
    ProductReview, Wishlist, Coupon, ShippingZone, PaymentTransaction
)
from .forms import CheckoutForm, ReviewForm


# ============================================================================
# PRODUCT VIEWS
# ============================================================================

class ProductListView(ListView):
    model = Product
    template_name = "store/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category')
        
        # Search
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(brand__icontains=query)
            )
        
        # Category filter
        category_slug = self.request.GET.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Price range filter
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Sorting
        sort = self.request.GET.get("sort", "-created_at")
        valid_sorts = {
            'price_low': 'price',
            'price_high': '-price',
            'name': 'name',
            'newest': '-created_at',
            'popular': '-sales_count',
        }
        queryset = queryset.order_by(valid_sorts.get(sort, '-created_at'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['current_category'] = self.request.GET.get('category')
        context['current_sort'] = self.request.GET.get('sort', 'newest')
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "store/product_detail.html"
    context_object_name = "product"

    def get_object(self):
        product = super().get_object()
        product.increment_views()
        return product

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Related products
        context['related_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(pk=product.pk)[:4]
        
        # Reviews
        context['reviews'] = product.reviews.all()[:10]
        context['review_form'] = ReviewForm()
        
        # Check if user has purchased
        if self.request.user.is_authenticated:
            context['has_purchased'] = Order.objects.filter(
                user=self.request.user,
                items__product=product,
                status__in=['paid', 'processing', 'shipped', 'delivered']
            ).exists()
            
            # Check if in wishlist
            context['in_wishlist'] = Wishlist.objects.filter(
                user=self.request.user,
                product=product
            ).exists()
        
        return context


@login_required
@require_POST
def add_review(request, pk):
    """Add a product review"""
    product = get_object_or_404(Product, pk=pk)
    
    # Check if user has purchased
    has_purchased = Order.objects.filter(
        user=request.user,
        items__product=product,
        status__in=['paid', 'processing', 'shipped', 'delivered']
    ).exists()
    
    if not has_purchased:
        messages.error(request, "You can only review products you've purchased.")
        return redirect('store:product_detail', slug=product.slug)
    
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.is_verified_purchase = True
        review.save()
        messages.success(request, "Review added successfully!")
    else:
        messages.error(request, "Error adding review.")
    
    return redirect('store:product_detail', slug=product.slug)


# ============================================================================
# CART VIEWS
# ============================================================================

class CartView(View):
    def get(self, request):
        cart = self.get_or_create_cart(request)
        
        # Validate cart items stock
        for item in cart.items.all():
            if item.quantity > item.product.stock:
                messages.warning(request, f"{item.product.name} has limited stock. Updated quantity.")
                item.quantity = item.product.stock
                item.save()
        
        # Apply coupon if in session
        coupon_code = request.session.get('coupon_code')
        discount_amount = 0
        coupon = None
        
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                is_valid, message = coupon.is_valid()
                if is_valid:
                    discount_amount = coupon.calculate_discount(cart.total_price)
                else:
                    del request.session['coupon_code']
                    messages.warning(request, message)
            except Coupon.DoesNotExist:
                del request.session['coupon_code']
        
        context = {
            'cart': cart,
            'coupon': coupon,
            'discount_amount': discount_amount,
            'final_total': cart.total_price - discount_amount,
        }
        return render(request, "store/cart.html", context)

    def get_or_create_cart(self, request):
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            # Merge session cart if exists
            session_key = request.session.session_key
            if session_key:
                try:
                    session_cart = Cart.objects.get(session_key=session_key)
                    for item in session_cart.items.all():
                        cart_item, created = CartItem.objects.get_or_create(
                            cart=cart,
                            product=item.product,
                            defaults={'quantity': item.quantity}
                        )
                        if not created:
                            cart_item.quantity += item.quantity
                            cart_item.save()
                    session_cart.delete()
                except Cart.DoesNotExist:
                    pass
        else:
            session_key = request.session.session_key or request.session.create()
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
        return cart


@require_POST
def add_to_cart(request, pk):
    """Add product to cart via AJAX"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    if not product.is_in_stock:
        return JsonResponse({
            'success': False,
            'message': 'Product is out of stock'
        })
    
    quantity = int(request.POST.get('quantity', 1))
    
    cart_view = CartView()
    cart = cart_view.get_or_create_cart(request)
    
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        new_quantity = item.quantity + quantity
        if new_quantity > product.stock:
            return JsonResponse({
                'success': False,
                'message': f'Only {product.stock} items available'
            })
        item.quantity = new_quantity
        item.save()
    
    return JsonResponse({
        'success': True,
        'message': f'{product.name} added to cart',
        'cart_count': cart.total_items
    })


@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_view = CartView()
    cart = cart_view.get_or_create_cart(request)
    
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > item.product.stock:
        return JsonResponse({
            'success': False,
            'message': f'Only {item.product.stock} items available'
        })
    
    if quantity > 0:
        item.quantity = quantity
        item.save()
    else:
        item.delete()
    
    return JsonResponse({
        'success': True,
        'cart_total': float(cart.total_price),
        'item_total': float(item.total_price) if quantity > 0 else 0
    })


@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_view = CartView()
    cart = cart_view.get_or_create_cart(request)
    
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = item.product.name
    item.delete()
    
    messages.success(request, f'{product_name} removed from cart')
    return redirect('store:cart')


@require_POST
def apply_coupon(request):
    """Apply coupon code"""
    code = request.POST.get('coupon_code', '').strip().upper()
    
    try:
        coupon = Coupon.objects.get(code=code)
        is_valid, message = coupon.is_valid()
        
        if is_valid:
            cart_view = CartView()
            cart = cart_view.get_or_create_cart(request)
            
            if cart.total_price < coupon.min_purchase_amount:
                messages.error(request, f'Minimum purchase of KES {coupon.min_purchase_amount} required')
            else:
                request.session['coupon_code'] = code
                discount = coupon.calculate_discount(cart.total_price)
                messages.success(request, f'Coupon applied! You saved KES {discount}')
        else:
            messages.error(request, message)
    except Coupon.DoesNotExist:
        messages.error(request, 'Invalid coupon code')
    
    return redirect('store:cart')


def remove_coupon(request):
    """Remove applied coupon"""
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
        messages.success(request, 'Coupon removed')
    return redirect('store:cart')




def send_order_confirmation_email(order):
    """Send a confirmation email with order details."""
    subject = f"Order Confirmation - #{order.order_number}"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [order.shipping_email]

    # Render your email HTML template
    message = render_to_string('store/emails/order_confirmation.html', {
        'order': order,
        'items': order.items.all(),
    })

    # Send email (HTML + plain text fallback)
    send_mail(
        subject,
        '',
        from_email,
        recipient_list,
        html_message=message,
        fail_silently=False,
    )


# ============================================================================
# CHECKOUT & ORDER VIEWS - ENHANCED WITH SECURITY
# ============================================================================

class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        cart_view = CartView()
        cart = cart_view.get_or_create_cart(request)
        
        if not cart.items.exists():
            messages.warning(request, 'Your cart is empty')
            return redirect('store:cart')
        
        # Check stock availability
        for item in cart.items.all():
            if not item.product.is_active:
                messages.error(request, f'{item.product.name} is no longer available')
                return redirect('store:cart')
            if item.quantity > item.product.stock:
                messages.error(request, f'{item.product.name} has insufficient stock')
                return redirect('store:cart')
        
        # Calculate totals
        subtotal = cart.total_price
        discount_amount = Decimal('0')
        
        coupon_code = request.session.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                is_valid, _ = coupon.is_valid()
                if is_valid:
                    discount_amount = coupon.calculate_discount(subtotal)
            except Coupon.DoesNotExist:
                pass
        
        # Shipping
        shipping_zones = ShippingZone.objects.filter(is_active=True)
        shipping_cost = shipping_zones.first().shipping_cost if shipping_zones.exists() else Decimal('0')
        
        total = subtotal - discount_amount 
        
        # Pre-fill form with user data
        initial_data = {
            'shipping_name': request.user.get_full_name(),
            'shipping_email': request.user.email,
            'shipping_phone': getattr(request.user, 'phone', ''),
        }
        
        form = CheckoutForm(initial=initial_data)
        
        context = {
            'cart': cart,
            'form': form,
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'shipping_cost': shipping_cost,
            'total': total,
            'shipping_zones': shipping_zones,
        }
        return render(request, 'store/checkout.html', context)

    @transaction.atomic
    def post(self, request):
        cart_view = CartView()
        cart = cart_view.get_or_create_cart(request)
        
        if not cart.items.exists():
            messages.error(request, 'Your cart is empty')
            return redirect('store:cart')
        
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Validate stock again
            for item in cart.items.all():
                if item.quantity > item.product.stock:
                    messages.error(request, f'{item.product.name} has insufficient stock')
                    return redirect('store:cart')
            
            # Calculate totals
            subtotal = cart.total_price
            discount_amount = Decimal('0')
            
            coupon_code = request.session.get('coupon_code')
            coupon = None
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    is_valid, _ = coupon.is_valid()
                    if is_valid:
                        discount_amount = coupon.calculate_discount(subtotal)
                except Coupon.DoesNotExist:
                    pass
            
            shipping_cost = Decimal(request.POST.get('shipping_cost', '0'))
            total = subtotal - discount_amount 
            
            # Create order with pending status
            order = Order.objects.create(
                user=request.user,
                subtotal=subtotal,
                discount_amount=discount_amount,
                shipping_cost=shipping_cost,
                total_price=total,
                payment_method=form.cleaned_data['payment_method'],
                shipping_name=form.cleaned_data['shipping_name'],
                shipping_email=form.cleaned_data['shipping_email'],
                shipping_phone=form.cleaned_data['shipping_phone'],
                shipping_address=form.cleaned_data['shipping_address'],
                shipping_city=form.cleaned_data['shipping_city'],
                shipping_postal_code=form.cleaned_data.get('shipping_postal_code', ''),
                delivery_notes=form.cleaned_data.get('delivery_notes', ''),
                mpesa_phone_number=form.cleaned_data.get('mpesa_phone', ''),
                status='pending',  # Order starts as pending
                payment_status='unpaid'
            )
            
            # Create order items (reserve inventory)
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price
                )
            
            # Update coupon usage
            if coupon:
                coupon.used_count += 1
                coupon.save()
                del request.session['coupon_code']
            
            # Initiate payment based on method
            if order.payment_method == 'mpesa':
                success, message = initiate_mpesa_payment(order)
                if success:
                    messages.success(request, 'STK Push sent! Please enter your M-Pesa PIN on your phone.')
                    # Don't clear cart yet - wait for payment confirmation
                    return redirect('store:payment_pending', pk=order.pk)
                else:
                    messages.error(request, f'Payment initiation failed: {message}')
                    order.status = 'cancelled'
                    order.save()
                    return redirect('store:checkout')
            
            elif order.payment_method == 'card':
                # Redirect to card payment gateway
                return redirect('store:card_payment', pk=order.pk)
            
            elif order.payment_method == 'cash':
                # Cash on delivery - order is confirmed but payment pending
                order.status = 'confirmed'
                order.save()
                cart.items.all().delete()
                send_order_confirmation_email(order)
                return redirect('store:order_confirmation', pk=order.pk)
        
        messages.error(request, 'Please correct the errors in the form')
        return redirect('store:checkout')


def initiate_mpesa_payment(order):
    """Initiate M-Pesa STK Push with enhanced security"""
    
    # M-Pesa credentials from settings
    MPESA_CONSUMER_KEY = getattr(settings, 'MPESA_CONSUMER_KEY', '')
    MPESA_CONSUMER_SECRET = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
    MPESA_SHORTCODE = getattr(settings, 'MPESA_SHORTCODE', '')
    MPESA_PASSKEY = getattr(settings, 'MPESA_PASSKEY', '')
    MPESA_CALLBACK_URL = getattr(settings, 'PESA_CALLBACK_URL', '')
    MPESA_ENVIRONMENT = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
    
    if not all([MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET, MPESA_SHORTCODE, MPESA_PASSKEY]):
        return False, 'M-Pesa configuration incomplete'
    
    # Determine API URLs
    if MPESA_ENVIRONMENT == 'production':
        auth_url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        stk_url = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    else:
        auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        stk_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    
    try:
        # Get access token
        auth_response = requests.get(
            auth_url,
            auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET),
            timeout=120
        )
        auth_response.raise_for_status()
        access_token = auth_response.json().get('access_token')
        
        if not access_token:
            return False, 'Failed to get access token'
        
        # Generate password
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f'{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}'
        password = base64.b64encode(password_str.encode()).decode('utf-8')
        
        # Format phone number
        phone = order.mpesa_phone_number
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        
        # STK Push request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': MPESA_SHORTCODE,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(order.total_price),
            'PartyA': phone,
            'PartyB': MPESA_SHORTCODE,
            'PhoneNumber': phone,
            'CallBackURL': MPESA_CALLBACK_URL,
            'AccountReference': order.order_number,
            'TransactionDesc': f'Payment for Order {order.order_number}'
        }
        
        response = requests.post(stk_url, json=payload, headers=headers, timeout=120)
        result = response.json()
        
        if result.get('ResponseCode') == '0':
            # Create payment transaction record
            PaymentTransaction.objects.create(
                order=order,
                transaction_type='mpesa',
                amount=order.total_price,
                phone_number=phone,
                checkout_request_id=result.get('CheckoutRequestID'),
                merchant_request_id=result.get('MerchantRequestID'),
                status='pending'
            )
            
            order.mpesa_checkout_request_id = result.get('CheckoutRequestID')
            order.save()
            return True, 'Success'
        else:
            return False, result.get('ResponseDescription', 'Unknown error')
            
    except requests.exceptions.Timeout:
        return False, 'Request timed out. Please try again.'
    except requests.exceptions.RequestException as e:
        return False, f'Network error: {str(e)}'
    except Exception as e:
        return False, f'Error: {str(e)}'


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """Handle M-Pesa callback with security verification"""
    try:
        # Verify callback source (optional - implement IP whitelisting)
        # allowed_ips = ['196.201.214.200', '196.201.214.206']  # Safaricom IPs
        # if request.META.get('REMOTE_ADDR') not in allowed_ips:
        #     return HttpResponse('Unauthorized', status=401)
        
        data = json.loads(request.body)
        result_code = data['Body']['stkCallback']['ResultCode']
        checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']
        
        # Find transaction
        transaction = PaymentTransaction.objects.filter(
            checkout_request_id=checkout_request_id
        ).first()
        
        if not transaction:
            return HttpResponse('Transaction not found', status=404)
        
        order = transaction.order
        
        if result_code == 0:
            # Payment successful
            callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
            mpesa_receipt = next(
                (item['Value'] for item in callback_metadata if item['Name'] == 'MpesaReceiptNumber'),
                None
            )
            amount = next(
                (item['Value'] for item in callback_metadata if item['Name'] == 'Amount'),
                None
            )
            phone = next(
                (item['Value'] for item in callback_metadata if item['Name'] == 'PhoneNumber'),
                None
            )
            
            # Update transaction
            transaction.transaction_id = mpesa_receipt
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.response_data = json.dumps(data)
            transaction.save()
            
            # Mark order as paid
            order.mark_as_paid(transaction_id=mpesa_receipt)
            
            # Clear user's cart
            Cart.objects.filter(user=order.user).first().items.all().delete()
            
            # Send confirmation email
            send_order_confirmation_email(order)
            
        else:
            # Payment failed
            result_desc = data['Body']['stkCallback'].get('ResultDesc', 'Payment failed')
            transaction.status = 'failed'
            transaction.response_data = json.dumps(data)
            transaction.failure_reason = result_desc
            transaction.save()
            
            order.status = 'cancelled'
            order.payment_status = 'failed'
            order.save()
        
        return HttpResponse('OK')
    except Exception as e:
        print(f'M-Pesa callback error: {e}')
        return HttpResponse('Error', status=400)


@login_required
def payment_pending(request, pk):
    """Payment pending page - waiting for M-Pesa confirmation"""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    # Check if payment was already completed
    if order.payment_status == 'paid':
        return redirect('store:order_confirmation', pk=order.pk)
    
    # Check payment timeout (5 minutes)
    if order.created_at < timezone.now() - timedelta(minutes=5):
        if order.payment_status == 'unpaid':
            order.status = 'cancelled'
            order.save()
            messages.error(request, 'Payment timed out. Please try again.')
            return redirect('store:cart')
    
    context = {
        'order': order,
    }
    return render(request, 'store/payment_pending.html', context)


@login_required
def check_payment_status(request, pk):
    """AJAX endpoint to check payment status"""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    return JsonResponse({
        'status': order.payment_status,
        'order_status': order.status,
        'paid': order.payment_status == 'paid'
    })


@login_required
def retry_payment(request, pk):
    """Retry payment for failed order"""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    if order.payment_status == 'paid':
        messages.info(request, 'This order has already been paid.')
        return redirect('store:order_detail', pk=order.pk)
    
    if order.status == 'cancelled':
        messages.error(request, 'This order has been cancelled.')
        return redirect('store:order_list')
    
    # Check if items are still in stock
    for item in order.items.all():
        if item.product and item.quantity > item.product.stock:
            messages.error(request, f'{item.product.name} is no longer in stock.')
            return redirect('store:order_detail', pk=order.pk)
    
    # Retry payment
    if order.payment_method == 'mpesa':
        success, message = initiate_mpesa_payment(order)
        if success:
            messages.success(request, 'Payment request sent! Please check your phone.')
            return redirect('store:payment_pending', pk=order.pk)
        else:
            messages.error(request, f'Payment failed: {message}')
    
    return redirect('store:order_detail', pk=order.pk)


class OrderConfirmationView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/order_confirmation.html'
    context_object_name = 'order'

    def get_queryset(self):
        # Only show confirmed orders (paid or cash on delivery)
        return Order.objects.filter(
            user=self.request.user,
            status__in=['paid', 'confirmed', 'processing', 'shipped', 'delivered']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get payment transaction if exists
        context['transaction'] = PaymentTransaction.objects.filter(
            order=self.object,
            status='completed'
        ).first()
        return context


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'store/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transaction'] = PaymentTransaction.objects.filter(
            order=self.object
        ).first()
        return context


@login_required
@require_POST
def cancel_order(request, pk):
    """Cancel an order - only if payment not completed"""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    if order.payment_status == 'paid':
        messages.error(request, 'Paid orders cannot be cancelled. Please contact support for refunds.')
        return redirect('store:order_detail', pk=pk)
    
    if order.can_cancel:
        order.status = 'cancelled'
        order.save()
        
        # Restore stock only if not paid
        if order.payment_status != 'paid':
            for item in order.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save()
        
        messages.success(request, 'Order cancelled successfully')
    else:
        messages.error(request, 'This order cannot be cancelled')
    
    return redirect('store:order_detail', pk=pk)


@login_required
@require_POST
def delete_order(request, pk):
    """Delete cancelled or failed orders"""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    # Only allow deletion of cancelled or very old pending orders
    if order.status not in ['cancelled'] and order.payment_status not in ['failed']:
        messages.error(request, 'Only cancelled orders can be deleted')
        return redirect('store:order_detail', pk=pk)
    
    order_number = order.order_number
    order.delete()
    messages.success(request, f'Order {order_number} has been deleted')
    return redirect('store:order_detail', pk=pk)


@login_required
def wishlist_view(request):
    """View wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})



@login_required
@require_POST
def toggle_wishlist(request, pk):
    """Add/remove product from wishlist"""
    product = get_object_or_404(Product, pk=pk)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    
    if wishlist_item:
        wishlist_item.delete()
        message = f'{product.name} removed from wishlist'
        in_wishlist = False
    else:
        Wishlist.objects.create(user=request.user, product=product)
        message = f'{product.name} added to wishlist'
        in_wishlist = True
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': message, 'in_wishlist': in_wishlist})
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'store:product_list'))