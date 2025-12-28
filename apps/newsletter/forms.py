
# ============================================================================
# newsletter/forms.py - COMPLETE VERSION
# ============================================================================

from django import forms
from django.core.validators import EmailValidator
from .models import Subscriber


class SubscribeForm(forms.ModelForm):
    """Form for newsletter subscription"""
    
    email = forms.EmailField(
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={
            'class': 'form-control newsletter-email-input',
            'placeholder': 'Enter your email',
            'required': True,
            'aria-label': 'Email address'
        })
    )
    
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control newsletter-name-input',
            'placeholder': 'Your name (optional)',
            'aria-label': 'Name'
        })
    )
    
    preferences = forms.ChoiceField(
        choices=Subscriber.PREFERENCE_CHOICES,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-control newsletter-preferences-select',
            'aria-label': 'Email preferences'
        })
    )
    
    # Honeypot field for bot protection
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'style': 'display:none;',
            'tabindex': '-1',
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = Subscriber
        fields = ['email', 'name', 'preferences']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if Subscriber.objects.filter(email=email, is_active=True).exists():
                raise forms.ValidationError('This email is already subscribed to our newsletter.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('website'):
            raise forms.ValidationError('Invalid submission detected.')
        return cleaned_data


class UnsubscribeForm(forms.Form):
    """Form for confirming unsubscription"""
    
    confirm = forms.BooleanField(
        required=True,
        label='I want to unsubscribe from all emails',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )