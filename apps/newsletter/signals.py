# ============================================================================
# newsletter/signals.py - COMPLETE AUTOMATED EMAIL SIGNALS
# ============================================================================

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

# Import all models directly (no string references!)
from apps.blog.models import BlogPost, Comment
from apps.store.models import Product, Order, ProductReview, Cart
from apps.classes.models import KarateClass, Booking, WaitingList
from apps.newsletter.models import Subscriber, Campaign
# from gallery.models import GalleryImage  # Uncomment if you want gallery signals

# Import Celery tasks
from .tasks import create_automated_campaign, send_campaign


# ============================================================================
# BLOG SIGNALS
# ============================================================================
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

# We'll store the old status temporarily on the instance
@receiver(pre_save, sender=BlogPost)
def store_old_status(sender, instance, **kwargs):
    """
    Capture the original status before save so we can detect actual changes.
    """
    if instance.pk:  # Only for existing objects (not new ones)
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._original_status = old_instance.status
        except sender.DoesNotExist:
            instance._original_status = None  # Shouldn't happen
    else:
        instance._original_status = None  # New instance


@receiver(post_save, sender=BlogPost)
def handle_blog_post_published(sender, instance, created, **kwargs):
    """
    Trigger newsletter/campaign only when a blog post is FIRST published.
    - On creation (if status is 'published')
    - Or when status changes from anything else → 'published'
    - Does NOT trigger on updates to already published posts
    """
    # Skip if not published or no published_at
    if instance.status != 'published' or not instance.published_at:
        return

    # Case 1: Newly created post that was saved as published
    if created:
        create_automated_campaign(
            campaign_type='blog_alert',
            title=f'New Blog Post: {instance.title}',
            subject=f'📝 New Article: {instance.title}',
            related_id=instance.id,
            content_object=instance
        )
        return

    # Case 2: Existing post whose status just changed to published
    old_status = getattr(instance, '_original_status', None)
    if old_status != 'published' and instance.status == 'published':
        create_automated_campaign(
            campaign_type='blog_alert',
            title=f'New Blog Post: {instance.title}',
            subject=f'📝 New Article: {instance.title}',
            related_id=instance.id,
            content_object=instance
        )


@receiver(post_save, sender=Comment)
def notify_comment_author(sender, instance, created, **kwargs):
    """Notify blog post author when someone comments"""
    if created and instance.approved and instance.post.author:
        author_email = instance.post.author.email
        
        context = {
            'post': instance.post,
            'comment': instance,
            'commenter': instance.get_display_name(),
        }
        
        html_message = render_to_string('newsletter/emails/new_comment_notification.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'💬 New comment on your post: {instance.post.title}',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[author_email],
            html_message=html_message,
            fail_silently=True,  # Change to False when debugging
        )


# ============================================================================
# KARATE CLASS SIGNALS
# ============================================================================

@receiver(post_save, sender=KarateClass)
def handle_new_class_created(sender, instance, created, **kwargs):
    """Notify subscribers when new class is added"""
    if created and instance.is_active:
        create_automated_campaign(
            campaign_type='new_class',
            title=f'New Class Available: {instance.title}',
            subject=f'🥋 New Karate Class: {instance.title}',
            related_id=instance.id,
            content_object=instance
        )


@receiver(post_save, sender=Booking)
def handle_booking_confirmation(sender, instance, created, **kwargs):
    """Send booking confirmation and payment reminders"""
    
    # New booking created
    if created:
        context = {
            'booking': instance,
            'user': instance.user,
            'karate_class': instance.karate_class,
        }
        
        html_message = render_to_string('newsletter/emails/booking_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'Booking Confirmation: {instance.booking_reference}',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
            html_message=html_message,
            fail_silently=True,
        )
    
    # Payment confirmed (only send once)
    elif instance.payment_status == 'Paid' and not instance.payment_email_sent:
        context = {
            'booking': instance,
            'user': instance.user,
            'karate_class': instance.karate_class,
        }
        
        html_message = render_to_string('newsletter/emails/payment_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'✅ Payment Confirmed: {instance.booking_reference}',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
            html_message=html_message,
            fail_silently=True,
        )
        
        # Mark as sent and save (avoid signal loop)
        instance.payment_email_sent = True
        instance.save(update_fields=['payment_email_sent'])


@receiver(post_save, sender=WaitingList)
def notify_waitlist_addition(sender, instance, created, **kwargs):
    """Notify user they've been added to waiting list"""
    if created:
        context = {
            'user': instance.user,
            'karate_class': instance.karate_class,
            'schedule': instance.schedule,
        }
        
        html_message = render_to_string('newsletter/emails/waitlist_notification.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'You\'re on the waiting list for {instance.karate_class.title}',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
            html_message=html_message,
            fail_silently=True,
        )


# ============================================================================
# STORE/PRODUCT SIGNALS
# ============================================================================

@receiver(post_save, sender=Product)
def handle_new_product_created(sender, instance, created, **kwargs):
    """Notify subscribers when new product is added"""
    if created and instance.is_active:
        create_automated_campaign(
            campaign_type='new_product',
            title=f'New Product: {instance.name}',
            subject=f'🛍️ Check Out Our New Product: {instance.name}',
            related_id=instance.id,
            content_object=instance
        )


@receiver(post_save, sender=Product)
def handle_product_discount(sender, instance, created, **kwargs):
    """Send promotion email when discount is first applied"""
    if not created and instance.discount_price:
        # Check if discount was just added (fetch previous state)
        old = sender.objects.filter(pk=instance.pk).only('discount_price').first()
        if old and not old.discount_price:
            create_automated_campaign(
                campaign_type='promotion',
                title=f'Special Offer: {instance.name}',
                subject=f'🔥 {instance.discount_percentage}% OFF: {instance.name}',
                related_id=instance.id,
                content_object=instance
            )


@receiver(post_save, sender=Product)
def notify_back_in_stock(sender, instance, created, **kwargs):
    """Notify wishlist users when product is back in stock"""
    if not created and instance.is_in_stock:
        # Check if stock was previously 0
        old = sender.objects.filter(pk=instance.pk).only('stock').first()
        if old and old.stock == 0:
            # Get wishlist users (assuming you have a Wishlist model)
            # If you don't have Wishlist yet, this will be empty — safe to leave
            try:
                wishlist_users = instance.wishlist_set.select_related('user').all()
                for wishlist_item in wishlist_users:
                    context = {
                        'user': wishlist_item.user,
                        'product': instance,
                    }
                    
                    html_message = render_to_string('newsletter/emails/back_in_stock.html', context)
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject=f'🎉 {instance.name} is Back in Stock!',
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[wishlist_item.user.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
            except AttributeError:
                # No wishlist model yet — skip silently
                pass


# ============================================================================
# ORDER SIGNALS
# ============================================================================

@receiver(post_save, sender=Order)
def handle_order_created(sender, instance, created, **kwargs):
    """Send order confirmation email"""
    if created:
        context = {
            'order': instance,
            'user': instance.user,
            'items': instance.items.all(),
        }
        
        html_message = render_to_string('newsletter/emails/order_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'Order Confirmation: {instance.order_number}',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email, instance.shipping_email],
            html_message=html_message,
            fail_silently=True,
        )


@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """Send email on order status changes"""
    if not created:
        status_emails = {
            'paid': ('✅ Payment Confirmed', 'payment_confirmed.html'),
            'processing': ('📦 Order Processing', 'order_processing.html'),
            'shipped': ('🚚 Order Shipped', 'order_shipped.html'),
            'delivered': ('✨ Order Delivered', 'order_delivered.html'),
            'cancelled': ('❌ Order Cancelled', 'order_cancelled.html'),
        }
        
        if instance.status in status_emails:
            subject_prefix, template_name = status_emails[instance.status]
            
            context = {
                'order': instance,
                'user': instance.user,
            }
            
            html_message = render_to_string(f'newsletter/emails/{template_name}', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f'{subject_prefix}: {instance.order_number}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.user.email],
                html_message=html_message,
                fail_silently=True,
            )


# ============================================================================
# REVIEW SIGNALS
# ============================================================================

@receiver(post_save, sender=ProductReview)
def notify_review_posted(sender, instance, created, **kwargs):
    """Thank user for review and notify admin"""
    if created:
        context = {
            'user': instance.user,
            'product': instance.product,
            'review': instance,
        }
        
        html_message = render_to_string('newsletter/emails/review_thank_you.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'Thank you for your review of {instance.product.name}',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
            html_message=html_message,
            fail_silently=True,
        )


# ============================================================================
# GALLERY SIGNALS (optional)
# ============================================================================

# Uncomment and import GalleryImage if you want this active
# @receiver(post_save, sender=GalleryImage)
# def handle_new_gallery_image(sender, instance, created, **kwargs):
#     """Notify subscribers about new gallery images (batch weekly)"""
#     if created and instance.is_featured and instance.is_public:
#         # Trigger weekly digest or individual campaign
#         pass


# ============================================================================
# NEWSLETTER SIGNALS
# ============================================================================
# apps/newsletter/signals.py

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Subscriber

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Subscriber)
def handle_new_subscriber(sender, instance, created, **kwargs):
    """
    Send welcome email exactly once when subscriber becomes active.
    Safe for double-opt-in confirmation flows.
    """
    # Skip if not active or email already sent
    if not instance.is_active or instance.welcome_email_sent:
        logger.debug(
            f"Skipped welcome email for {instance.email}: "
            f"active={instance.is_active}, already_sent={instance.welcome_email_sent}"
        )
        return

    try:
        logger.info(f"Sending welcome email to {instance.email} (ID: {instance.id})")

        context = {
            'subscriber': instance,
            'unsubscribe_url': f"{settings.SITE_URL}/newsletter/unsubscribe/{instance.unsubscribe_token}/",
        }

        html_message = render_to_string('newsletter/emails/welcome_subscriber.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject='🎉 Welcome to Our Newsletter!',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            html_message=html_message,
            fail_silently=False,  # Raise errors in dev
        )

        # Mark as sent (atomic update)
        instance.welcome_email_sent = True
        instance.save(update_fields=['welcome_email_sent'])

        logger.info(f"Welcome email successfully sent to {instance.email}")

    except Exception as e:
        logger.error(
            f"Failed to send welcome email to {instance.email} (ID: {instance.id})",
            exc_info=True
        )
        # In development, raise to see in terminal
        if settings.DEBUG:
            raise


        


@receiver(post_save, sender=Campaign)
def handle_campaign_scheduled(sender, instance, created, **kwargs):
    """Auto-send campaign when status changes to 'scheduled'"""
    if not created and instance.status == 'scheduled':
        send_campaign(instance.id)


# ============================================================================
# CART ABANDONMENT SIGNAL (placeholder)
# ============================================================================

@receiver(post_save, sender=Cart)
def track_cart_abandonment(sender, instance, created, **kwargs):
    """Track cart abandonment and send reminder emails"""
    # Usually handled by a periodic Celery task, not here
    pass


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def send_bulk_notification(email_list, subject, template_name, context):
    """Helper function to send bulk notifications"""
    for email in email_list:
        html_message = render_to_string(f'newsletter/emails/{template_name}', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True,
        )