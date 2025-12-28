# apps/accounts/admin.py - COMPLETE FILE
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, BeltProgress, TrainingStats, OTPVerification


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('email', 'first_name', 'last_name', 'is_instructor', 'is_member', 'email_verified', 'date_joined')
    list_filter = ('is_instructor', 'is_member', 'email_verified', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_instructor', 'is_member', 'email_verified')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'last_active')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'belt_level', 'phone', 'city', 'years_of_experience', 'is_profile_complete')
    list_filter = ('belt_level', 'gender', 'country')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('joined_at', 'updated_at', 'age')
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Contact Information', {'fields': ('phone', 'address', 'city', 'country')}),
        ('Personal Information', {'fields': ('date_of_birth', 'age', 'gender', 'bio', 'profile_picture')}),
        ('Karate Information', {'fields': ('belt_level', 'years_of_experience', 'preferred_training_time', 'training_goals')}),
        ('Emergency Contact', {'fields': ('emergency_contact_name', 'emergency_contact_phone')}),
        ('Notifications', {'fields': ('email_notifications', 'sms_notifications')}),
        ('Timestamps', {'fields': ('joined_at', 'updated_at')}),
    )


@admin.register(BeltProgress)
class BeltProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_belt', 'achieved_on', 'instructor', 'test_score')
    list_filter = ('current_belt', 'achieved_on')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    date_hierarchy = 'achieved_on'
    readonly_fields = ('created_at',)


@admin.register(TrainingStats)
class TrainingStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_classes_attended', 'total_training_hours', 'current_streak_days', 'tournaments_participated')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('updated_at',)


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('email', 'purpose', 'otp_code', 'is_verified', 'attempts', 'created_at', 'expires_at', 'is_expired_status')
    list_filter = ('purpose', 'is_verified', 'created_at')
    search_fields = ('email', 'user__email', 'otp_code')
    readonly_fields = ('created_at', 'verified_at', 'is_expired_status')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {'fields': ('user', 'email', 'phone')}),
        ('OTP Details', {'fields': ('otp_code', 'purpose')}),
        ('Verification Status', {'fields': ('is_verified', 'verified_at', 'attempts', 'max_attempts')}),
        ('Timestamps', {'fields': ('created_at', 'expires_at', 'is_expired_status')}),
    )
    
    def is_expired_status(self, obj):
        """Display whether OTP is expired"""
        return obj.is_expired()
    is_expired_status.boolean = True
    is_expired_status.short_description = 'Expired'
    
    actions = ['cleanup_expired_otps']
    
    def cleanup_expired_otps(self, request, queryset):
        """Admin action to clean up expired OTPs"""
        deleted_count = OTPVerification.cleanup_expired()
        self.message_user(request, f'{deleted_count} expired OTP records deleted.')
    cleanup_expired_otps.short_description = 'Delete expired OTP records'


# Register User model
admin.site.unregister(User) if admin.site.is_registered(User) else None
admin.site.register(User, UserAdmin)