
# ============================================================================
# newsletter/email_utils.py - COMPLETE VERSION
# ============================================================================

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

def send_confirmation_email(subscriber,request):
    """Send double opt-in confirmation email"""
    confirmation_url = request.build_absolute_uri(
    reverse('newsletter:confirm', kwargs={'token': subscriber.confirmation_token})
)
    
    html_content = render_to_string('newsletter/confirmation_email.html', {
        'subscriber': subscriber,
        'confirmation_url': confirmation_url
    })
    
    email = EmailMultiAlternatives(
        subject='Confirm Your Newsletter Subscription',
        body='Please confirm your subscription by clicking the link in this email.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[subscriber.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()
