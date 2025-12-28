# management/commands/load_advanced_sample_data.py
# Additional advanced sample data generator
# Run with: python manage.py load_advanced_sample_data

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, time
from decimal import Decimal
import random

from apps.accounts.models import UserProfile, BeltProgress, TrainingStats
from apps.core.models import Instructor, Achievement
from apps.classes.models import KarateClass, ClassSchedule, Booking, PaymentLog
from apps.blog.models import BlogPost, Comment

User = get_user_model()


class Command(BaseCommand):
    help = 'Load advanced sample data including edge cases and complex scenarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scenario',
            type=str,
            default='all',
            help='Scenario to load: all, payment_failures, cancellations, high_volume'
        )

    def handle(self, *args, **kwargs):
        scenario = kwargs['scenario']
        
        self.stdout.write(self.style.SUCCESS(f'Loading advanced scenario: {scenario}'))
        
        if scenario == 'all' or scenario == 'payment_failures':
            self.create_payment_failure_scenarios()
        
        if scenario == 'all' or scenario == 'cancellations':
            self.create_cancellation_scenarios()
        
        if scenario == 'all' or scenario == 'high_volume':
            self.create_high_volume_booking_scenarios()
        
        if scenario == 'all' or scenario == 'expired_payments':
            self.create_expired_payment_scenarios()
        
        if scenario == 'all' or scenario == 'competitive_members':
            self.create_competitive_member_profiles()
        
        self.stdout.write(self.style.SUCCESS('✅ Advanced sample data loaded!'))

    def create_payment_failure_scenarios(self):
        """Create bookings with various payment failure scenarios"""
        self.stdout.write('Creating payment failure scenarios...')
        
        users = User.objects.filter(is_member=True)[:3]
        classes = KarateClass.objects.all()[:2]
        
        failure_scenarios = [
            {
                'status': 'Pending',
                'payment_status': 'Failed',
                'response': {
                    'ResultCode': '1032',
                    'ResultDesc': 'Request cancelled by user'
                },
                'action': 'failed'
            },
            {
                'status': 'Pending',
                'payment_status': 'Failed',
                'response': {
                    'ResultCode': '1',
                    'ResultDesc': 'Insufficient balance'
                },
                'action': 'failed'
            },
            {
                'status': 'Pending',
                'payment_status': 'Failed',
                'response': {
                    'ResultCode': '1037',
                    'ResultDesc': 'Timeout in completing transaction'
                },
                'action': 'failed'
            }
        ]
        
        for user in users:
            for karate_class in classes[:1]:
                if karate_class.schedules.exists():
                    schedule = karate_class.schedules.first()
                    scenario = random.choice(failure_scenarios)
                    
                    booking = Booking.objects.create(
                        user=user,
                        karate_class=karate_class,
                        schedule=schedule,
                        booking_type='Monthly',
                        status=scenario['status'],
                        payment_status=scenario['payment_status'],
                        amount_paid=Decimal('0.00'),
                        phone_number=user.profile.phone if hasattr(user, 'profile') else None,
                        payment_attempts=random.randint(1, 3),
                        last_payment_attempt=timezone.now() - timedelta(minutes=random.randint(5, 30))
                    )
                    
                    # Create payment log
                    PaymentLog.objects.create(
                        booking=booking,
                        action=scenario['action'],
                        status_code=scenario['response']['ResultCode'],
                        response_data=scenario['response'],
                        ip_address='197.156.240.1',
                        created_at=booking.last_payment_attempt
                    )
        
        self.stdout.write('  Created payment failure scenarios')

    def create_cancellation_scenarios(self):
        """Create cancelled bookings with various reasons"""
        self.stdout.write('Creating cancellation scenarios...')
        
        users = User.objects.filter(is_member=True)[:2]
        classes = KarateClass.objects.all()[:2]
        
        cancellation_reasons = [
            'Schedule conflict - had to work',
            'Personal emergency',
            'Moved to different city',
            'Financial constraints',
            'Health issues - doctor advised rest',
            'Switched to different class time'
        ]
        
        for user in users:
            for karate_class in classes[:1]:
                if karate_class.schedules.exists():
                    schedule = karate_class.schedules.first()
                    
                    booking = Booking.objects.create(
                        user=user,
                        karate_class=karate_class,
                        schedule=schedule,
                        booking_type='Monthly',
                        status='Cancelled',
                        payment_status='Refunded',
                        amount_paid=karate_class.price,
                        transaction_id=f"TXN{random.randint(100000, 999999)}",
                        mpesa_receipt_number=f"MPE{random.randint(1000000000, 9999999999)}",
                        phone_number=user.profile.phone if hasattr(user, 'profile') else None,
                        booked_at=timezone.now() - timedelta(days=random.randint(10, 30)),
                        cancelled_at=timezone.now() - timedelta(days=random.randint(1, 5)),
                        notes=f"Cancellation reason: {random.choice(cancellation_reasons)}"
                    )
        
        self.stdout.write('  Created cancellation scenarios')

    def create_expired_payment_scenarios(self):
        """Create bookings that expired due to payment timeout"""
        self.stdout.write('Creating expired payment scenarios...')
        
        users = User.objects.filter(is_member=True)[:2]
        classes = KarateClass.objects.all()[:2]
        
        for user in users:
            for karate_class in classes[:1]:
                if karate_class.schedules.exists():
                    schedule = karate_class.schedules.first()
                    
                    booked_time = timezone.now() - timedelta(hours=random.randint(2, 24))
                    
                    booking = Booking.objects.create(
                        user=user,
                        karate_class=karate_class,
                        schedule=schedule,
                        booking_type='Monthly',
                        status='Expired',
                        payment_status='Failed',
                        amount_paid=Decimal('0.00'),
                        phone_number=user.profile.phone if hasattr(user, 'profile') else None,
                        booked_at=booked_time,
                        expires_at=booked_time + timedelta(hours=1),
                        notes='Expired due to payment timeout'
                    )
        
        self.stdout.write('  Created expired payment scenarios')

    def create_high_volume_booking_scenarios(self):
        """Create multiple bookings to simulate high activity"""
        self.stdout.write('Creating high volume booking scenarios...')
        
        users = list(User.objects.filter(is_member=True)[:5])
        classes = list(KarateClass.objects.all())
        
        # Create 20 random bookings
        for _ in range(20):
            user = random.choice(users)
            karate_class = random.choice(classes)
            
            if karate_class.schedules.exists():
                schedule = random.choice(list(karate_class.schedules.all()))
                
                booking_type = random.choice(['Monthly', 'Monthly', 'Drop-in'])
                status = random.choice(['Confirmed', 'Confirmed', 'Pending'])
                
                booking = Booking.objects.create(
                    user=user,
                    karate_class=karate_class,
                    schedule=schedule,
                    booking_type=booking_type,
                    status=status,
                    payment_status='Paid' if status == 'Confirmed' else 'Pending',
                    amount_paid=karate_class.price if status == 'Confirmed' else Decimal('0.00'),
                    phone_number=user.profile.phone if hasattr(user, 'profile') else None,
                    booked_at=timezone.now() - timedelta(
                        days=random.randint(0, 60),
                        hours=random.randint(0, 23)
                    )
                )
                
                if status == 'Confirmed':
                    booking.transaction_id = f"TXN{random.randint(100000, 999999)}"
                    booking.mpesa_receipt_number = f"MPE{random.randint(1000000000, 9999999999)}"
                    booking.save()
        
        self.stdout.write('  Created high volume booking scenarios')

    def create_competitive_member_profiles(self):
        """Create members with competitive training profiles"""
        self.stdout.write('Creating competitive member profiles...')
        
        competitive_users_data = [
            {
                'email': 'champion1@example.com',
                'first_name': 'Alex',
                'last_name': 'Kimutai',
                'password': 'Password123!',
                'profile': {
                    'phone': '+254767890123',
                    'belt_level': 'Black',
                    'date_of_birth': datetime(1997, 5, 20).date(),
                    'gender': 'M',
                    'city': 'Nairobi',
                    'years_of_experience': 8,
                    'training_goals': 'Olympic qualification and world championship'
                }
            },
            {
                'email': 'fighter2@example.com',
                'first_name': 'Mercy',
                'last_name': 'Achieng',
                'password': 'Password123!',
                'profile': {
                    'phone': '+254778901234',
                    'belt_level': 'Brown',
                    'date_of_birth': datetime(1999, 8, 14).date(),
                    'gender': 'F',
                    'city': 'Nairobi',
                    'years_of_experience': 6,
                    'training_goals': 'National championship gold medal'
                }
            }
        ]
        
        for user_data in competitive_users_data:
            profile_data = user_data.pop('profile')
            user = User.objects.create_user(**user_data)
            user.email_verified = True
            user.save()
            
            UserProfile.objects.create(user=user, **profile_data)
            
            # Create impressive training stats
            TrainingStats.objects.create(
                user=user,
                total_classes_attended=random.randint(300, 500),
                total_training_hours=Decimal(random.randint(500, 1000)),
                current_streak_days=random.randint(50, 120),
                longest_streak_days=random.randint(100, 200),
                last_training_date=timezone.now().date(),
                tournaments_participated=random.randint(10, 25),
                tournaments_won=random.randint(5, 15)
            )
            
            self.stdout.write(f'  Created competitive member: {user.email}')
        
        self.stdout.write('  Created competitive member profiles')

    def create_bulk_comments(self):
        """Create additional comments for engagement"""
        self.stdout.write('Creating bulk comments...')
        
        posts = BlogPost.objects.filter(status='published')
        users = list(User.objects.all()[:5])
        
        comment_templates = [
            "This is really helpful, thanks for sharing!",
            "Great article! Looking forward to more content like this.",
            "I tried these tips and they really work!",
            "Excellent explanation, very clear and easy to follow.",
            "This motivated me to train harder. Thank you!",
            "Can you write more about this topic?",
            "Shared this with my training partners!",
            "Exactly what I needed to read today.",
        ]
        
        for post in posts:
            num_comments = random.randint(2, 5)
            for _ in range(num_comments):
                if random.random() > 0.5 and users:
                    # Authenticated comment
                    Comment.objects.create(
                        post=post,
                        author=random.choice(users),
                        content=random.choice(comment_templates),
                        approved=True
                    )
                else:
                    # Guest comment
                    Comment.objects.create(
                        post=post,
                        name=f"Guest{random.randint(100, 999)}",
                        email=f"guest{random.randint(100, 999)}@example.com",
                        content=random.choice(comment_templates),
                        approved=random.choice([True, True, False])
                    )
        
        self.stdout.write('  Created bulk comments')