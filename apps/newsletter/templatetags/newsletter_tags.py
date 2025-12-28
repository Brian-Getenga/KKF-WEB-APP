# ============================================================================
# newsletter/templatetags/newsletter_tags.py - COMPLETE VERSION
# ============================================================================

from django import template
from apps.newsletter.forms import SubscribeForm

register = template.Library()


@register.inclusion_tag('newsletter/footer_form.html')
def newsletter_footer_form():
    """Template tag to include newsletter form in footer"""
    return {
        'form': SubscribeForm()
    }


@register.inclusion_tag('newsletter/inline_form.html')
def newsletter_inline_form():
    """Template tag to include newsletter form inline"""
    return {
        'form': SubscribeForm()
    }