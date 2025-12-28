"""
apps/classes/views.py - ENHANCED WITH BUG FIXES
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.db import transaction as db_transaction
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import json
import logging
from django.db import transaction
from django.db.models import Sum  # ← ADD THIS LINE

from .models import KarateClass, Booking, ClassSchedule, ClassReview, WaitingList, PaymentLog
from .forms import ClassFilterForm, BookingForm, PaymentForm, ReviewForm
from .payments import process_class_payment, MPesaPayment
from .emails import (
    send_booking_confirmation_email_sync,
    send_payment_confirmation_email_sync,
    send_payment_failed_email_sync
)

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ============================================================================
# CLASS VIEWS
# ============================================================================

class ClassListView(ListView):
    """Display list of all active classes with filtering"""
    model = KarateClass
    template_name = "classes/class_list.html"
    context_object_name = "classes"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            KarateClass.objects.filter(is_active=True)
            .select_related("instructor")
            .prefetch_related("schedules", "reviews")
            .annotate(
                avg_rating=Avg('reviews__rating'),
                review_count=Count('reviews')
            )
        )
        
        # Apply filters
        category = self.request.GET.get("category")
        level = self.request.GET.get("level")
        search = self.request.GET.get("search")
        
        if category:
            queryset = queryset.filter(category=category)
        if level:
            queryset = queryset.filter(level=level)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Sort
        sort_by = self.request.GET.get("sort")
        if sort_by == "price_low":
            queryset = queryset.order_by("price")
        elif sort_by == "price_high":
            queryset = queryset.order_by("-price")
        elif sort_by == "rating":
            queryset = queryset.order_by("-avg_rating")
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = ClassFilterForm(self.request.GET or None)
        return context


class ClassDetailView(DetailView):
    """Display detailed information about a specific class"""
    model = KarateClass
    template_name = "classes/class_detail.html"
    context_object_name = "cls"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        karate_class = self.object
        
        context["schedules"] = karate_class.schedules.filter(
            is_active=True
        ).order_by("day_of_week", "start_time")
        context["instructor"] = karate_class.instructor
        context["form"] = BookingForm(karate_class=karate_class)
        context["reviews"] = karate_class.reviews.select_related('user').order_by('-created_at')[:10]
        context["avg_rating"] = karate_class.reviews.aggregate(Avg('rating'))['rating__avg']
        context["review_count"] = karate_class.reviews.count()
        
        # Check if user has already booked
        if self.request.user.is_authenticated:
            context["user_booking"] = Booking.objects.filter(
                user=self.request.user,
                karate_class=karate_class,
                status__in=['Confirmed', 'Pending']
            ).first()
            
            # Check if user can review
            context["can_review"] = Booking.objects.filter(
                user=self.request.user,
                karate_class=karate_class,
                attended=True
            ).exists() and not ClassReview.objects.filter(
                user=self.request.user,
                karate_class=karate_class
            ).exists()
        
        return context


class ScheduleView(ListView):
    """Display all class schedules organized by day"""
    model = ClassSchedule
    template_name = 'classes/schedule.html'
    context_object_name = 'schedules'
    
    def get_queryset(self):
        return (
            ClassSchedule.objects
            .filter(is_active=True, karate_class__is_active=True)
            .select_related('karate_class', 'karate_class__instructor')
            .order_by('day_of_week', 'start_time')
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Organize schedules by day
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        schedules_by_day = {}
        
        for day in days_order:
            day_schedules = [s for s in context['schedules'] if s.day_of_week == day]
            if day_schedules:
                schedules_by_day[day] = day_schedules
        
        context['schedules_by_day'] = schedules_by_day
        context['total_classes'] = context['schedules'].count()
        
        return context


# ============================================================================
# BOOKING VIEWS
# ============================================================================

@method_decorator(login_required, name="dispatch")
class BookingCreateView(View):
    """Create new booking with payment processing"""
    
    def post(self, request, pk):
        karate_class = get_object_or_404(KarateClass, pk=pk)
        form = BookingForm(request.POST, karate_class=karate_class)
        
        if form.is_valid():
            schedule = form.cleaned_data['schedule']
            booking_type = form.cleaned_data['booking_type']
            phone_number = form.cleaned_data['phone_number']
            
            # Security check: Rate limit bookings (max 3 per 5 minutes)
            recent_bookings = Booking.objects.filter(
                user=request.user,
                booked_at__gte=timezone.now() - timedelta(minutes=5)
            ).count()
            
            if recent_bookings >= 3:
                messages.error(request, "Too many booking attempts. Please wait a few minutes.")
                return redirect("classes:class_detail", slug=karate_class.slug)
            
            # Check for existing active bookings
            existing_booking = Booking.objects.filter(
                user=request.user,
                karate_class=karate_class,
                schedule=schedule,
                status__in=['Confirmed', 'Pending']
            ).first()
            
            if existing_booking:
                messages.error(
                    request,
                    f"You already have an active booking for this class schedule. "
                    f"Booking reference: {existing_booking.booking_reference}"
                )
                return redirect("classes:class_detail", slug=karate_class.slug)
            
            # Check availability for free trials
            if booking_type == 'Free Trial' and karate_class.free_trials_available <= 0:
                messages.error(request, "Sorry, all free trial spots are taken.")
                return redirect("classes:class_detail", slug=karate_class.slug)
            
            # Check if class is full
            if karate_class.is_full:
                WaitingList.objects.get_or_create(
                    user=request.user,
                    karate_class=karate_class,
                    schedule=schedule
                )
                messages.info(
                    request,
                    "Class is full. You've been added to the waiting list "
                    "and will be notified when a spot opens."
                )
                return redirect("classes:class_detail", slug=karate_class.slug)
            
            # Create booking with atomic transaction
            try:
                with db_transaction.atomic():
                    booking = form.save(commit=False)
                    booking.user = request.user
                    booking.karate_class = karate_class
                    booking.status = 'Pending'
                    booking.payment_status = 'Unpaid'
                    booking.amount_paid = karate_class.price if booking_type != 'Free Trial' else 0
                    booking.save()
                    
                    # Log booking creation
                    PaymentLog.objects.create(
                        booking=booking,
                        action='booking_created',
                        status_code='CREATED',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                    )
                    
                    logger.info(f"✓ Booking created: {booking.booking_reference}")
                    
                    # Process payment
                    result = process_class_payment(booking, phone_number)
                    
                    if result['success']:
                        if result.get('is_free_trial'):
                            messages.success(
                                request,
                                "Free trial booked successfully! Check your email for confirmation."
                            )
                            return redirect("classes:booking_success", booking_id=booking.id)
                        else:
                            messages.info(
                                request,
                                "Payment request sent to your phone. Please enter your M-Pesa PIN to complete booking."
                            )
                            return redirect("classes:payment_pending", booking_id=booking.id)
                    else:
                        # Payment initiation failed - cancel booking
                        booking.status = 'Cancelled'
                        booking.payment_status = 'Failed'
                        booking.cancelled_at = timezone.now()
                        booking.notes = f"Payment initiation failed: {result.get('error_code', 'UNKNOWN')}"
                        booking.save()
                        
                        error_msg = result.get('message', 'Payment initiation failed')
                        messages.error(request, f"Booking failed: {error_msg}")
                        return redirect("classes:class_detail", slug=karate_class.slug)
                        
            except Exception as e:
                logger.error(f"Booking creation error: {e}", exc_info=True)
                messages.error(request, "An error occurred. Please try again.")
                return redirect("classes:class_detail", slug=karate_class.slug)
        
        # Form invalid
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        
        return redirect("classes:class_detail", slug=karate_class.slug)


@login_required
def payment_pending_view(request, booking_id):
    """Display payment pending page with auto-refresh and security checks"""
    booking = get_object_or_404(
        Booking.objects.select_related('karate_class', 'schedule'),
        id=booking_id,
        user=request.user
    )
    
    # Check if payment already completed
    if booking.payment_status == 'Paid' and booking.status == 'Confirmed':
        return redirect("classes:booking_success", booking_id=booking.id)
    
    # Check if payment expired
    if booking.is_payment_expired() and booking.payment_status == 'Pending':
        booking.mark_expired()
        messages.error(request, "Payment time expired. Please try booking again.")
        return redirect("classes:class_detail", slug=booking.karate_class.slug)
    
    # Check if payment failed
    if booking.payment_status == 'Failed' or booking.status == 'Cancelled':
        messages.error(request, "Payment failed. Please try booking again.")
        return redirect("classes:class_detail", slug=booking.karate_class.slug)
    
    # Calculate remaining time
    if booking.expires_at:
        remaining_seconds = int((booking.expires_at - timezone.now()).total_seconds())
        remaining_seconds = max(0, remaining_seconds)
    else:
        remaining_seconds = 300  # Default 5 minutes
    
    context = {
        'booking': booking,
        'timeout_seconds': remaining_seconds,
    }
    return render(request, "classes/payment_pending.html", context)

@login_required
@require_http_methods(["GET"])
def check_payment_status(request, booking_id):
    """
    AJAX endpoint to check payment status.
    Prioritizes database state (updated by callback) over M-Pesa query.
    This ensures redirect works even when sandbox query rate-limits (429).
    """
    try:
        booking = Booking.objects.select_related('karate_class').get(
            id=booking_id,
            user=request.user  # Security: only allow user to check their own booking
        )

        # 1. Check if payment is already confirmed via callback (most reliable)
        if booking.status == 'Confirmed' and booking.payment_status == 'Paid':
            return JsonResponse({
                'confirmed': True,
                'status': 'Paid',
                'booking_status': 'Confirmed',
                'receipt_number': booking.mpesa_receipt_number or '',
            })

        # 2. Check if failed or cancelled
        if booking.payment_status == 'Failed' or booking.status in ['Cancelled', 'Expired']:
            return JsonResponse({
                'failed': True,
                'status': booking.payment_status,
                'booking_status': booking.status,
                'reason': 'Payment failed or cancelled by user/timeout'
            })

        # 3. Check for timeout
        if booking.is_payment_expired():
            if booking.status == 'Pending':
                booking.mark_expired()  # Updates status to Expired
            return JsonResponse({
                'expired': True,
                'status': 'Pending',
                'booking_status': 'Expired'
            })

        # 4. Still pending → try querying M-Pesa ONLY if we have a transaction_id
        if (booking.payment_status == 'Pending' and
            booking.status == 'Pending' and
            booking.transaction_id):

            try:
                mpesa = MPesaPayment()
                result = mpesa.query_transaction(booking.transaction_id)

                if result and 'ResultCode' in result:
                    result_code = str(result['ResultCode'])

                    if result_code == '0':  # Success
                        receipt = result.get('MpesaReceiptNumber', '')
                        with transaction.atomic():
                            booking.confirm_payment(booking.transaction_id, receipt)
                            PaymentLog.objects.create(
                                booking=booking,
                                transaction_id=booking.transaction_id,
                                action='payment_confirmed_via_query',
                                status_code='0',
                                response_data=result
                            )

                        return JsonResponse({
                            'confirmed': True,
                            'status': 'Paid',
                            'booking_status': 'Confirmed',
                            'receipt_number': receipt
                        })

                    elif result_code not in ['1032', '1']:  # Not "user cancelled" or "pending"
                        # Treat as failed
                        with transaction.atomic():
                            booking.payment_status = 'Failed'
                            booking.status = 'Cancelled'
                            booking.cancelled_at = timezone.now()
                            booking.save()

                            PaymentLog.objects.create(
                                booking=booking,
                                transaction_id=booking.transaction_id,
                                action='payment_failed_via_query',
                                status_code=result_code,
                                response_data=result
                            )

                        return JsonResponse({
                            'failed': True,
                            'status': 'Failed',
                            'booking_status': 'Cancelled'
                        })

            except Exception as query_error:
                # Log but DO NOT fail the whole check
                logger.warning(
                    f"STK Query failed for booking {booking.id} (will rely on callback): {query_error}"
                )
                # Continue — we'll just return pending

        # 5. Still pending after all checks
        return JsonResponse({
            'status': 'Pending',
            'booking_status': 'Pending'
        })

    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found or access denied'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in check_payment_status: {e}", exc_info=True)
        return JsonResponse({'error': 'Server error'}, status=500)
    

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """M-Pesa callback endpoint - processes payment confirmations"""
    try:
        raw_body = request.body
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in callback")
            return HttpResponse("Invalid JSON", status=400)

        # Respond immediately to M-Pesa
        response = HttpResponse("OK", status=200)

        # Process the payment in a background thread
        import threading

        def process_callback():
            try:
                stk_callback = data.get('Body', {}).get('stkCallback', {})
                result_code = stk_callback.get('ResultCode')
                checkout_request_id = stk_callback.get('CheckoutRequestID')
                result_desc = stk_callback.get('ResultDesc', '')

                if not checkout_request_id:
                    logger.error("No CheckoutRequestID in callback")
                    return

                try:
                    booking = Booking.objects.select_related(
                        'user', 'karate_class', 'schedule'
                    ).get(transaction_id=checkout_request_id)
                except Booking.DoesNotExist:
                    logger.error(f"No booking found for CheckoutRequestID: {checkout_request_id}")
                    return

                # Log callback
                PaymentLog.objects.create(
                    booking=booking,
                    transaction_id=checkout_request_id,
                    action='callback_received',
                    status_code=str(result_code),
                    response_data=data,
                    ip_address=get_client_ip(request)
                )

                if result_code == 0:
                    # Payment success
                    callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                    receipt_number = next((i['Value'] for i in callback_metadata if i['Name'] == 'MpesaReceiptNumber'), 'N/A')

                    with db_transaction.atomic():
                        booking.confirm_payment(checkout_request_id, receipt_number)
                        PaymentLog.objects.create(
                            booking=booking,
                            transaction_id=checkout_request_id,
                            action='payment_confirmed',
                            status_code='0',
                            response_data={'receipt': receipt_number}
                        )

                    logger.info(f"✅ Payment confirmed: {booking.booking_reference} - Receipt: {receipt_number}")

                    # Send emails
                    try:
                        from .emails import send_booking_confirmation_email, send_payment_confirmation_email
                        if hasattr(send_booking_confirmation_email, 'delay'):
                            send_booking_confirmation_email.delay(booking.id)
                            send_payment_confirmation_email.delay(booking.id, receipt_number)
                        else:
                            send_booking_confirmation_email_sync(booking.id)
                            send_payment_confirmation_email_sync(booking.id, receipt_number)
                    except Exception as e:
                        logger.error(f"Failed to send confirmation emails: {e}")

                else:
                    # Payment failed
                    with db_transaction.atomic():
                        booking.payment_status = 'Failed'
                        booking.status = 'Cancelled'
                        booking.notes = f"{booking.notes or ''}\nPayment failed: {result_desc} (Code: {result_code})"
                        booking.cancelled_at = timezone.now()
                        booking.save()

                        PaymentLog.objects.create(
                            booking=booking,
                            transaction_id=checkout_request_id,
                            action='payment_failed',
                            status_code=str(result_code),
                            response_data=data
                        )

                    logger.warning(f"❌ Payment failed: {booking.booking_reference} - Code: {result_code}")

                    # Send failure email
                    try:
                        from .emails import send_payment_failed_email
                        if hasattr(send_payment_failed_email, 'delay'):
                            send_payment_failed_email.delay(booking.id, result_desc)
                        else:
                            send_payment_failed_email_sync(booking.id, result_desc)
                    except Exception as e:
                        logger.error(f"Failed to send payment failed email: {e}")

            except Exception as e:
                logger.error(f"Error processing callback in thread: {e}", exc_info=True)

        threading.Thread(target=process_callback).start()
        return response

    except Exception as e:
        logger.error(f"M-Pesa callback error: {e}", exc_info=True)
        return HttpResponse("Server error", status=500)


@login_required
def booking_success_view(request, booking_id):
    """Display booking success page with security validation"""
    booking = get_object_or_404(
        Booking.objects.select_related(
            'karate_class', 'schedule', 'karate_class__instructor'
        ),
        id=booking_id,
        user=request.user
    )
    
    # Verify booking is confirmed
    if booking.status != 'Confirmed':
        messages.warning(
            request,
            "This booking is not yet confirmed. Please wait for payment confirmation."
        )
        return redirect("classes:payment_pending", booking_id=booking.id)
    
    return render(request, "classes/booking_success.html", {"booking": booking})


@login_required
@require_http_methods(["POST"])
def cancel_booking_view(request, booking_id):
    """Cancel a booking with refund handling"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status not in ['Confirmed', 'Pending']:
        messages.error(request, "This booking cannot be cancelled.")
        return redirect("accounts:dashboard")
    
    # Cancel with atomic transaction
    with db_transaction.atomic():
        booking.cancel_booking("User requested cancellation")
        
        PaymentLog.objects.create(
            booking=booking,
            action='booking_cancelled',
            status_code='USER_CANCEL',
            ip_address=get_client_ip(request)
        )
        
        # Handle refunds
        if booking.payment_status == 'Paid':
            booking.payment_status = 'Refunded'
            booking.save()
            messages.info(
                request,
                f"Booking {booking.booking_reference} cancelled. "
                "Your refund request will be processed within 7 business days."
            )
        else:
            messages.success(request, f"Booking {booking.booking_reference} cancelled successfully.")
    
    return redirect("accounts:dashboard")


# ============================================================================
# REVIEW VIEWS
# ============================================================================

@login_required
def add_review_view(request, pk):
    """Add review for attended class"""
    karate_class = get_object_or_404(KarateClass, pk=pk)
    
    # Check if user has attended this class
    has_attended = Booking.objects.filter(
        user=request.user,
        karate_class=karate_class,
        attended=True
    ).exists()
    
    if not has_attended:
        messages.error(request, "You can only review classes you've attended.")
        return redirect("classes:class_detail", slug=karate_class.slug)
    
    # Check if already reviewed
    if ClassReview.objects.filter(user=request.user, karate_class=karate_class).exists():
        messages.error(request, "You've already reviewed this class.")
        return redirect("classes:class_detail", slug=karate_class.slug)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.karate_class = karate_class
            review.save()
            messages.success(request, "Review added successfully!")
            return redirect("classes:class_detail", slug=karate_class.slug)
    else:
        form = ReviewForm()
    
    return render(request, "classes/add_review.html", {"form": form, "cls": karate_class})


# In apps/classes/views.py

from django.db.models import Sum  # ← ADD THIS IMPORT (fixes the error)
# ... your other imports remain the same

@login_required
def my_bookings_view(request):
    """
    Display all bookings for the current logged-in user.
    Includes stats, active/pending/past separation, and total spent.
    """
    # All bookings for this user
    bookings = Booking.objects.filter(
        user=request.user
    ).select_related(
        'karate_class', 'schedule', 'karate_class__instructor'
    ).order_by('-booked_at')

    # Categorize bookings
    active_bookings = bookings.filter(
        status='Confirmed',
        payment_status='Paid'
    )

    pending_bookings = bookings.filter(
        status='Pending'
    ).exclude(payment_status='Failed')

    past_bookings = bookings.exclude(
        status__in=['Confirmed', 'Pending']
    )

    # Calculate total amount spent (only paid bookings)
    total_spent_result = active_bookings.aggregate(total=Sum('amount_paid'))
    total_spent = total_spent_result['total'] or 0

    # Optional: Upcoming sessions preview (if you track session dates)
    # For now, we'll leave it as empty — you can expand later
    upcoming_sessions = []

    context = {
        'bookings': bookings,
        'active_bookings': active_bookings,
        'pending_bookings': pending_bookings,
        'past_bookings': past_bookings,
        'has_any_booking': bookings.exists(),
        'total_spent': total_spent,
        'upcoming_sessions': upcoming_sessions,  # For future use
    }

    return render(request, "classes/my_bookings.html", context)