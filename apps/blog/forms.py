from django import forms
from django.core.validators import EmailValidator
from .models import Comment, Newsletter


class CommentForm(forms.ModelForm):
    """Form for posting comments with custom styling"""
    
    class Meta:
        model = Comment
        fields = ['name', 'email', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Your name',
                'required': False  # Will be required for non-authenticated users in view
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Your email (optional, won\'t be published)',
                'required': False
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors resize-none',
                'rows': 4,
                'placeholder': 'Share your thoughts...',
                'required': True
            })
        }
        labels = {
            'name': 'Name',
            'email': 'Email (optional)',
            'content': 'Comment'
        }

    def clean_content(self):
        """Validate comment content"""
        content = self.cleaned_data.get('content')
        if content:
            content = content.strip()
            if len(content) < 3:
                raise forms.ValidationError("Comment must be at least 3 characters long.")
            if len(content) > 2000:
                raise forms.ValidationError("Comment cannot exceed 2000 characters.")
        return content

    def clean_email(self):
        """Validate email if provided"""
        email = self.cleaned_data.get('email')
        if email:
            validator = EmailValidator()
            validator(email)
        return email


class NewsletterForm(forms.ModelForm):
    """Form for newsletter subscription"""
    
    class Meta:
        model = Newsletter
        fields = ['email', 'name']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Enter your email',
                'required': True
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
                'placeholder': 'Your name (optional)',
                'required': False
            })
        }
        labels = {
            'email': 'Email Address',
            'name': 'Name'
        }

    def clean_email(self):
        """Validate and normalize email"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
        return email


class SearchForm(forms.Form):
    """Search form for blog posts"""
    q = forms.CharField(
        max_length=200,
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
            'placeholder': 'Search articles...',
            'type': 'search'
        })
    )

    def clean_q(self):
        """Clean and validate search query"""
        query = self.cleaned_data.get('q')
        if query:
            query = query.strip()
        return query


class ContactForm(forms.Form):
    """Optional contact form for blog inquiries"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
            'placeholder': 'Your name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
            'placeholder': 'Your email'
        })
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors',
            'placeholder': 'Subject'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] placeholder-[#525252] focus:border-[#FFCD00] focus:outline-none transition-colors resize-none',
            'rows': 6,
            'placeholder': 'Your message'
        })
    )

    def clean_message(self):
        """Validate message content"""
        message = self.cleaned_data.get('message')
        if len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        return message