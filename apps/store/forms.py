from django import forms
from .models import Order, ProductReview
from django.core.validators import RegexValidator


class CheckoutForm(forms.ModelForm):
    phone_validator = RegexValidator(
        regex=r'^254\d{9}$',
        message="Phone number must be in format: 254XXXXXXXXX"
    )
    
    mpesa_phone = forms.CharField(
        max_length=12,
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
            'placeholder': '254712345678'
        })
    )
    
    class Meta:
        model = Order
        fields = [
            'payment_method', 'shipping_name', 'shipping_email', 'shipping_phone',
            'shipping_address', 'shipping_city', 'shipping_postal_code', 'delivery_notes'
        ]
        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black focus:border-[#FFCD00] focus:outline-none transition-colors'
            }),
            'shipping_name': forms.TextInput(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Full Name'
            }),
            'shipping_email': forms.EmailInput(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'email@example.com'
            }),
            'shipping_phone': forms.TextInput(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': '0700123456'
            }),
            'shipping_address': forms.TextInput(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Street Address'
            }),
            'shipping_city': forms.TextInput(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'City'
            }),
            'shipping_postal_code': forms.TextInput(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Postal Code (Optional)'
            }),
            'delivery_notes': forms.Textarea(attrs={
                'class': 'w-full px-6 py-4 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors resize-none',
                'rows': 3,
                'placeholder': 'Special delivery instructions (Optional)'
            }),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-[#d6d3d1] text-black focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Summary of your review'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-[#d6d3d1] text-black focus:border-[#FFCD00] focus:outline-none transition-colors resize-none',
                'rows': 5,
                'placeholder': 'Tell us about your experience with this product'
            }),
        }


class CouponForm(forms.Form):
    coupon_code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'flex-1 px-6 py-3 border-2 border-[#d6d3d1] text-black placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors uppercase',
            'placeholder': 'Enter coupon code'
        })
    )