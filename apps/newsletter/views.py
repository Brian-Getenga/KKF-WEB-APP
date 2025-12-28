
# ============================================================================
# newsletter/views.py - COMPLETE VERSION
# ============================================================================

from django.views.generic import CreateView, TemplateView
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Subscriber
from .forms import SubscribeForm, UnsubscribeForm
from .utils import send_confirmation_email


class SubscribeView(CreateView):
    """Handle newsletter subscription with double opt-in"""
    model = Subscriber
    form_class = SubscribeForm
    template_name = 'newsletter/subscribe.html'
    success_url = reverse_lazy('newsletter:subscribe_success')
    
    def form_valid(self, form):
        subscriber = form.save(commit=False)
        subscriber.is_active = False  # Require confirmation
        subscriber.save()
        
        # Pass self.request to the email function
        send_confirmation_email(subscriber, self.request)
        
        messages.success(
            self.request,
            'Almost there! Please check your email to confirm your subscription.'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'There was an error with your submission. Please try again.'
        )
        return super().form_invalid(form)


class SubscribeSuccessView(TemplateView):
    """Success page after subscription"""
    template_name = 'newsletter/subscribe_success.html'


class ConfirmSubscriptionView(TemplateView):
    """Confirm email subscription via token"""
    template_name = 'newsletter/confirm.html'
    
    def get(self, request, token):
        try:
            subscriber = Subscriber.objects.get(confirmation_token=token)
            
            if subscriber.is_active:
                messages.info(request, 'Your subscription is already confirmed!')
            else:
                subscriber.confirm_subscription()
                messages.success(
                    request,
                    f'Success! Your subscription has been confirmed. Welcome aboard!'
                )
            
            context = {
                'subscriber': subscriber,
                'already_confirmed': subscriber.is_active
            }
            return render(request, self.template_name, context)
            
        except Subscriber.DoesNotExist:
            messages.error(request, 'Invalid confirmation link.')
            return redirect('home')


class UnsubscribeView(TemplateView):
    """Handle unsubscription"""
    template_name = 'newsletter/unsubscribe.html'
    
    def get(self, request, token):
        subscriber = get_object_or_404(Subscriber, unsubscribe_token=token)
        form = UnsubscribeForm()
        
        return render(request, self.template_name, {
            'subscriber': subscriber,
            'form': form
        })
    
    def post(self, request, token):
        subscriber = get_object_or_404(Subscriber, unsubscribe_token=token)
        form = UnsubscribeForm(request.POST)
        
        if form.is_valid():
            subscriber.is_active = False
            subscriber.save()
            
            messages.success(
                request,
                'You have been unsubscribed. We\'re sorry to see you go!'
            )
            return redirect('newsletter:unsubscribe_success')
        
        return render(request, self.template_name, {
            'subscriber': subscriber,
            'form': form
        })


class UnsubscribeSuccessView(TemplateView):
    """Success page after unsubscription"""
    template_name = 'newsletter/unsubscribe_success.html'
