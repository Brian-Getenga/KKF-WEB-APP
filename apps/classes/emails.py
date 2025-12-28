from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


def send_booking_confirmation_email_sync(booking_id):
    """
    Send booking confirmation email (synchronous version)
    """
    try:
        from .models import Booking
        
        with transaction.atomic():
            booking = Booking.objects.select_related(
                'user',
                'karate_class',
                'karate_class__instructor',
                'schedule'
            ).get(id=booking_id)
            
            # Check if already sent
            if booking.confirmation_email_sent:
                logger.info(f"Confirmation email already sent for booking {booking.booking_reference}")
                return
            
            subject = f"🥋 Booking Confirmed - {booking.karate_class.title}"
            to_email = booking.user.email
            from_email = settings.DEFAULT_FROM_EMAIL
            
            context = {
                'user': booking.user,
                'booking': booking,
                'class': booking.karate_class,
                'instructor': booking.karate_class.instructor,
                'schedule': booking.schedule,
                'site_url': settings.SITE_URL,
            }
            
            # Render HTML email
            html_content = render_to_string(
                'classes/emails/booking_confirmation.html',
                context
            )
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=f"Your booking for {booking.karate_class.title} has been confirmed!",
                from_email=from_email,
                to=[to_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            # Mark as sent
            booking.confirmation_email_sent = True
            booking.save(update_fields=['confirmation_email_sent'])
            
            logger.info(f"✓ Booking confirmation email sent to {to_email} for {booking.booking_reference}")
            
    except Exception as e:
        logger.error(f"Failed to send booking confirmation email: {e}", exc_info=True)
        raise


def send_payment_confirmation_email_sync(booking_id, receipt_number):
    """
    Send payment confirmation email (synchronous version)
    """
    try:
        from .models import Booking
        
        with transaction.atomic():
            booking = Booking.objects.select_related(
                'user',
                'karate_class',
                'karate_class__instructor',
                'schedule'
            ).get(id=booking_id)
            
            # Check if already sent
            if booking.payment_email_sent:
                logger.info(f"Payment email already sent for booking {booking.booking_reference}")
                return
            
            subject = f"💰 Payment Received - {booking.karate_class.title}"
            to_email = booking.user.email
            from_email = settings.DEFAULT_FROM_EMAIL
            
            context = {
                'user': booking.user,
                'booking': booking,
                'class': booking.karate_class,
                'instructor': booking.karate_class.instructor,
                'schedule': booking.schedule,
                'payment': {
                    'transaction_id': booking.transaction_id,
                    'receipt_number': receipt_number,
                    'amount': booking.amount_paid,
                    'date': booking.payment_date,
                },
                'site_url': settings.SITE_URL,
            }
            
            # Render HTML email
            html_content = render_to_string(
                'classes/emails/payment_confirmation.html',
                context
            )
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=f"Your payment of KES {booking.amount_paid} has been received!",
                from_email=from_email,
                to=[to_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            # Mark as sent
            booking.payment_email_sent = True
            booking.save(update_fields=['payment_email_sent'])
            
            logger.info(f"✓ Payment confirmation email sent to {to_email} for {booking.booking_reference}")
            
    except Exception as e:
        logger.error(f"Failed to send payment confirmation email: {e}", exc_info=True)
        raise


def send_payment_failed_email_sync(booking_id, reason=None):
    """
    Send payment failed notification email (synchronous version)
    """
    try:
        from .models import Booking
        
        booking = Booking.objects.select_related(
            'user',
            'karate_class',
            'karate_class__instructor',
            'schedule'
        ).get(id=booking_id)
        
        subject = f"❌ Payment Issue - {booking.karate_class.title}"
        to_email = booking.user.email
        from_email = settings.DEFAULT_FROM_EMAIL
        
        context = {
            'user': booking.user,
            'booking': booking,
            'class': booking.karate_class,
            'instructor': booking.karate_class.instructor,
            'schedule': booking.schedule,
            'reason': reason or "Payment could not be processed",
            'site_url': settings.SITE_URL,
        }
        
        # Render HTML email
        html_content = render_to_string(
            'classes/emails/payment_failed.html',
            context
        )
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=f"There was an issue processing your payment for {booking.karate_class.title}",
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"✓ Payment failed email sent to {to_email} for {booking.booking_reference}")
        
    except Exception as e:
        logger.error(f"Failed to send payment failed email: {e}", exc_info=True)
        raise


# Celery async tasks (if using Celery)
try:
    from celeryy import shared_task
    
    @shared_task(bind=True, max_retries=3)
    def send_booking_confirmation_email(self, booking_id):
        """Async task for booking confirmation email"""
        try:
            send_booking_confirmation_email_sync(booking_id)
        except Exception as exc:
            logger.error(f"Booking confirmation email task failed: {exc}")
            raise self.retry(exc=exc, countdown=60)
    
    @shared_task(bind=True, max_retries=3)
    def send_payment_confirmation_email(self, booking_id, receipt_number):
        """Async task for payment confirmation email"""
        try:
            send_payment_confirmation_email_sync(booking_id, receipt_number)
        except Exception as exc:
            logger.error(f"Payment confirmation email task failed: {exc}")
            raise self.retry(exc=exc, countdown=60)
    
    @shared_task(bind=True, max_retries=3)
    def send_payment_failed_email(self, booking_id, reason=None):
        """Async task for payment failed email"""
        try:
            send_payment_failed_email_sync(booking_id, reason)
        except Exception as exc:
            logger.error(f"Payment failed email task failed: {exc}")
            raise self.retry(exc=exc, countdown=60)

except ImportError:
    # Fallback to synchronous if Celery not available
    logger.warning("Celery not available, using synchronous email sending")
    send_booking_confirmation_email = send_booking_confirmation_email_sync
    send_payment_confirmation_email = send_payment_confirmation_email_sync
    send_payment_failed_email = send_payment_failed_email_sync