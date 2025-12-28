# apps/accounts/forms.py - COMPLETE FILE
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import User, UserProfile, BeltProgress

# Get the custom user model
User = get_user_model()

# =============================================================================
# SHARED STYLING
# =============================================================================

# Consistent input styling across all forms
INPUT_CLASSES = (
    "w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] "
    "focus:border-[#FFCD00] focus:outline-none transition-colors"
)

SELECT_CLASSES = (
    "w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] "
    "focus:border-[#FFCD00] focus:outline-none transition-colors"
)

TEXTAREA_CLASSES = (
    "w-full px-4 py-3 rounded border-2 border-[#d6d3d1] text-[#525252] "
    "focus:border-[#FFCD00] focus:outline-none transition-colors resize-none"
)

CHECKBOX_CLASSES = (
    "w-5 h-5 text-[#FFCD00] border-[#d6d3d1] rounded focus:ring-[#FFCD00]"
)

FILE_INPUT_CLASSES = (
    "block w-full text-sm text-[#525252] "
    "file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 "
    "file:text-sm file:font-semibold file:bg-[#FFCD00] file:text-black "
    "hover:file:bg-[#FBBF24] transition-colors"
)


# =============================================================================
# OTP VERIFICATION FORMS
# =============================================================================

class OTPVerificationForm(forms.Form):
    """
    Form for entering OTP code
    """
    otp_code = forms.CharField(
        label="Verification Code",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}',
            'maxlength': '6',
        }),
        help_text="Enter the 6-digit code sent to your email"
    )
    
    email = forms.EmailField(widget=forms.HiddenInput())
    purpose = forms.CharField(widget=forms.HiddenInput(), initial='signup')
    
    def clean_otp_code(self):
        """
        Validate OTP code format
        """
        code = self.cleaned_data.get('otp_code')
        
        if not code:
            raise forms.ValidationError("Please enter the verification code.")
        
        # Remove spaces and validate
        code = code.replace(' ', '')
        
        if not code.isdigit():
            raise forms.ValidationError("Verification code must contain only numbers.")
        
        if len(code) != 6:
            raise forms.ValidationError("Verification code must be exactly 6 digits.")
        
        return code


class ResendOTPForm(forms.Form):
    """
    Form for resending OTP
    """
    email = forms.EmailField(widget=forms.HiddenInput())
    purpose = forms.CharField(widget=forms.HiddenInput(), initial='signup')


# =============================================================================
# USER REGISTRATION FORM WITH OTP
# =============================================================================

class UserRegisterForm(UserCreationForm):
    """
    User registration form with OTP verification
    """
    first_name = forms.CharField(
        label="First Name",
        max_length=50,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your first name",
            "class": INPUT_CLASSES,
        }),
        help_text="Required. Enter your first name."
    )

    last_name = forms.CharField(
        label="Last Name",
        max_length=50,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your last name",
            "class": INPUT_CLASSES,
        }),
        help_text="Required. Enter your last name."
    )

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            "placeholder": "you@example.com",
            "class": INPUT_CLASSES,
        }),
        help_text="Required. We'll send a verification code to this email."
    )

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Create a strong password",
            "class": INPUT_CLASSES,
        }),
        help_text="Must be at least 8 characters with letters and numbers."
    )

    password2 = forms.CharField(
        label="Confirm Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Re-enter your password",
            "class": INPUT_CLASSES,
        }),
        help_text="Enter the same password as before, for verification."
    )
    
    agree_terms = forms.BooleanField(
        required=True,
        label="I agree to the Terms of Service and Privacy Policy",
        widget=forms.CheckboxInput(attrs={
            "class": CHECKBOX_CLASSES,
        })
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password1", "password2"]

    def clean_email(self):
        """
        Validate email is unique and lowercase.
        """
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower()
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(
                    "This email address is already registered. Please use a different email or try logging in."
                )
        return email

    def clean_first_name(self):
        """
        Clean and capitalize first name.
        """
        first_name = self.cleaned_data.get("first_name")
        return first_name.strip().title() if first_name else ""

    def clean_last_name(self):
        """
        Clean and capitalize last name.
        """
        last_name = self.cleaned_data.get("last_name")
        return last_name.strip().title() if last_name else ""


# =============================================================================
# USER LOGIN FORM WITH OTP OPTION
# =============================================================================

class UserLoginForm(AuthenticationForm):
    """
    User login form with optional OTP verification
    """
    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        })
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )
    
    require_otp = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Email Address"

    def clean_username(self):
        """
        Convert email to lowercase for consistency.
        """
        username = self.cleaned_data.get('username')
        return username.lower() if username else username


# =============================================================================
# USER PROFILE FORM
# =============================================================================

class UserProfileForm(forms.ModelForm):
    """
    User profile form.
    Handles all extended user information including emergency contacts,
    belt level, training preferences, and notification settings.
    """
    class Meta:
        model = UserProfile
        fields = [
            "phone",
            "emergency_contact_name",
            "emergency_contact_phone",
            "belt_level",
            "date_of_birth",
            "gender",
            "address",
            "city",
            "country",
            "profile_picture",
            "bio",
            "preferred_training_time",
            "training_goals",
            "years_of_experience",
            "email_notifications",
            "sms_notifications",
        ]
        
        widgets = {
            "phone": forms.TextInput(attrs={
                "placeholder": "+254XXXXXXXXX",
                "class": INPUT_CLASSES,
            }),
            "emergency_contact_name": forms.TextInput(attrs={
                "placeholder": "Emergency contact name",
                "class": INPUT_CLASSES,
            }),
            "emergency_contact_phone": forms.TextInput(attrs={
                "placeholder": "+254XXXXXXXXX",
                "class": INPUT_CLASSES,
            }),
            "belt_level": forms.Select(attrs={
                "class": SELECT_CLASSES,
            }),
            "date_of_birth": forms.DateInput(attrs={
                "type": "date",
                "class": INPUT_CLASSES,
            }),
            "gender": forms.Select(attrs={
                "class": SELECT_CLASSES,
            }),
            "address": forms.TextInput(attrs={
                "placeholder": "Street address",
                "class": INPUT_CLASSES,
            }),
            "city": forms.TextInput(attrs={
                "placeholder": "City",
                "class": INPUT_CLASSES,
            }),
            "country": forms.TextInput(attrs={
                "placeholder": "Country",
                "class": INPUT_CLASSES,
            }),
            "bio": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Tell us about yourself...",
                "class": TEXTAREA_CLASSES,
            }),
            "preferred_training_time": forms.TextInput(attrs={
                "placeholder": "e.g., Mornings, Evenings",
                "class": INPUT_CLASSES,
            }),
            "training_goals": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "What are your training goals?",
                "class": TEXTAREA_CLASSES,
            }),
            "years_of_experience": forms.NumberInput(attrs={
                "class": INPUT_CLASSES,
                "min": 0,
            }),
            "profile_picture": forms.FileInput(attrs={
                "class": FILE_INPUT_CLASSES,
                "accept": "image/*",
            }),
            "email_notifications": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASSES,
            }),
            "sms_notifications": forms.CheckboxInput(attrs={
                "class": CHECKBOX_CLASSES,
            }),
        }

        labels = {
            "phone": "Phone Number",
            "emergency_contact_name": "Emergency Contact Name",
            "emergency_contact_phone": "Emergency Contact Phone",
            "belt_level": "Current Belt Level",
            "date_of_birth": "Date of Birth",
            "gender": "Gender",
            "address": "Address",
            "city": "City",
            "country": "Country",
            "profile_picture": "Profile Picture",
            "bio": "Bio",
            "preferred_training_time": "Preferred Training Time",
            "training_goals": "Training Goals",
            "years_of_experience": "Years of Experience",
            "email_notifications": "Email Notifications",
            "sms_notifications": "SMS Notifications",
        }

        help_texts = {
            "phone": "Include country code, e.g., +254712345678",
            "emergency_contact_phone": "Include country code",
            "bio": "Tell us about your karate journey (max 500 characters)",
            "training_goals": "What do you want to achieve?",
            "email_notifications": "Receive updates about classes and events via email",
            "sms_notifications": "Receive SMS notifications (carrier charges may apply)",
        }


# =============================================================================
# USER ACCOUNT FORM
# =============================================================================

class UserAccountForm(forms.ModelForm):
    """
    Basic user account information form.
    For updating name and email.
    """
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        
        widgets = {
            "first_name": forms.TextInput(attrs={
                "placeholder": "First name",
                "class": INPUT_CLASSES,
            }),
            "last_name": forms.TextInput(attrs={
                "placeholder": "Last name",
                "class": INPUT_CLASSES,
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Email address",
                "class": INPUT_CLASSES,
            }),
        }

    def clean_email(self):
        """
        Validate email is unique (excluding current user).
        """
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower()
            # Exclude current user from uniqueness check
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This email is already in use.")
        return email


# =============================================================================
# BELT PROGRESS FORM
# =============================================================================

class BeltProgressForm(forms.ModelForm):
    """
    Belt progress recording form.
    Used by instructors to record belt achievements.
    """
    class Meta:
        model = BeltProgress
        fields = [
            "user",
            "current_belt",
            "achieved_on",
            "next_goal",
            "notes",
            "instructor",
            "certificate_url",
            "test_score",
        ]
        
        widgets = {
            "user": forms.Select(attrs={
                "class": SELECT_CLASSES,
            }),
            "current_belt": forms.Select(attrs={
                "class": SELECT_CLASSES,
            }),
            "achieved_on": forms.DateInput(attrs={
                "type": "date",
                "class": INPUT_CLASSES,
            }),
            "next_goal": forms.Select(attrs={
                "class": SELECT_CLASSES,
            }),
            "notes": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Add notes about this achievement...",
                "class": TEXTAREA_CLASSES,
            }),
            "instructor": forms.Select(attrs={
                "class": SELECT_CLASSES,
            }),
            "certificate_url": forms.URLInput(attrs={
                "placeholder": "https://",
                "class": INPUT_CLASSES,
            }),
            "test_score": forms.NumberInput(attrs={
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0",
                "max": "100",
                "class": INPUT_CLASSES,
            }),
        }

        labels = {
            "user": "Student",
            "current_belt": "Belt Achieved",
            "achieved_on": "Achievement Date",
            "next_goal": "Next Goal",
            "notes": "Notes",
            "instructor": "Instructor",
            "certificate_url": "Certificate URL",
            "test_score": "Test Score (%)",
        }


# =============================================================================
# PASSWORD CHANGE FORM
# =============================================================================

class PasswordChangeForm(forms.Form):
    """
    Password change form.
    Requires current password and new password confirmation.
    """
    old_password = forms.CharField(
        label="Current Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Enter your current password",
            "class": INPUT_CLASSES,
            "autocomplete": "current-password",
        })
    )
    
    new_password1 = forms.CharField(
        label="New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Enter new password",
            "class": INPUT_CLASSES,
            "autocomplete": "new-password",
        }),
        help_text="Must be at least 8 characters with letters and numbers."
    )
    
    new_password2 = forms.CharField(
        label="Confirm New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Confirm new password",
            "class": INPUT_CLASSES,
            "autocomplete": "new-password",
        })
    )

    def clean(self):
        """
        Validate that both new passwords match.
        """
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError(
                    "The two password fields didn't match. Please try again."
                )
        
        return cleaned_data

    def clean_new_password1(self):
        """
        Validate password strength.
        """
        password = self.cleaned_data.get('new_password1')
        
        if password:
            # Check minimum length
            if len(password) < 8:
                raise forms.ValidationError(
                    "Password must be at least 8 characters long."
                )
            
            # Check for at least one letter and one number
            has_letter = any(c.isalpha() for c in password)
            has_number = any(c.isdigit() for c in password)
            
            if not (has_letter and has_number):
                raise forms.ValidationError(
                    "Password must contain both letters and numbers."
                )
        
        return password


# =============================================================================
# SEARCH/FILTER FORMS (Optional)
# =============================================================================

class UserSearchForm(forms.Form):
    """
    User search form for admin/instructor use.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Search by name or email...",
            "class": INPUT_CLASSES,
        })
    )
    
    belt_level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Belts')] + UserProfile.BELT_LEVELS,
        widget=forms.Select(attrs={
            "class": SELECT_CLASSES,
        })
    )
    
    is_instructor = forms.BooleanField(
        required=False,
        label="Instructors Only",
        widget=forms.CheckboxInput(attrs={
            "class": CHECKBOX_CLASSES,
        })
    )