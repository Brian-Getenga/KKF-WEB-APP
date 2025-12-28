from .models import Subscriber, Campaign, NewsletterSettings
from .forms import QuickSubscribeForm


def newsletter_context(request):
    """
    Context processor to add newsletter data to all templates
    
    Add to settings.py:
    TEMPLATES = [{
        ...
        'OPTIONS': {
            'context_processors': [
                ...
                'newsletter.context_processors.newsletter_context',
            ],
        },
    }]
    """
    try:
        settings = NewsletterSettings.load()
        
        context = {
            'newsletter_quick_form': QuickSubscribeForm(),
            'newsletter_settings': settings,
        }
        
        # Add subscriber count if enabled
        if settings.show_subscriber_count:
            context['newsletter_subscriber_count'] = Subscriber.objects.filter(
                is_active=True
            ).count()
        
        # Add latest sent campaign
        latest_campaign = Campaign.objects.filter(
            status='sent'
        ).order_by('-sent_date').first()
        
        if latest_campaign:
            context['newsletter_latest_campaign'] = latest_campaign
        
        return context
    
    except Exception:
        # Return empty context if there's any error
        return {
            'newsletter_quick_form': QuickSubscribeForm(),
        }