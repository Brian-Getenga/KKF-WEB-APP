from django import forms
from .models import Testimonial, InstructorReview


class ContactForm(forms.Form):
    """Contact form for the website"""
    
    SUBJECT_CHOICES = [
        ('', 'Select a subject'),
        ('general', 'General Inquiry'),
        ('classes', 'Classes Information'),
        ('membership', 'Membership'),
        ('schedule', 'Schedule & Timing'),
        ('competitions', 'Competitions'),
        ('partnership', 'Partnership Opportunities'),
        ('other', 'Other'),
    ]
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-white border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
            'placeholder': 'John Doe'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 bg-white border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
            'placeholder': 'john@example.com'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-white border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
            'placeholder': '+254 700 000 000'
        })
    )
    
    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 bg-white border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 bg-white border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none resize-none',
            'rows': 6,
            'placeholder': 'Tell us how we can help you...'
        })
    )
    
    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if not subject:
            raise forms.ValidationError('Please select a subject.')
        return subject


class TestimonialForm(forms.ModelForm):
    """Form for submitting testimonials"""
    
    class Meta:
        model = Testimonial
        fields = ['name', 'email', 'belt_rank', 'photo', 'title', 'message', 'rating', 'instructor']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'placeholder': 'Your Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'placeholder': 'your@email.com'
            }),
            'belt_rank': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'placeholder': 'e.g., Green Belt, 2nd Dan'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'placeholder': 'Short highlight of your experience'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'rows': 5,
                'placeholder': 'Share your experience with us...'
            }),
            'rating': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none'
            }, choices=[(i, f'{i} Stars') for i in range(1, 6)]),
            'instructor': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none'
            }),
        }


class InstructorReviewForm(forms.ModelForm):
    """Form for reviewing instructors"""
    
    class Meta:
        model = InstructorReview
        fields = [
            'teaching_quality', 'communication', 'technique', 
            'motivation', 'review_text', 'pros', 'cons'
        ]
        widgets = {
            'teaching_quality': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'communication': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'technique': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'motivation': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            'review_text': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'rows': 5,
                'placeholder': 'Write your detailed review...'
            }),
            'pros': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'rows': 3,
                'placeholder': 'What did you like most?'
            }),
            'cons': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 focus:border-[#FFCD00] focus:outline-none',
                'rows': 3,
                'placeholder': 'What could be improved?'
            }),
        }