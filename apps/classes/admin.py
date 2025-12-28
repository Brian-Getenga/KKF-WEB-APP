from django.contrib import admin
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from .models import (
    KarateClass,
    ClassSchedule,
    Booking,
    ClassReview,
    WaitingList,
    PaymentLog,
)


@admin.register(KarateClass)
class KarateClassAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "level",
        "instructor",
        "price",
        "spots_available",
        "free_trials_available",
        "is_full",
        "is_active",
        "featured",
    )
    list_filter = ("category", "level", "is_active", "featured", "instructor")
    search_fields = ("title", "description", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "spots_available", "free_trials_available")
    fieldsets = (
        (None, {
            "fields": (
                "title",
                "slug",
                "category",
                "level",
                "description",
                "instructor",
                "image",
            )
        }),
        ("Pricing & Capacity", {
            "fields": (
                "price",
                "max_students",
                "duration_minutes",
                "free_trial_spots",
            )
        }),
        ("Additional Info", {
            "fields": ("requirements", "what_youll_learn"),
            "classes": ("collapse",),
        }),
        ("Status", {
            "fields": ("is_active", "featured"),
        }),
        ("Read-only", {
            "fields": ("spots_available", "free_trials_available", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def spots_available(self, obj):
        return obj.spots_available
    spots_available.short_description = "Spots Available"

    def free_trials_available(self, obj):
        return obj.free_trials_available
    free_trials_available.short_description = "Free Trials Available"

    def is_full(self, obj):
        # Fixed TypeError using mark_safe
        if obj.is_full:
            return mark_safe('<span style="color: red; font-weight: bold;">Full</span>')
        return mark_safe('<span style="color: green;">Available</span>')
    is_full.short_description = "Capacity Status"


class ClassScheduleInline(admin.TabularInline):
    model = ClassSchedule
    extra = 1
    fields = ("day_of_week", "start_time", "end_time", "location", "is_active")
    ordering = ("day_of_week", "start_time")


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ("karate_class", "day_of_week", "start_time", "end_time", "location", "is_active")
    list_filter = ("day_of_week", "is_active", "karate_class__category")
    search_fields = ("karate_class__title", "location")
    inlines = []


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_reference",
        "user_link",
        "karate_class",
        "schedule",
        "booking_type",
        "status",
        "payment_status",
        "amount_paid",
        "booked_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "booking_type",
        "karate_class__category",
        "booked_at",
        "payment_date",
    )
    search_fields = (
        "booking_reference",
        "user__email",
        "user__first_name",
        "user__last_name",
        "transaction_id",
        "mpesa_receipt_number",
        "phone_number",
    )
    readonly_fields = (
        "booking_reference",
        "payment_verification_token",
        "booked_at",
        "confirmed_at",
        "cancelled_at",
        "payment_date",
        "expires_at",
    )
    date_hierarchy = "booked_at"
    actions = ["mark_as_confirmed", "mark_as_cancelled"]

    fieldsets = (
        (None, {
            "fields": (
                "booking_reference",
                "user",
                "karate_class",
                "schedule",
                "booking_type",
                "status",
                "payment_status",
            )
        }),
        ("Payment Details", {
            "fields": (
                "amount_paid",
                "transaction_id",
                "mpesa_receipt_number",
                "phone_number",
                "payment_date",
                "expires_at",
            )
        }),
        ("Attendance & Notes", {
            "fields": ("attended", "attendance_date", "notes"),
        }),
        ("Security & Tracking", {
            "fields": ("payment_verification_token", "payment_attempts", "last_payment_attempt"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("booked_at", "confirmed_at", "cancelled_at"),
            "classes": ("collapse",),
        }),
    )

    def user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=[obj.user.id])
        return mark_safe(f'<a href="{url}">{obj.user.email}</a>')
    user_link.short_description = "User"

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status="Confirmed", payment_status="Paid", confirmed_at=timezone.now())
    mark_as_confirmed.short_description = "Mark selected bookings as Confirmed/Paid"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(status="Cancelled", cancelled_at=timezone.now())
    mark_as_cancelled.short_description = "Mark selected bookings as Cancelled"


@admin.register(ClassReview)
class ClassReviewAdmin(admin.ModelAdmin):
    list_display = ("karate_class", "user", "rating", "created_at")
    list_filter = ("rating", "karate_class__category", "created_at")
    search_fields = ("user__email", "comment", "karate_class__title")
    readonly_fields = ("user", "karate_class", "created_at")


@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = ("user", "karate_class", "schedule", "added_at", "notified")
    list_filter = ("notified", "karate_class__category", "added_at")
    search_fields = ("user__email", "karate_class__title")
    actions = ["mark_as_notified"]

    def mark_as_notified(self, request, queryset):
        queryset.update(notified=True)
    mark_as_notified.short_description = "Mark selected as notified"


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ("booking", "action", "transaction_id", "status_code", "created_at")
    list_filter = ("action", "status_code", "created_at")
    search_fields = ("booking__booking_reference", "transaction_id")
    readonly_fields = ("booking", "transaction_id", "action", "status_code", "response_data", "ip_address", "user_agent", "created_at")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
