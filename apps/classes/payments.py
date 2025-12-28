"""
apps/classes/payments.py - ENHANCED WITH BUG FIXES
"""
import requests
import base64
import hmac
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction as db_transaction
import logging
import json
import time

logger = logging.getLogger(__name__)


class MPesaPayment:
    """Enhanced M-Pesa STK Push Payment Integration with Security"""
    
    def __init__(self):
        self.business_short_code = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.api_url = settings.MPESA_API_URL
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.timeout = 30  # 30 seconds timeout
        self.max_retries = 3
        
    def get_access_token(self):
        """Get OAuth access token with caching and retry"""
        cache_key = 'mpesa_access_token'
        token = cache.get(cache_key)
        
        if token:
            logger.info("Using cached M-Pesa access token")
            return token
        
        for attempt in range(self.max_retries):
            try:
                api_url = f"{self.api_url}/oauth/v1/generate?grant_type=client_credentials"
                response = requests.get(
                    api_url,
                    auth=(self.consumer_key, self.consumer_secret),
                    timeout=self.timeout
                )
                response.raise_for_status()
                token = response.json()['access_token']
                
                # Cache for 50 minutes (expires in 60)
                cache.set(cache_key, token, 3000)
                logger.info("✓ M-Pesa access token obtained and cached")
                return token
                
            except requests.exceptions.Timeout:
                logger.error(f"Attempt {attempt + 1} - Access token request timeout")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt + 1} - Access token error: {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)
        
        return None
    
    def generate_password(self):
        """Generate password for STK push"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = f"{self.business_short_code}{self.passkey}{timestamp}"
        encoded = base64.b64encode(data_to_encode.encode())
        return encoded.decode('utf-8'), timestamp
    
    def generate_callback_signature(self, data):
        """Generate signature for callback verification"""
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.passkey.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_callback_signature(self, received_signature, data):
        """Verify callback signature"""
        expected_signature = self.generate_callback_signature(data)
        return hmac.compare_digest(received_signature, expected_signature)
    
    def validate_phone_number(self, phone_number):
        """Validate and format Kenyan phone number"""
        phone = ''.join(filter(str.isdigit, str(phone_number)))
        
        if len(phone) == 12 and phone.startswith('254'):
            return phone
        elif len(phone) == 10 and phone.startswith('0'):
            return '254' + phone[1:]
        elif len(phone) == 9:
            return '254' + phone
        else:
            logger.warning(f"Invalid phone format: {phone_number}")
            return None
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc, booking_id=None):
        """Initiate STK Push with enhanced security and validation"""
        try:
            # Validate phone
            phone = self.validate_phone_number(phone_number)
            if not phone:
                return {
                    'success': False,
                    'error_code': 'INVALID_PHONE',
                    'message': 'Invalid phone number. Use format: 254712345678'
                }
            
            # Validate amount
            try:
                amount_int = int(float(amount))
                if amount_int < 1:
                    return {
                        'success': False,
                        'error_code': 'INVALID_AMOUNT',
                        'message': 'Amount must be at least KES 1'
                    }
            except (ValueError, TypeError):
                return {
                    'success': False,
                    'error_code': 'INVALID_AMOUNT',
                    'message': 'Invalid amount format'
                }
            
            # Get access token
            access_token = self.get_access_token()
            if not access_token:
                return {
                    'success': False,
                    'error_code': 'AUTH_FAILED',
                    'message': 'Failed to authenticate with M-Pesa. Please try again.'
                }
            
            # Generate password and timestamp
            password, timestamp = self.generate_password()
            
            # Prepare API request
            api_url = f"{self.api_url}/mpesa/stkpush/v1/processrequest"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': self.business_short_code,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': str(amount_int),
                'PartyA': phone,
                'PartyB': self.business_short_code,
                'PhoneNumber': phone,
                'CallBackURL': self.callback_url,
                'AccountReference': account_reference[:20],
                'TransactionDesc': transaction_desc[:20]
            }
            
            logger.info(f"🚀 Initiating STK push: Phone={phone}, Amount={amount_int}, Ref={account_reference}")
            
            # Make request with retry
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        api_url,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    logger.info(f"M-Pesa Response ({response.status_code}): {response.text}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result.get('ResponseCode') == '0':
                            checkout_request_id = result.get('CheckoutRequestID')
                            merchant_request_id = result.get('MerchantRequestID')
                            
                            # Cache request for validation (10 minutes)
                            cache_key = f"mpesa_request_{checkout_request_id}"
                            cache.set(cache_key, {
                                'merchant_request_id': merchant_request_id,
                                'phone': phone,
                                'amount': amount_int,
                                'reference': account_reference,
                                'timestamp': timestamp,
                                'booking_id': booking_id
                            }, 600)
                            
                            logger.info(f"✓ STK push successful: {checkout_request_id}")
                            
                            return {
                                'success': True,
                                'checkout_request_id': checkout_request_id,
                                'merchant_request_id': merchant_request_id,
                                'message': 'Payment request sent. Check your phone.',
                                'phone_number': phone
                            }
                        else:
                            error_code = result.get('ResponseCode', 'UNKNOWN')
                            error_msg = result.get('ResponseDescription', 'Payment request failed')
                            logger.warning(f"✗ STK push failed: {error_code} - {error_msg}")
                            
                            return {
                                'success': False,
                                'error_code': error_code,
                                'message': self._get_user_friendly_error(error_msg)
                            }
                    else:
                        if attempt < self.max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1} - HTTP {response.status_code}, retrying...")
                            time.sleep(2)
                            continue
                        else:
                            return {
                                'success': False,
                                'error_code': f'HTTP_{response.status_code}',
                                'message': 'M-Pesa service temporarily unavailable. Please try again.'
                            }
                        
                except requests.exceptions.Timeout:
                    logger.error(f"Attempt {attempt + 1} - Request timeout")
                    if attempt < self.max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        return {
                            'success': False,
                            'error_code': 'TIMEOUT',
                            'message': 'Request timeout. Please try again.'
                        }
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Attempt {attempt + 1} - Request error: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        return {
                            'success': False,
                            'error_code': 'NETWORK_ERROR',
                            'message': 'Network error. Please check your connection and try again.'
                        }
                
        except Exception as e:
            logger.error(f"Unexpected STK Push error: {e}", exc_info=True)
            return {
                'success': False,
                'error_code': 'SYSTEM_ERROR',
                'message': 'System error. Please try again or contact support.'
            }
    
    def query_transaction(self, checkout_request_id):
        """Query transaction status with validation"""
        try:
            cache_key = f"mpesa_request_{checkout_request_id}"
            cached_data = cache.get(cache_key)
            
            if not cached_data:
                logger.warning(f"No cached data for: {checkout_request_id}")
                return None
            
            access_token = self.get_access_token()
            if not access_token:
                logger.error("Failed to get access token for query")
                return None
            
            password, timestamp = self.generate_password()
            
            api_url = f"{self.api_url}/mpesa/stkpushquery/v1/query"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': self.business_short_code,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }
            
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            result['cached_data'] = cached_data
            
            logger.info(f"Query result for {checkout_request_id}: {result.get('ResultCode')}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Query timeout for {checkout_request_id}")
            return None
        except Exception as e:
            logger.error(f"Query transaction error: {e}", exc_info=True)
            return None
    
    def _get_user_friendly_error(self, error_message):
        """Convert technical errors to user-friendly messages"""
        error_map = {
            'insufficient funds': 'Insufficient M-Pesa balance. Please top up and try again.',
            'invalid phone': 'Invalid phone number. Please check and try again.',
            'transaction failed': 'Transaction failed. Please try again.',
            'user cancelled': 'Payment was cancelled.',
            'timeout': 'Request timeout. Please try again.',
            'invalid account': 'Invalid M-Pesa account.',
            'exceeds withdrawal': 'Amount exceeds M-Pesa limits.',
            'request cancelled': 'Payment request was cancelled.',
            'ds timeout': 'M-Pesa service timeout. Please try again.',
        }
        
        error_lower = error_message.lower()
        for key, friendly_msg in error_map.items():
            if key in error_lower:
                return friendly_msg
        
        return 'Payment failed. Please try again or contact support.'


def process_class_payment(booking, phone_number):
    """
    Process payment for class booking with enhanced security
    CRITICAL: Payment MUST complete before confirmation
    """
    mpesa = MPesaPayment()
    
    # Handle free trial
    if booking.booking_type == 'Free Trial':
        with db_transaction.atomic():
            booking.payment_status = 'Paid'
            booking.status = 'Confirmed'
            booking.amount_paid = 0
            booking.payment_date = timezone.now()
            booking.confirmed_at = timezone.now()
            booking.save()
            
            # Log payment
            from .models import PaymentLog
            PaymentLog.objects.create(
                booking=booking,
                action='free_trial_confirmed',
                status_code='FREE_TRIAL'
            )
        
        # Queue email
        try:
            from .emails import send_booking_confirmation_email
            if hasattr(send_booking_confirmation_email, 'delay'):
                send_booking_confirmation_email.delay(booking.id)
            else:
                from .emails import send_booking_confirmation_email_sync
                send_booking_confirmation_email_sync(booking.id)
        except Exception as e:
            logger.error(f"Failed to send free trial email: {e}")
        
        logger.info(f"✓ Free trial confirmed: {booking.booking_reference}")
        
        return {
            'success': True,
            'message': 'Free trial confirmed!',
            'is_free_trial': True,
            'booking_id': booking.id
        }
    
    # Validate amount
    amount = booking.karate_class.price
    if amount <= 0:
        return {
            'success': False,
            'error_code': 'INVALID_AMOUNT',
            'message': 'Invalid class price'
        }
    
    # Generate reference
    account_ref = f"{booking.booking_reference}"
    description = f"{booking.karate_class.title[:15]}"
    
    # Log attempt
    with db_transaction.atomic():
        booking.payment_attempts += 1
        booking.last_payment_attempt = timezone.now()
        booking.save()
        
        from .models import PaymentLog
        PaymentLog.objects.create(
            booking=booking,
            action='payment_initiated',
            status_code='INITIATED'
        )
    
    # Initiate STK push
    result = mpesa.stk_push(
        phone_number, 
        amount, 
        account_ref, 
        description,
        booking_id=booking.id
    )
    
    if result['success']:
        # Update booking with transaction details
        with db_transaction.atomic():
            booking.transaction_id = result['checkout_request_id']
            booking.phone_number = result['phone_number']
            booking.amount_paid = amount
            booking.payment_status = 'Pending'
            booking.status = 'Pending'
            # Set payment expiry (5 minutes)
            booking.expires_at = timezone.now() + timedelta(minutes=5)
            booking.save()
            
            from .models import PaymentLog
            PaymentLog.objects.create(
                booking=booking,
                transaction_id=result['checkout_request_id'],
                action='stk_push_sent',
                status_code='SUCCESS',
                response_data=result
            )
        
        logger.info(f"✓ Payment initiated: {booking.booking_reference} - {result['checkout_request_id']}")
        
        return {
            'success': True,
            'checkout_request_id': result['checkout_request_id'],
            'message': result['message'],
            'booking_id': booking.id
        }
    else:
        # Payment initiation failed
        with db_transaction.atomic():
            booking.payment_status = 'Failed'
            booking.status = 'Cancelled'
            booking.notes = f"Payment failed: {result.get('error_code', 'UNKNOWN')}"
            booking.cancelled_at = timezone.now()
            booking.save()
            
            from .models import PaymentLog
            PaymentLog.objects.create(
                booking=booking,
                action='stk_push_failed',
                status_code=result.get('error_code', 'FAILED'),
                response_data=result
            )
        
        logger.warning(f"✗ Payment initiation failed: {booking.booking_reference} - {result['message']}")
        
        return {
            'success': False,
            'error_code': result.get('error_code', 'PAYMENT_FAILED'),
            'message': result['message']
        }