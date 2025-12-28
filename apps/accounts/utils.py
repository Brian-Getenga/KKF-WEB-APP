# apps/accounts/utils.py - COMPLETE FILE
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_otp_email(email, otp_code, purpose='signup', user_name=None):
    """
    Send OTP via email
    """
    purpose_text = {
        'signup': 'Account Registration',
        'login': 'Login Verification',
        'password_reset': 'Password Reset',
        'email_change': 'Email Change Verification',
    }
    
    subject = f'KKF - Your Verification Code for {purpose_text.get(purpose, "Verification")}'
    
    # Create email context
    context = {
        'otp_code': otp_code,
        'purpose': purpose_text.get(purpose, 'Verification'),
        'user_name': user_name or email.split('@')[0],
        'expires_in': '10 minutes',
    }
    
    # Try to render HTML email template
    try:
        html_message = render_to_string('accounts/emails/otp_email.html', context)
        plain_message = strip_tags(html_message)
    except:
        # Fallback to simple message if template doesn't exist
        html_message = None
        plain_message = f"""
Hello {context['user_name']},

Your verification code for {context['purpose']} is:

{otp_code}

This code will expire in {context['expires_in']}.

If you didn't request this code, please ignore this email.

Best regards,
Kenya Karate Federation Team
        """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@kkf.co.ke',
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False


def send_otp_sms(phone, otp_code, purpose='signup'):
    """
    Send OTP via SMS
    You'll need to integrate with an SMS provider like Twilio, Africa's Talking, etc.
    """
    purpose_text = {
        'signup': 'Sign Up',
        'login': 'Login',
        'password_reset': 'Password Reset',
    }
    
    message = f"Your KKF {purpose_text.get(purpose, 'verification')} code is: {otp_code}. Valid for 10 minutes."
    
    # TODO: Integrate with your SMS provider
    # Example with Africa's Talking (Kenya):
    """
    try:
        import africastalking
        
        username = settings.AFRICASTALKING_USERNAME
        api_key = settings.AFRICASTALKING_API_KEY
        
        africastalking.initialize(username, api_key)
        sms = africastalking.SMS
        
        response = sms.send(message, [phone])
        print(response)
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False
    """
    
    # For now, just print (development mode)
    print(f"SMS to {phone}: {message}")
    return True


def format_phone_number(phone):
    """
    Format phone number to Kenya format
    Converts various formats to +254XXXXXXXXX
    """
    if not phone:
        return None
    
    # Remove spaces, dashes, parentheses
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Handle Kenya numbers
    if phone.startswith('0'):
        phone = '+254' + phone[1:]
    elif phone.startswith('254'):
        phone = '+' + phone
    elif not phone.startswith('+'):
        phone = '+254' + phone
    
    return phone


def validate_otp_code(code):
    """
    Validate OTP code format
    """
    if not code:
        return False
    
    # Remove spaces
    code = code.replace(' ', '')
    
    # Must be 6 digits
    return code.isdigit() and len(code) == 6