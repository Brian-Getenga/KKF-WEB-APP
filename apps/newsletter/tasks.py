# ============================================================================
# newsletter/tasks.py - COMPLETE VERSION
# ============================================================================

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import Campaign, Subscriber, EmailLog


def send_campaign(campaign_id):
    """Send email campaign to all targeted subscribers"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        campaign.status = 'sending'
        campaign.save()
        
        # Get target subscribers
        subscribers = campaign.get_target_subscribers()
        campaign.total_recipients = subscribers.count()
        campaign.save()
        
        success_count = 0
        fail_count = 0
        
        for subscriber in subscribers:
            try:
                # Render email with unsubscribe link
                html_content = render_to_string('newsletter/email_template.html', {
                    'subscriber': subscriber,
                    'campaign': campaign,
                    'content': campaign.content,
                    'unsubscribe_url': f"{settings.SITE_URL}/newsletter/unsubscribe/{subscriber.unsubscribe_token}/"
                })
                
                # Send email
                email = EmailMultiAlternatives(
                    subject=campaign.subject,
                    body='Please view this email in an HTML-compatible email client.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[subscriber.email]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                
                # Log success
                EmailLog.objects.create(
                    campaign=campaign,
                    subscriber=subscriber,
                    success=True
                )
                success_count += 1
                
            except Exception as e:
                # Log failure
                EmailLog.objects.create(
                    campaign=campaign,
                    subscriber=subscriber,
                    success=False,
                    error_message=str(e)
                )
                fail_count += 1
        
        # Update campaign status
        campaign.status = 'sent'
        campaign.sent_date = timezone.now()
        campaign.successful_sends = success_count
        campaign.failed_sends = fail_count
        campaign.save()
        
    except Campaign.DoesNotExist:
        pass
    except Exception as e:
        try:
            campaign.status = 'failed'
            campaign.save()
        except:
            pass


def create_automated_campaign(campaign_type, title, subject, related_id, content_object):
    """Create and send automated campaign based on triggers"""
    from .email_templates import get_email_template
    
    # Generate HTML content based on type
    html_content = get_email_template(campaign_type, content_object)
    
    # Create campaign
    campaign = Campaign.objects.create(
        title=title,
        subject=subject,
        content=html_content,
        campaign_type=campaign_type,
        status='draft'
    )
    
    # Set related ID based on type
    if campaign_type == 'blog_alert':
        campaign.related_post_id = related_id
    elif campaign_type == 'new_class':
        campaign.related_class_id = related_id
    elif campaign_type in ['promotion', 'new_product']:
        campaign.related_product_id = related_id
    
    campaign.save()
    
    # Auto-send
    send_campaign(campaign.id)

