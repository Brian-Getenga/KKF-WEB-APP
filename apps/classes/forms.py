"""
apps/classes/forms.py - Form Definitions
"""
from django import forms
from .models import Booking, ClassReview, ClassSchedule


class ClassFilterForm(forms.Form):
    """Form for filtering classes"""
    CATEGORY_CHOICES = [
        ('', 'All Categories'),
        ('Kids', 'Kids (5-12)'),
        ('Teens', 'Teens (13-17)'),
        ('Adults', 'Adults (18+)'),
        ('Private', 'Private Lessons'),
    ]
    
    LEVEL_CHOICES = [
        ('', 'All Levels'),
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('Competition', 'Competition Team'),
    ]
    
    SORT_CHOICES = [
        ('', 'Sort By'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low'),
        ('rating', 'Highest Rated'),
    ]
    
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border-2 border-[#d6d3d1] rounded-lg focus:border-[#FFCD00] focus:outline-none'
        })
    )
    
    level = forms.ChoiceField(
        choices=LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border-2 border-[#d6d3d1] rounded-lg focus:border-[#FFCD00] focus:outline-none'
        })
    )
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border-2 border-[#d6d3d1] rounded-lg focus:border-[#FFCD00] focus:outline-none'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search classes...',
            'class': 'w-full px-4 py-2 border-2 border-[#d6d3d1] rounded-lg focus:border-[#FFCD00] focus:outline-none'
        })
    )


class BookingForm(forms.ModelForm):
    """Form for creating bookings"""
    BOOKING_TYPE_CHOICES = [
        ('Free Trial', 'Free Trial - First Class Free'),
        ('Monthly', 'Monthly Subscription'),
        ('Drop-in', 'Drop-in Class'),
    ]
    
    schedule = forms.ModelChoiceField(
        queryset=ClassSchedule.objects.none(),
        empty_label="Select a schedule",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border-2 border-[#d6d3d1] rounded-xl focus:border-[#FFCD00] focus:outline-none font-semibold text-[#525252]'
        })
    )
    
    booking_type = forms.ChoiceField(
        choices=BOOKING_TYPE_CHOICES,
        initial='Monthly',
        widget=forms.RadioSelect(attrs={
            'class': 'text-[#FFCD00]'
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'placeholder': '254712345678',
            'class': 'w-full px-4 py-3 border-2 border-[#d6d3d1] rounded-xl focus:border-[#FFCD00] focus:outline-none font-semibold text-[#525252]'
        }),
        help_text='Format: 254712345678'
    )
    
    class Meta:
        model = Booking
        fields = ['schedule', 'booking_type', 'phone_number']
    
    def __init__(self, *args, **kwargs):
        karate_class = kwargs.pop('karate_class', None)
        super().__init__(*args, **kwargs)
        
        if karate_class:
            self.fields['schedule'].queryset = karate_class.schedules.filter(is_active=True)
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Validate format
        if not phone.startswith('254') or len(phone) != 12:
            raise forms.ValidationError(
                'Invalid phone number. Please use format: 254712345678'
            )
        
        return phone


class PaymentForm(forms.Form):
    """Form for payment processing"""
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'placeholder': '254712345678',
            'class': 'w-full px-4 py-3 border-2 border-[#d6d3d1] rounded-xl focus:border-[#FFCD00] focus:outline-none'
        })
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        phone = ''.join(filter(str.isdigit, phone))
        
        if not phone.startswith('254') or len(phone) != 12:
            raise forms.ValidationError(
                'Invalid phone number. Format: 254712345678'
            )
        
        return phone


class ReviewForm(forms.ModelForm):
    """Form for adding class reviews"""
    class Meta:
        model = ClassReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)],
                attrs={
                    'class': 'w-full px-4 py-3 border-2 border-[#d6d3d1] rounded-xl focus:border-[#FFCD00] focus:outline-none'
                }
            ),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share your experience with this class...',
                'class': 'w-full px-4 py-3 border-2 border-[#d6d3d1] rounded-xl focus:border-[#FFCD00] focus:outline-none'
            })
        }
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise forms.ValidationError('Rating must be between 1 and 5 stars.')
        return rating
    
    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        if len(comment) < 10:
            raise forms.ValidationError('Please provide a more detailed review (at least 10 characters).')
        return comment