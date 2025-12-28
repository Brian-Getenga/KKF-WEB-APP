from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from apps.accounts.models import User
from apps.core.models import Instructor
from decimal import Decimal
import secrets


class KarateClass(models.Model):
    LEVEL_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('Competition', 'Competition Team'),
    ]
    CATEGORY_CHOICES = [
        ('Kids', 'Kids (5-12)'),
        ('Teens', 'Teens (13-17)'),
        ('Adults', 'Adults (18+)'),
        ('Private', 'Private Lessons'),
    ]

    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES)
    description = models.TextField()
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True)
    image = models.ImageField(upload_to='classes/', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    max_students = models.PositiveIntegerField(default=20)
    duration_minutes = models.PositiveIntegerField(default=60)
    
    free_trial_spots = models.PositiveIntegerField(default=5)
    requirements = models.TextField(blank=True, help_text="What students need to bring")
    what_youll_learn = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-featured', 'category', 'level']
        verbose_name = 'Karate Class'
        verbose_name_plural = 'Karate Classes'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def spots_available(self):
        total_bookings = self.bookings.filter(
            status__in=['Confirmed', 'Pending']
        ).count()
        return max(0, self.max_students - total_bookings)

    @property
    def free_trials_available(self):
        free_trial_count = self.bookings.filter(
            booking_type='Free Trial',
            status__in=['Confirmed', 'Pending']
        ).count()
        return max(0, self.free_trial_spots - free_trial_count)

    @property
    def is_full(self):
        return self.spots_available == 0

    def __str__(self):
        return f"{self.title} - {self.level}"


class ClassSchedule(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    karate_class = models.ForeignKey(
        KarateClass, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    day_of_week = models.CharField(max_length=20, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=255, default="Main Dojo")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ('karate_class', 'day_of_week', 'start_time')

    def __str__(self):
        return f"{self.karate_class.title} - {self.day_of_week} {self.start_time.strftime('%H:%M')}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending Payment'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
        ('Expired', 'Expired'),  # New: for expired pending payments
    ]
    
    BOOKING_TYPE_CHOICES = [
        ('Free Trial', 'Free Trial'),
        ('Monthly', 'Monthly Subscription'),
        ('Drop-in', 'Drop-in Class'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Pending', 'Pending'),  # New: payment initiated but not confirmed
        ('Paid', 'Paid'),
        ('Refunded', 'Refunded'),
        ('Failed', 'Failed'),
    ]

    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='class_bookings')
    karate_class = models.ForeignKey(KarateClass, on_delete=models.CASCADE, related_name='bookings')
    schedule = models.ForeignKey(ClassSchedule, on_delete=models.CASCADE)
    
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES, default='Monthly')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Unpaid')
    
    # Payment details
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transaction_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Security fields
    booking_reference = models.CharField(max_length=50, unique=True, blank=True)
    payment_verification_token = models.CharField(max_length=100, blank=True, null=True)
    payment_attempts = models.PositiveIntegerField(default=0)
    last_payment_attempt = models.DateTimeField(null=True, blank=True)
    
    # Attendance tracking
    attended = models.BooleanField(default=False)
    attendance_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    booked_at = models.DateTimeField(auto_now_add=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # New: payment expiry
    
    notes = models.TextField(blank=True)
    
    # Email tracking
    confirmation_email_sent = models.BooleanField(default=False)
    payment_email_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-booked_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['karate_class', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['booking_reference']),
            models.Index(fields=['payment_status', 'expires_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        if not self.payment_verification_token:
            self.payment_verification_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def generate_booking_reference(self):
        """Generate unique booking reference"""
        prefix = "BK"
        timestamp = timezone.now().strftime("%Y%m%d")
        random_str = secrets.token_hex(4).upper()
        return f"{prefix}{timestamp}{random_str}"

    def confirm_payment(self, transaction_id, receipt_number):
        """Confirm payment and update booking status - ATOMIC"""
        self.payment_status = 'Paid'
        self.status = 'Confirmed'
        self.transaction_id = transaction_id
        self.mpesa_receipt_number = receipt_number
        self.payment_date = timezone.now()
        self.confirmed_at = timezone.now()
        self.expires_at = None  # Clear expiry
        self.save()

    def cancel_booking(self, reason=None):
        """Cancel booking"""
        self.status = 'Cancelled'
        self.cancelled_at = timezone.now()
        if reason:
            self.notes = f"{self.notes}\nCancellation reason: {reason}" if self.notes else f"Cancellation reason: {reason}"
        self.save()

    def mark_expired(self):
        """Mark booking as expired due to payment timeout"""
        self.status = 'Expired'
        self.payment_status = 'Failed'
        self.notes = f"{self.notes}\nExpired due to payment timeout" if self.notes else "Expired due to payment timeout"
        self.save()

    def is_payment_expired(self):
        """Check if payment window has expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def __str__(self):
        return f"{self.booking_reference} - {self.user.email} - {self.karate_class.title} ({self.status})"


class ClassReview(models.Model):
    """Student reviews for classes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    karate_class = models.ForeignKey(KarateClass, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'karate_class')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.karate_class.title} ({self.rating}★)"


class WaitingList(models.Model):
    """Waiting list for full classes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    karate_class = models.ForeignKey(KarateClass, on_delete=models.CASCADE, related_name='waiting_list')
    schedule = models.ForeignKey(ClassSchedule, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'karate_class', 'schedule')
        ordering = ['added_at']
    
    def __str__(self):
        return f"{self.user.email} waiting for {self.karate_class.title}"


class PaymentLog(models.Model):
    """Log all payment attempts for audit trail"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payment_logs')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    action = models.CharField(max_length=50)  # 'initiated', 'callback_received', 'confirmed', 'failed'
    status_code = models.CharField(max_length=20, blank=True, null=True)
    response_data = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.booking.booking_reference} - {self.action} - {self.created_at}"