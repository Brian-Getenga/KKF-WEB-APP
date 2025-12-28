# ============================================================================
# newsletter/models.py - UPDATED & CLEANED VERSION
# ============================================================================

from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator
import uuid


class Subscriber(models.Model):
    """Model for newsletter subscribers with preference management"""
    
    PREFERENCE_CHOICES = [
        ('blog_updates', 'Blog Updates'),
        ('new_classes', 'New Classes'),
        ('promotions', 'Promotions & New Products'),
        ('all', 'All Updates'),
    ]
    
    # Default integer primary key (id) is automatically added by Django
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    name = models.CharField(max_length=100, blank=True)
    preferences = models.CharField(
        max_length=20,
        choices=PREFERENCE_CHOICES,
        default='all'
    )
    is_active = models.BooleanField(default=False)  # False until confirmed
    confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    subscribed_date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(null=True, blank=True)
    welcome_email_sent = models.BooleanField(default=False, help_text="Has the welcome email been sent?")
    
    class Meta:
        ordering = ['-subscribed_date']
        verbose_name = 'Subscriber'
        verbose_name_plural = 'Subscribers'
    
    def __str__(self):
        return f"{self.email} ({'Active' if self.is_active else 'Pending'})"
    
    def confirm_subscription(self):
        """Confirm the subscription"""
        self.is_active = True
        self.confirmed_date = timezone.now()
        self.save(update_fields=['is_active', 'confirmed_date'])


class Campaign(models.Model):
    """Model for email campaigns"""
    
    CAMPAIGN_TYPES = [
        ('blog_alert', 'Blog Alert'),
        ('new_class', 'New Class Alert'),
        ('promotion', 'Promotion'),
        ('new_product', 'New Product'),
        ('manual', 'Manual Campaign'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField(help_text="HTML content for the email")
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES, default='manual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Related objects for automated campaigns
    related_post_id = models.IntegerField(null=True, blank=True, help_text="ID of related blog post")
    related_class_id = models.IntegerField(null=True, blank=True, help_text="ID of related class")
    related_product_id = models.IntegerField(null=True, blank=True, help_text="ID of related product")
    
    scheduled_date = models.DateTimeField(null=True, blank=True)
    sent_date = models.DateTimeField(null=True, blank=True)
    
    total_recipients = models.IntegerField(default=0)
    successful_sends = models.IntegerField(default=0)
    failed_sends = models.IntegerField(default=0)
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def get_target_subscribers(self):
        """Get subscribers based on campaign type"""
        base_qs = Subscriber.objects.filter(is_active=True)
        
        if self.campaign_type == 'blog_alert':
            return base_qs.filter(preferences__in=['blog_updates', 'all'])
        elif self.campaign_type == 'new_class':
            return base_qs.filter(preferences__in=['new_classes', 'all'])
        elif self.campaign_type in ['promotion', 'new_product']:
            return base_qs.filter(preferences__in=['promotions', 'all'])
        else:  # manual or any other
            return base_qs


class EmailLog(models.Model):
    """Log all sent emails for tracking"""
    
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='email_logs'
    )
    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.SET_NULL,   # Keeps log even if subscriber is deleted
        null=True,
        blank=True,                  # Allows logs without subscriber (e.g. bounced)
        related_name='email_logs'
    )
    sent_date = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-sent_date']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        indexes = [
            models.Index(fields=['campaign', 'sent_date']),
            models.Index(fields=['subscriber']),
        ]
    
    def __str__(self):
        email = self.subscriber.email if self.subscriber else 'N/A (deleted or bounced)'
        return f"{self.campaign.title} → {email} [{self.get_success_display()}]"

    def get_success_display(self):
        return "Success" if self.success else "Failed"