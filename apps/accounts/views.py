# apps/accounts/views.py - COMPLETE FILE WITH OTP
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from .models import User, UserProfile, BeltProgress, TrainingStats, OTPVerification
from .forms import (
    UserRegisterForm, UserLoginForm, UserProfileForm, 
    UserAccountForm, BeltProgressForm, PasswordChangeForm,
    OTPVerificationForm, ResendOTPForm
)
from .utils import send_otp_email, send_otp_sms, validate_otp_code


# =============================================================================
# OTP VERIFICATION VIEWS
# =============================================================================

def verify_otp_view(request):
    """
    Verify OTP code entered by user
    Handles both signup and login OTP verification
    """
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            otp_code = form.cleaned_data['otp_code']
            purpose = form.cleaned_data['purpose']
            
            # Verify OTP
            success, message, otp_instance = OTPVerification.verify_otp(
                email=email,
                otp_code=otp_code,
                purpose=purpose
            )
            
            if success:
                messages.success(request, message)
                
                # Handle based on purpose
                if purpose == 'signup':
                    # Get user data from session
                    user_data = request.session.get('pending_user_data')
                    
                    if not user_data:
                        messages.error(request, "Session expired. Please sign up again.")
                        return redirect('accounts:signup')
                    
                    # Create the user account
                    try:
                        user = User.objects.create_user(
                            email=user_data['email'],
                            password=user_data['password'],
                            first_name=user_data['first_name'],
                            last_name=user_data['last_name'],
                            email_verified=True
                        )
                        
                        # Create profile and stats
                        UserProfile.objects.get_or_create(user=user)
                        TrainingStats.objects.get_or_create(user=user)
                        
                        # Clear session data
                        del request.session['pending_user_data']
                        if 'otp_email' in request.session:
                            del request.session['otp_email']
                        if 'otp_purpose' in request.session:
                            del request.session['otp_purpose']
                        
                        # Log user in
                        user.backend = 'django.contrib.auth.backends.ModelBackend'
                        login(request, user)
                        
                        messages.success(
                            request, 
                            f"Welcome to KKF, {user.first_name}! Your account has been created successfully."
                        )
                        return redirect('accounts:dashboard')
                        
                    except Exception as e:
                        messages.error(request, f"Error creating account: {str(e)}")
                        return redirect('accounts:signup')
                
                elif purpose == 'login':
                    # Get user credentials from session
                    login_data = request.session.get('pending_login_data')
                    
                    if not login_data:
                        messages.error(request, "Session expired. Please log in again.")
                        return redirect('accounts:login')
                    
                    # Authenticate and log in
                    user = authenticate(
                        request,
                        username=login_data['email'],
                        password=login_data['password']
                    )
                    
                    if user:
                        login(request, user)
                        user.last_active = timezone.now()
                        user.save(update_fields=['last_active'])
                        
                        # Clear session data
                        del request.session['pending_login_data']
                        if 'otp_email' in request.session:
                            del request.session['otp_email']
                        if 'otp_purpose' in request.session:
                            del request.session['otp_purpose']
                        
                        messages.success(request, f"Welcome back, {user.first_name}!")
                        
                        # Redirect to next or dashboard
                        next_url = request.session.pop('next_url', None)
                        return redirect(next_url or 'accounts:dashboard')
                    else:
                        messages.error(request, "Authentication failed. Please try again.")
                        return redirect('accounts:login')
            
            else:
                messages.error(request, message)
    
    else:
        # GET request - check if we have email in session
        email = request.session.get('otp_email')
        purpose = request.session.get('otp_purpose', 'signup')
        
        if not email:
            messages.error(request, "No verification pending.")
            return redirect('accounts:signup')
        
        form = OTPVerificationForm(initial={'email': email, 'purpose': purpose})
    
    context = {
        'form': form,
        'email': request.session.get('otp_email', ''),
        'purpose': request.session.get('otp_purpose', 'signup'),
    }
    
    return render(request, 'accounts/verify_otp.html', context)


@require_http_methods(["POST"])
def resend_otp_view(request):
    """
    Resend OTP code to user's email
    """
    form = ResendOTPForm(request.POST)
    
    if form.is_valid():
        email = form.cleaned_data['email']
        purpose = form.cleaned_data['purpose']
        
        # Create new OTP
        otp = OTPVerification.create_otp(email=email, purpose=purpose)
        
        # Send OTP email
        success = send_otp_email(
            email=email,
            otp_code=otp.otp_code,
            purpose=purpose
        )
        
        if success:
            messages.success(request, "A new verification code has been sent to your email.")
        else:
            messages.error(request, "Failed to send verification code. Please try again.")
    
    return redirect('accounts:verify_otp')


# =============================================================================
# AUTHENTICATION VIEWS WITH OTP
# =============================================================================

class RegisterView(CreateView):
    """
    Handle user registration with OTP verification
    """
    template_name = "accounts/signup.html"
    form_class = UserRegisterForm
    success_url = reverse_lazy("accounts:verify_otp")

    def form_valid(self, form):
        """
        Store user data in session and send OTP
        Don't create user yet - wait for OTP verification
        """
        email = form.cleaned_data['email']
        
        # Store user data in session (temporarily)
        self.request.session['pending_user_data'] = {
            'email': email,
            'password': form.cleaned_data['password1'],
            'first_name': form.cleaned_data['first_name'],
            'last_name': form.cleaned_data['last_name'],
        }
        
        # Store OTP info in session
        self.request.session['otp_email'] = email
        self.request.session['otp_purpose'] = 'signup'
        
        # Create OTP
        otp = OTPVerification.create_otp(email=email, purpose='signup')
        
        # Send OTP email
        success = send_otp_email(
            email=email,
            otp_code=otp.otp_code,
            purpose='signup',
            user_name=form.cleaned_data['first_name']
        )
        
        if success:
            messages.info(
                self.request,
                f"A verification code has been sent to {email}. Please check your inbox."
            )
        else:
            messages.warning(
                self.request,
                "Failed to send verification email. Please contact support."
            )
        
        return redirect('accounts:verify_otp')

    def dispatch(self, request, *args, **kwargs):
        """
        Redirect authenticated users away from signup page.
        """
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)


class LoginView(DjangoLoginView):
    """
    Handle user login with optional OTP verification
    """
    template_name = "accounts/login.html"
    authentication_form = UserLoginForm

    def form_valid(self, form):
        """
        Authenticate user and optionally require OTP
        """
        user = form.get_user()
        email = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        # Check if user has OTP enabled (you can add this to UserProfile)
        # For now, we'll make OTP optional based on a setting
        from django.conf import settings
        require_login_otp = getattr(settings, 'REQUIRE_LOGIN_OTP', False)
        
        if require_login_otp:
            # Store login credentials in session
            self.request.session['pending_login_data'] = {
                'email': email,
                'password': password,
            }
            
            # Store OTP info
            self.request.session['otp_email'] = email
            self.request.session['otp_purpose'] = 'login'
            
            # Store next URL if present
            next_url = self.request.GET.get('next')
            if next_url:
                self.request.session['next_url'] = next_url
            
            # Create and send OTP
            otp = OTPVerification.create_otp(email=email, purpose='login', user=user)
            
            success = send_otp_email(
                email=email,
                otp_code=otp.otp_code,
                purpose='login',
                user_name=user.first_name
            )
            
            if success:
                messages.info(
                    self.request,
                    "A verification code has been sent to your email for security."
                )
            else:
                messages.warning(
                    self.request,
                    "Failed to send verification code. Logging you in without OTP."
                )
                # Fallback: log in without OTP
                login(self.request, user)
                user.last_active = timezone.now()
                user.save(update_fields=['last_active'])
                return redirect('accounts:dashboard')
            
            return redirect('accounts:verify_otp')
        
        else:
            # Normal login without OTP
            login(self.request, user)
            user.last_active = timezone.now()
            user.save(update_fields=['last_active'])
            
            messages.success(self.request, f"Welcome back, {user.first_name}!")
            
            next_url = self.request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect("accounts:dashboard")

    def dispatch(self, request, *args, **kwargs):
        """
        Redirect authenticated users away from login page.
        """
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)


@login_required
def logout_view(request):
    """
    Handle user logout.
    """
    user_name = request.user.first_name
    logout(request)
    messages.info(request, f"Goodbye, {user_name}! You have been logged out successfully.")
    return redirect("core:home")


# =============================================================================
# DASHBOARD & PROFILE VIEWS
# =============================================================================

@login_required
def dashboard_view(request):
    """
    User dashboard showing overview of activity.
    """
    user = request.user
    profile = user.profile
    
    training_stats, _ = TrainingStats.objects.get_or_create(user=user)
    belt_history = BeltProgress.objects.filter(user=user).order_by("-achieved_on")[:5]
    
    bookings = []
    try:
        from apps.classes.models import Booking
        bookings = Booking.objects.filter(user=user).order_by('-booked_at')[:5]
    except (ImportError, Exception):
        pass
    
    orders = []
    try:
        from apps.store.models import Order
        orders = Order.objects.filter(user=user).order_by('-created_at')[:5]
    except (ImportError, Exception):
        pass
    
    profile_completion = _calculate_profile_completion(profile)
    
    context = {
        "profile": profile,
        "training_stats": training_stats,
        "belt_history": belt_history,
        "bookings": bookings,
        "orders": orders,
        "profile_completion": profile_completion,
    }
    
    return render(request, "accounts/dashboard.html", context)


@login_required
def profile_view(request):
    """
    Display read-only view of user profile.
    """
    user = request.user
    profile = user.profile
    
    training_stats, _ = TrainingStats.objects.get_or_create(user=user)
    profile_completion = _calculate_profile_completion(profile)
    recent_belts = BeltProgress.objects.filter(user=user).order_by('-achieved_on')[:3]
    
    context = {
        'profile': profile,
        'training_stats': training_stats,
        'profile_completion': profile_completion,
        'recent_belts': recent_belts,
    }
    
    return render(request, 'accounts/profile_view.html', context)


def public_profile_view(request, user_id):
    """
    Public profile view - visible to other users.
    """
    profile_user = get_object_or_404(User, id=user_id, is_active=True)
    profile = profile_user.profile
    
    training_stats, _ = TrainingStats.objects.get_or_create(user=profile_user)
    belt_history = BeltProgress.objects.filter(user=profile_user).order_by('-achieved_on')[:5]
    
    is_own_profile = request.user.is_authenticated and request.user.id == profile_user.id
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'training_stats': training_stats,
        'belt_history': belt_history,
        'is_own_profile': is_own_profile,
    }
    
    return render(request, 'accounts/public_profile.html', context)


def _calculate_profile_completion(profile):
    """Calculate profile completion percentage."""
    fields = [
        profile.phone,
        profile.date_of_birth,
        profile.gender,
        profile.address,
        profile.city,
        profile.emergency_contact_name,
        profile.emergency_contact_phone,
        profile.bio,
        profile.profile_picture,
    ]
    completed = sum(1 for field in fields if field)
    return int((completed / len(fields)) * 100)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Handle profile updates.
    """
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile_view")

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile_completion'] = _calculate_profile_completion(self.get_object())
        return context


# =============================================================================
# SETTINGS VIEWS
# =============================================================================

@login_required
def account_settings_view(request):
    """
    Account settings page.
    """
    if request.method == 'POST':
        form = UserAccountForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account information has been updated!")
            return redirect('accounts:settings')
    else:
        form = UserAccountForm(instance=request.user)
    
    return render(request, 'accounts/settings.html', {'form': form})


@login_required
def password_change_view(request):
    """
    Handle password change.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password1']
            
            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                
                update_session_auth_hash(request, user)
                
                messages.success(request, "Your password has been changed successfully!")
                return redirect('accounts:settings')
            else:
                messages.error(request, "Your old password was incorrect.")
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/password_change.html', {'form': form})


@login_required
def delete_account_view(request):
    """
    Handle account deletion.
    """
    if request.method == 'POST':
        password = request.POST.get('password')
        
        if request.user.check_password(password):
            user = request.user
            user.is_active = False
            user.save()
            
            logout(request)
            
            messages.success(request, "Your account has been deactivated successfully.")
            return redirect('core:home')
        else:
            messages.error(request, "Incorrect password. Account deletion cancelled.")
    
    return render(request, 'accounts/delete_account.html')


# =============================================================================
# TRAINING & PROGRESS VIEWS
# =============================================================================

@login_required
def belt_progress_view(request):
    """
    Display user's belt progression history.
    """
    belt_history = BeltProgress.objects.filter(
        user=request.user
    ).order_by('-achieved_on')
    
    context = {
        'belt_history': belt_history,
        'current_belt': request.user.profile.belt_level,
    }
    
    return render(request, 'accounts/belt_progress.html', context)


@login_required
def training_stats_view(request):
    """
    Display user's training statistics.
    """
    stats, _ = TrainingStats.objects.get_or_create(user=request.user)
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'accounts/training_stats.html', context)


@login_required
def add_belt_progress(request):
    """
    Add new belt progress record.
    """
    if not request.user.is_instructor and not request.user.is_staff:
        messages.error(request, "You don't have permission to add belt progress.")
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = BeltProgressForm(request.POST)
        if form.is_valid():
            belt_progress = form.save(commit=False)
            
            user_profile = belt_progress.user.profile
            user_profile.belt_level = belt_progress.current_belt
            user_profile.save()
            
            belt_progress.save()
            
            messages.success(
                request, 
                f"Belt progress recorded for {belt_progress.user.full_name}!"
            )
            return redirect('accounts:belt_progress')
    else:
        form = BeltProgressForm()
    
    return render(request, 'accounts/add_belt_progress.html', {'form': form})


# =============================================================================
# EXPORT & DOWNLOAD FEATURES
# =============================================================================

@login_required
def download_profile_pdf(request):
    """
    Generate PDF of user profile for download.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        user = request.user
        profile = user.profile
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, f"Kenya Karate Federation - Member Profile")
        
        p.setFont("Helvetica", 12)
        y = 700
        p.drawString(100, y, f"Name: {user.full_name}")
        y -= 20
        p.drawString(100, y, f"Email: {user.email}")
        y -= 20
        p.drawString(100, y, f"Belt Level: {profile.belt_level}")
        y -= 20
        p.drawString(100, y, f"Member Since: {user.date_joined.strftime('%B %Y')}")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="profile_{user.id}.pdf"'
        return response
    except ImportError:
        messages.error(request, "PDF generation not available. Install reportlab package.")
        return redirect('accounts:profile_view')


@login_required
def export_training_data(request):
    """
    Export training data as CSV.
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="training_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Belt Level', 'Test Score', 'Instructor', 'Notes'])
    
    belt_history = BeltProgress.objects.filter(user=request.user).order_by('-achieved_on')
    for belt in belt_history:
        writer.writerow([
            belt.achieved_on,
            belt.current_belt,
            belt.test_score or 'N/A',
            belt.instructor.name if belt.instructor else 'N/A',
            belt.notes or ''
        ])
    
    return response