# apps/accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile, TrainingStats

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile and TrainingStats when a new user is created.
    This signal is triggered after a User instance is saved.
    """
    if created:
        # Create UserProfile for the new user
        UserProfile.objects.get_or_create(user=instance)
        
        # Create TrainingStats for the new user
        TrainingStats.objects.get_or_create(user=instance)
        
        print(f"✅ Profile and Stats created for user: {instance.email}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Ensure the profile is saved when the user is saved.
    This handles cases where the profile might exist but needs updating.
    """
    # Only try to save if profile exists
    if hasattr(instance, 'profile'):
        instance.profile.save()