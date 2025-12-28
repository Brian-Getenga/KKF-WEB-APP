"""
apps/classes/urls.py - URL Configuration
"""
from django.urls import path
from . import views

app_name = 'classes'

urlpatterns = [
    # Class listing and details
    path('', views.ClassListView.as_view(), name='class_list'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('<slug:slug>/', views.ClassDetailView.as_view(), name='class_detail'),
    path('schedule/', views.ScheduleView.as_view(), name='schedule'),
    
    # Booking
    path('<int:pk>/book/', views.BookingCreateView.as_view(), name='book_class'),
    path('booking/<int:booking_id>/pending/', views.payment_pending_view, name='payment_pending'),
    path('booking/<int:booking_id>/success/', views.booking_success_view, name='booking_success'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    
    # Payment
    path('payment/check/<int:booking_id>/', views.check_payment_status, name='check_payment'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Reviews
    path('<int:pk>/review/', views.add_review_view, name='add_review'),
   
]