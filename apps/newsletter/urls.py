
# ============================================================================
# newsletter/urls.py - COMPLETE VERSION
# ============================================================================

from django.urls import path
from . import views

app_name = 'newsletter'

urlpatterns = [
    path('subscribe/', views.SubscribeView.as_view(), name='subscribe'),
    path('subscribe/success/', views.SubscribeSuccessView.as_view(), name='subscribe_success'),
    path('confirm/<uuid:token>/', views.ConfirmSubscriptionView.as_view(), name='confirm'),
    path('unsubscribe/<uuid:token>/', views.UnsubscribeView.as_view(), name='unsubscribe'),
    path('unsubscribe/success/', views.UnsubscribeSuccessView.as_view(), name='unsubscribe_success'),
]