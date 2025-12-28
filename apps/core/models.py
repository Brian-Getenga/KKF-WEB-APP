# apps/core/models.py - FIXED FOR CIRCULAR DEPENDENCY (NO LOGIC CHANGES)

from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()


class Instructor(models.Model):
    """Enhanced instructor model with additional features"""
    
    BELT_RANKS = [
        ('1dan', '1st Dan Black Belt'),
        ('2dan', '2nd Dan Black Belt'),
        ('3dan', '3rd Dan Black Belt'),
        ('4dan', '4th Dan Black Belt'),
        ('5dan', '5th Dan Black Belt'),
        ('6dan', '6th Dan Black Belt'),
        ('7dan', '7th Dan Black Belt'),
        ('8dan', '8th Dan Black Belt'),
        ('9dan', '9th Dan Black Belt'),
        ('10dan', '10th Dan Black Belt'),
    ]
    
    SPECIALIZATIONS = [
        ('kata', 'Kata'),
        ('kumite', 'Kumite'),
        ('both', 'Kata & Kumite'),
        ('kids', 'Kids Training'),
        ('competition', 'Competition'),
    ]
    
    # Basic Info
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    rank = models.CharField(max_length=50, choices=BELT_RANKS)
    bio = models.TextField()
    short_bio = models.CharField(max_length=200, blank=True, help_text="Brief description for listings")
    
    # Professional Details
    experience_years = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    certifications = models.TextField(blank=True, help_text="List certifications, one per line")
    specialization = models.CharField(max_length=20, choices=SPECIALIZATIONS, default='both')
    
    # Media
    photo = models.ImageField(upload_to='instructors/')
    video_intro_url = models.URLField(blank=True, null=True, help_text="YouTube or Vimeo URL")
    
    # Social Links (JSONField for flexibility)
    social_links = models.JSONField(
        blank=True, 
        null=True,
        default=dict,
        help_text="Format: {'instagram': 'url', 'facebook': 'url', 'linkedin': 'url', 'twitter': 'url'}"
    )
    
    # Contact & Availability
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True, help_text="Available for new students")
    max_students = models.PositiveIntegerField(default=30, help_text="Maximum class capacity")
    
    # Stats & Features
    total_students = models.PositiveIntegerField(default=0, editable=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0, editable=False)
    is_featured = models.BooleanField(default=False, help_text="Display on homepage")
    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Instructor'
        verbose_name_plural = 'Instructors'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Instructor.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Auto-generate short_bio from bio if not provided
        if not self.short_bio and self.bio:
            self.short_bio = ' '.join(self.bio.split()[:25]) + '...'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.get_rank_display()}"
    
    def get_social_link(self, platform):
        """Safely get social link for a platform"""
        if self.social_links and isinstance(self.social_links, dict):
            return self.social_links.get(platform, '')
        return ''


class Achievement(models.Model):
    """Enhanced achievement tracking"""
    
    ACHIEVEMENT_TYPES = [
        ('competition', 'Competition Medal'),
        ('championship', 'Championship Title'),
        ('certification', 'Certification'),
        ('milestone', 'Milestone'),
        ('award', 'Award'),
        ('recognition', 'Recognition'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES, default='competition')
    image = models.ImageField(upload_to='achievements/', blank=True, null=True)
    date = models.DateField()
    location = models.CharField(max_length=200, blank=True, help_text="Event location")
    
    # Relations
    instructor = models.ForeignKey(
        Instructor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='achievements'
    )
    # FIXED: string reference
    students = models.ManyToManyField(
        'accounts.User', 
        blank=True, 
        related_name='achievements',
        help_text="Students who earned this achievement"
    )
    
    # Display Options
    highlight_color = models.CharField(max_length=10, default="#FFCD00")
    is_featured = models.BooleanField(default=False, help_text="Display on homepage")
    external_link = models.URLField(blank=True, help_text="Link to news article or proof")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Achievement'
        verbose_name_plural = 'Achievements'

    def __str__(self):
        return f"{self.title} ({self.date.year})"


class Testimonial(models.Model):
    """Enhanced testimonial system"""
    
    # Personal Info
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    belt_rank = models.CharField(max_length=50, blank=True, help_text="e.g., Green Belt, 2nd Dan")
    photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    
    # Testimonial Content
    message = models.TextField()
    title = models.CharField(max_length=150, blank=True, help_text="Short highlight quote")
    rating = models.PositiveIntegerField(
        default=5, 
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Relations
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        help_text="Instructor being reviewed"
    )
    # FIXED: string reference
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials'
    )
    
    # Moderation
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Display on homepage")
    admin_notes = models.TextField(blank=True, help_text="Internal notes")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'

    def __str__(self):
        return f"{self.name} - {self.rating}★"
    
    def approve(self):
        """Approve testimonial"""
        from django.utils import timezone
        self.is_approved = True
        self.approved_at = timezone.now()
        self.save()


class InstructorAvailability(models.Model):
    """Track instructor availability and schedule"""
    
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['instructor', 'day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.instructor.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class InstructorReview(models.Model):
    """Detailed instructor reviews from students"""
    
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    # FIXED: string reference
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='instructor_reviews'
    )
    
    # Rating Categories (1-5)
    teaching_quality = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    technique = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    motivation = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Review Content
    review_text = models.TextField()
    pros = models.TextField(blank=True, help_text="What you liked")
    cons = models.TextField(blank=True, help_text="What could be improved")
    
    # Metadata
    is_verified = models.BooleanField(default=False, help_text="Verified student review")
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['instructor', 'user']
        verbose_name = 'Instructor Review'
        verbose_name_plural = 'Instructor Reviews'
    
    def __str__(self):
        return f"{self.user} review of {self.instructor.name}"
    
    @property
    def overall_rating(self):
        """Calculate average rating"""
        return (self.teaching_quality + self.communication + 
                self.technique + self.motivation) / 4