# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import (
    Category, Product, ProductReview, Cart, CartItem,
    Order, OrderItem, Coupon, ShippingZone, Wishlist
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count', 'is_active', 'display_order']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    readonly_fields = ['user', 'rating', 'created_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'price_display', 'stock_status',
        'sales_count', 'average_rating', 'is_active', 'is_featured'
    ]
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['sku', 'views_count', 'sales_count', 'created_at', 'updated_at']
    inlines = [ProductReviewInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'category', 'brand')
        }),
        ('Description', {
            'fields': ('short_description', 'description', 'features', 'material')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price')
        }),
        ('Inventory', {
            'fields': ('stock', 'low_stock_threshold')
        }),
        ('Images', {
            'fields': ('image', 'image_2', 'image_3', 'image_4')
        }),
        ('Variants', {
            'fields': ('color', 'size')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('views_count', 'sales_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def price_display(self, obj):
        if obj.discount_price:
            return format_html(
                '<span style="text-decoration: line-through;">KES {}</span><br>'
                '<strong style="color: green;">KES {}</strong>',
                obj.price, obj.discount_price
            )
        return f'KES {obj.price}'
    price_display.short_description = 'Price'

    def stock_status(self, obj):
        if obj.stock == 0:
            color = 'red'
            status = 'Out of Stock'
        elif obj.is_low_stock:
            color = 'orange'
            status = f'Low Stock ({obj.stock})'
        else:
            color = 'green'
            status = f'In Stock ({obj.stock})'
        return format_html('<span style="color: {};">{}</span>', color, status)
    stock_status.short_description = 'Stock'


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['product__name', 'user__email', 'comment']
    readonly_fields = ['created_at', 'updated_at']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'unit_price', 'total_price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'total_price', 'status_display',
        'payment_method', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__email', 'shipping_name', 'mpesa_transaction_id']
    readonly_fields = [
        'order_number', 'subtotal', 'discount_amount', 'shipping_cost', 'total_price',
        'mpesa_transaction_id', 'mpesa_checkout_request_id',
        'created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at'
    ]
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payment_method', 'payment_status')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'discount_amount', 'shipping_cost', 'total_price')
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_name', 'shipping_email', 'shipping_phone',
                'shipping_address', 'shipping_city', 'shipping_postal_code',
                'delivery_notes', 'tracking_number'
            )
        }),
        ('M-Pesa Details', {
            'fields': ('mpesa_phone_number', 'mpesa_transaction_id', 'mpesa_checkout_request_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'processing': 'blue',
            'shipped': 'purple',
            'delivered': 'darkgreen',
            'cancelled': 'red',
            'refunded': 'gray',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered']

    def mark_as_paid(self, request, queryset):
        for order in queryset:
            if order.status == 'pending':
                order.mark_as_paid()
        self.message_user(request, f'{queryset.count()} orders marked as paid')
    mark_as_paid.short_description = 'Mark selected orders as paid'

    def mark_as_shipped(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='shipped', shipped_at=timezone.now())
        self.message_user(request, f'{count} orders marked as shipped')
    mark_as_shipped.short_description = 'Mark selected orders as shipped'

    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{count} orders marked as delivered')
    mark_as_delivered.short_description = 'Mark selected orders as delivered'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'discount_display', 'usage_display', 'valid_from',
        'valid_to', 'is_active'
    ]
    list_filter = ['is_active', 'discount_type']
    search_fields = ['code']
    readonly_fields = ['used_count', 'created_at']

    def discount_display(self, obj):
        if obj.discount_type == 'percentage':
            return f'{obj.discount_value}%'
        return f'KES {obj.discount_value}'
    discount_display.short_description = 'Discount'

    def usage_display(self, obj):
        if obj.usage_limit:
            return f'{obj.used_count}/{obj.usage_limit}'
        return f'{obj.used_count}/∞'
    usage_display.short_description = 'Usage'


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'shipping_cost', 'estimated_days', 'is_active']
    list_filter = ['is_active']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'items_count', 'total_price', 'created_at']
    readonly_fields = ['created_at', 'updated_at']

    def items_count(self, obj):
        return obj.total_items
    items_count.short_description = 'Items'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__email', 'product__name']

