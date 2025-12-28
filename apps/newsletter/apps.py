from django.apps import AppConfig


class NewsletterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.newsletter'
    verbose_name = 'Newsletter Management'
    
    def ready(self):
        """Import signal handlers when app is ready"""
        import apps.newsletter.signals  # noqa
