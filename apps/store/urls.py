# store/urls.py

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Product URLs
    path('', views.ProductListView.as_view(), name='product_list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<int:pk>/review/', views.add_review, name='add_review'),
    
    # Cart URLs
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('cart/remove-coupon/', views.remove_coupon, name='remove_coupon'),
    
    # Checkout & Payment URLs
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('payment/pending/<int:pk>/', views.payment_pending, name='payment_pending'),
    path('payment/status/<int:pk>/', views.check_payment_status, name='check_payment_status'),
    path('payment/retry/<int:pk>/', views.retry_payment, name='retry_payment'),
    path('payment/callback/mpesa/', views.mpesa_callback, name='mpesa_callback'),
    
    # Order URLs
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/confirmation/', views.OrderConfirmationView.as_view(), name='order_confirmation'),
    path('orders/<int:pk>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/<int:pk>/delete/', views.delete_order, name='delete_order'),
    
    # Wishlist URLs
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:pk>/', views.toggle_wishlist, name='toggle_wishlist'),
]