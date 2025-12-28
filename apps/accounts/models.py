# apps/accounts/models.py - COMPLETE FILE (FIXED FOR CIRCULAR DEPENDENCY)

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.conf import settings
from django.core.validators import RegexValidator
import random
import string
from datetime import timedelta


# -----------------------------
# Custom User Manager
# -----------------------------
class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    instead of username.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


# -----------------------------
# Custom User Model
# -----------------------------
class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = None  # remove username
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_instructor = models.BooleanField(default=False)
    is_member = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    email_verified = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_instructor', 'is_member']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper()


# -----------------------------
# Extended User Profile
# -----------------------------
class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]

    BELT_LEVELS = [
        ('White', 'White Belt'),
        ('Yellow', 'Yellow Belt'),
        ('Orange', 'Orange Belt'),
        ('Green', 'Green Belt'),
        ('Blue', 'Blue Belt'),
        ('Brown', 'Brown Belt'),
        ('Black', 'Black Belt'),
    ]

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)
    belt_level = models.CharField(max_length=30, choices=BELT_LEVELS, default="White")
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default="Kenya")
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    
    # Training preferences
    preferred_training_time = models.CharField(max_length=50, blank=True, null=True)
    training_goals = models.TextField(max_length=500, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    
    # Notifications
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-joined_at']

    def __str__(self):
        return f"Profile - {self.user.email}"

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

    @property
    def is_profile_complete(self):
        required_fields = [
            self.phone, self.date_of_birth, self.address, 
            self.city, self.emergency_contact_name, self.emergency_contact_phone
        ]
        return all(required_fields)


# -----------------------------
# Belt Progress Tracker
# -----------------------------
class BeltProgress(models.Model):
    BELT_COLORS = [
        ('White', 'White'),
        ('Yellow', 'Yellow'),
        ('Orange', 'Orange'),
        ('Green', 'Green'),
        ('Blue', 'Blue'),
        ('Brown', 'Brown'),
        ('Black', 'Black'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='belt_history')
    current_belt = models.CharField(max_length=20, choices=BELT_COLORS, default='White')
    achieved_on = models.DateField(default=timezone.now)
    
    # FIXED: Changed from direct import to string reference
    instructor = models.ForeignKey(
        'core.Instructor', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    next_goal = models.CharField(max_length=20, choices=BELT_COLORS, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    certificate_url = models.URLField(blank=True, null=True)
    test_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-achieved_on']
        verbose_name_plural = "Belt Progress Records"

    def __str__(self):
        return f"{self.user.full_name} - {self.current_belt} Belt"


# -----------------------------
# Training Stats
# -----------------------------
class TrainingStats(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='training_stats')
    total_classes_attended = models.PositiveIntegerField(default=0)
    total_training_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    current_streak_days = models.PositiveIntegerField(default=0)
    longest_streak_days = models.PositiveIntegerField(default=0)
    last_training_date = models.DateField(null=True, blank=True)
    tournaments_participated = models.PositiveIntegerField(default=0)
    tournaments_won = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Training Statistics"

    def __str__(self):
        return f"Stats - {self.user.full_name}"

    def update_streak(self, training_date):
        """Update training streak based on training date"""
        if self.last_training_date:
            days_diff = (training_date - self.last_training_date).days
            if days_diff == 1:
                self.current_streak_days += 1
            elif days_diff > 1:
                self.current_streak_days = 1
        else:
            self.current_streak_days = 1
        
        if self.current_streak_days > self.longest_streak_days:
            self.longest_streak_days = self.current_streak_days
        
        self.last_training_date = training_date
        self.save()


# -----------------------------
# OTP Verification Model
# -----------------------------
class OTPVerification(models.Model):
    """
    OTP verification model for email/phone verification
    """
    OTP_PURPOSE_CHOICES = [
        ('signup', 'Sign Up Verification'),
        ('login', 'Login Verification'),
        ('password_reset', 'Password Reset'),
        ('email_change', 'Email Change'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='otp_codes',
        null=True,
        blank=True
    )
    email = models.EmailField()
    phone = models.CharField(max_length=17, blank=True, null=True)
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=OTP_PURPOSE_CHOICES, default='signup')
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'otp_code', 'is_verified']),
            models.Index(fields=['created_at', 'expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.email} - {self.purpose}"
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_otp(length=6):
        """Generate a random 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def is_max_attempts_reached(self):
        """Check if maximum verification attempts reached"""
        return self.attempts >= self.max_attempts
    
    def verify(self, input_otp):
        """
        Verify the OTP code
        Returns: (success: bool, message: str)
        """
        self.attempts += 1
        self.save(update_fields=['attempts'])
        
        # Check if max attempts reached
        if self.is_max_attempts_reached():
            return False, "Maximum verification attempts reached. Please request a new code."
        
        # Check if expired
        if self.is_expired():
            return False, "OTP has expired. Please request a new code."
        
        # Check if already verified
        if self.is_verified:
            return False, "This OTP has already been used."
        
        # Verify the code
        if self.otp_code == input_otp:
            self.is_verified = True
            self.verified_at = timezone.now()
            self.save(update_fields=['is_verified', 'verified_at'])
            return True, "OTP verified successfully!"
        
        remaining_attempts = self.max_attempts - self.attempts
        return False, f"Invalid OTP. {remaining_attempts} attempts remaining."
    
    @classmethod
    def create_otp(cls, email, purpose='signup', phone=None, user=None):
        """
        Create a new OTP for the given email
        Invalidates any existing unverified OTPs
        """
        # Invalidate existing unverified OTPs for this email and purpose
        cls.objects.filter(
            email=email,
            purpose=purpose,
            is_verified=False
        ).update(is_verified=True)  # Mark as verified to prevent reuse
        
        # Create new OTP
        otp = cls.objects.create(
            user=user,
            email=email,
            phone=phone,
            purpose=purpose
        )
        
        return otp
    
    @classmethod
    def verify_otp(cls, email, otp_code, purpose='signup'):
        """
        Verify OTP for given email and purpose
        Returns: (success: bool, message: str, otp_instance)
        """
        try:
            otp = cls.objects.filter(
                email=email,
                purpose=purpose,
                is_verified=False
            ).order_by('-created_at').first()
            
            if not otp:
                return False, "No valid OTP found. Please request a new code.", None
            
            success, message = otp.verify(otp_code)
            return success, message, otp
            
        except cls.DoesNotExist:
            return False, "Invalid OTP request.", None
    
    @classmethod
    def cleanup_expired(cls):
        """
        Clean up expired OTPs (run this periodically via cron/celery)
        """
        expired_date = timezone.now() - timedelta(hours=24)
        deleted_count = cls.objects.filter(created_at__lt=expired_date).delete()[0]
        return deleted_count