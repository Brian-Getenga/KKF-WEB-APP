# apps/accounts/urls.py - COMPLETE FILE
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # =============================================================================
    # AUTHENTICATION URLS
    # =============================================================================
    path('signup/', views.RegisterView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # OTP Verification
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    
    # =============================================================================
    # DASHBOARD & PROFILE URLS
    # =============================================================================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/view/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('profile/<int:user_id>/', views.public_profile_view, name='public_profile'),
    
    # =============================================================================
    # SETTINGS URLS
    # =============================================================================
    path('settings/', views.account_settings_view, name='settings'),
    path('settings/password/', views.password_change_view, name='password_change'),
    path('settings/delete/', views.delete_account_view, name='delete_account'),
    
    # =============================================================================
    # TRAINING & PROGRESS URLS
    # =============================================================================
    path('belt-progress/', views.belt_progress_view, name='belt_progress'),
    path('belt-progress/add/', views.add_belt_progress, name='add_belt_progress'),
    path('training-stats/', views.training_stats_view, name='training_stats'),
    
    # =============================================================================
    # EXPORT & DOWNLOAD URLS
    # =============================================================================
    path('profile/download-pdf/', views.download_profile_pdf, name='download_profile_pdf'),
    path('training/export-csv/', views.export_training_data, name='export_training_data'),
]