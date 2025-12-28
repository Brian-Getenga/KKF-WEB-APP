# ============================================================================
# newsletter/admin.py - COMPREHENSIVE ADMIN CONFIGURATION (BUG-FREE)
# ============================================================================

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import csv
from datetime import timedelta

from .models import Subscriber, Campaign, EmailLog


# ============================================================================
# CUSTOM FILTERS
# ============================================================================

class SubscriptionStatusFilter(admin.SimpleListFilter):
    title = 'subscription status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active Subscribers'),
            ('pending', 'Pending Confirmation'),
            ('recent', 'Subscribed Last 7 Days'),
            ('inactive_30', 'Inactive 30+ Days'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_active=True)
        if self.value() == 'pending':
            return queryset.filter(is_active=False)
        if self.value() == 'recent':
            week_ago = timezone.now() - timedelta(days=7)
            return queryset.filter(subscribed_date__gte=week_ago)
        if self.value() == 'inactive_30':
            month_ago = timezone.now() - timedelta(days=30)
            return queryset.filter(
                is_active=True,
                confirmed_date__lt=month_ago
            )


class CampaignStatusFilter(admin.SimpleListFilter):
    title = 'campaign status'
    parameter_name = 'campaign_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active (Draft/Scheduled)'),
            ('completed', 'Completed (Sent)'),
            ('failed', 'Failed'),
            ('scheduled_today', 'Scheduled for Today'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(status__in=['draft', 'scheduled'])
        if self.value() == 'completed':
            return queryset.filter(status='sent')
        if self.value() == 'failed':
            return queryset.filter(status='failed')
        if self.value() == 'scheduled_today':
            today = timezone.now().date()
            return queryset.filter(
                status='scheduled',
                scheduled_date__date=today
            )


# ============================================================================
# SUBSCRIBER ADMIN
# ============================================================================

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = [
        'email',
        'name',
        'status_badge',
        'preferences',
        'subscribed_date',
        'confirmed_date',
        'action_buttons'
    ]
    list_filter = [
        SubscriptionStatusFilter,
        'preferences',
        'is_active',
        'subscribed_date',
    ]
    search_fields = ['email', 'name']
    readonly_fields = [
        'confirmation_token',
        'unsubscribe_token',
        'subscribed_date',
        'confirmed_date',
        'subscriber_stats'
    ]
    fieldsets = (
        ('Subscriber Information', {
            'fields': ('email', 'name', 'preferences')
        }),
        ('Status', {
            'fields': ('is_active', 'confirmed_date', 'subscriber_stats')
        }),
        ('Security Tokens', {
            'fields': ('confirmation_token', 'unsubscribe_token'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('subscribed_date',),
            'classes': ('collapse',)
        }),
    )
    actions = [
        'activate_subscribers',
        'deactivate_subscribers',
        'export_to_csv',
        'send_test_email',
        'bulk_delete_inactive'
    ]
    list_per_page = 50
    date_hierarchy = 'subscribed_date'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate with email counts for stats
        qs = qs.annotate(
            total_emails_received=Count('email_logs')
        )
        return qs

    def status_badge(self, obj):
        if obj.is_active:
            color = '#28a745'
            text = 'Active'
            icon = '✓'
        else:
            color = '#ffc107'
            text = 'Pending'
            icon = '⏳'
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-weight: bold;">'
            '{} {}</span>',
            color, icon, text
        )
    status_badge.short_description = 'Status'

    def action_buttons(self, obj):
        buttons = []
        
        if not obj.is_active:
            confirm_url = reverse('admin:newsletter_confirm_subscriber', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{confirm_url}" '
                f'style="background-color: #28a745; color: white; '
                f'padding: 5px 10px; text-decoration: none; border-radius: 3px;">✓ Confirm</a>'
            )
        
        history_url = reverse('admin:newsletter_subscriber_history', args=[obj.id])
        buttons.append(
            f'<a class="button" href="{history_url}" '
            f'style="background-color: #007bff; color: white; '
            f'padding: 5px 10px; text-decoration: none; border-radius: 3px;">📊 History</a>'
        )
        
        return mark_safe(' '.join(buttons))
    action_buttons.short_description = 'Actions'

    def subscriber_stats(self, obj):
        if obj.pk:
            total_emails = obj.email_logs.count()
            successful = obj.email_logs.filter(success=True).count()
            failed = obj.email_logs.filter(success=False).count()
            
            percentage = round(successful / total_emails * 100, 1) if total_emails > 0 else 0
            
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">'
                '<h4 style="margin-top: 0;">Email Statistics</h4>'
                '<p><strong>Total Emails Received:</strong> {}</p>'
                '<p><strong>Successful Deliveries:</strong> {} ({}%)</p>'
                '<p><strong>Failed Deliveries:</strong> {}</p>'
                '</div>',
                total_emails,
                successful,
                percentage,
                failed
            )
        return mark_safe("Save subscriber to see statistics")
    subscriber_stats.short_description = 'Statistics'

    # Custom Actions
    @admin.action(description='✓ Activate selected subscribers')
    def activate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=True, confirmed_date=timezone.now())
        self.message_user(
            request,
            f'{updated} subscriber(s) successfully activated.',
            messages.SUCCESS
        )

    @admin.action(description='✗ Deactivate selected subscribers')
    def deactivate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} subscriber(s) deactivated.',
            messages.WARNING
        )

    @admin.action(description='📥 Export to CSV')
    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="subscribers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Name', 'Preferences', 'Status', 'Subscribed Date', 'Confirmed Date'])
        
        for sub in queryset:
            writer.writerow([
                sub.email,
                sub.name,
                sub.get_preferences_display(),
                'Active' if sub.is_active else 'Pending',
                sub.subscribed_date.strftime('%Y-%m-%d %H:%M'),
                sub.confirmed_date.strftime('%Y-%m-%d %H:%M') if sub.confirmed_date else 'N/A'
            ])
        
        return response

    @admin.action(description='📧 Send test email')
    def send_test_email(self, request, queryset):
        count = 0
        for subscriber in queryset.filter(is_active=True):
            try:
                send_mail(
                    'Test Email from Newsletter System',
                    f'Hello {subscriber.name or "Subscriber"},\n\nThis is a test email.',
                    settings.DEFAULT_FROM_EMAIL,
                    [subscriber.email],
                    fail_silently=False,
                )
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Failed to send to {subscriber.email}: {str(e)}',
                    messages.ERROR
                )
        
        if count > 0:
            self.message_user(
                request,
                f'Test email sent to {count} subscriber(s).',
                messages.SUCCESS
            )

    @admin.action(description='🗑️ Delete inactive pending subscribers')
    def bulk_delete_inactive(self, request, queryset):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        to_delete = queryset.filter(
            is_active=False,
            subscribed_date__lt=thirty_days_ago
        )
        count = to_delete.count()
        to_delete.delete()
        
        self.message_user(
            request,
            f'{count} inactive pending subscriber(s) deleted.',
            messages.SUCCESS
        )

    # Custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:subscriber_id>/confirm/',
                self.admin_site.admin_view(self.confirm_subscriber_view),
                name='newsletter_confirm_subscriber',
            ),
            path(
                '<int:subscriber_id>/history/',
                self.admin_site.admin_view(self.subscriber_history_view),
                name='newsletter_subscriber_history',
            ),
        ]
        return custom_urls + urls

    def confirm_subscriber_view(self, request, subscriber_id):
        subscriber = get_object_or_404(Subscriber, pk=subscriber_id)
        subscriber.confirm_subscription()
        messages.success(request, f'Subscriber {subscriber.email} confirmed successfully.')
        return redirect('admin:newsletter_subscriber_changelist')

    def subscriber_history_view(self, request, subscriber_id):
        subscriber = get_object_or_404(Subscriber, pk=subscriber_id)
        logs = subscriber.email_logs.select_related('campaign').order_by('-sent_date')
        
        context = {
            'subscriber': subscriber,
            'logs': logs,
            'title': f'Email History for {subscriber.email}',
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
            'has_permission': True,
        }
        return render(request, 'admin/newsletter/subscriber_history.html', context)


# ============================================================================
# CAMPAIGN ADMIN
# ============================================================================

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'campaign_type',
        'status_badge',
        'scheduled_date',
        'delivery_stats',
        'created_date',
        'action_buttons'
    ]
    list_filter = [
        CampaignStatusFilter,
        'campaign_type',
        'status',
        'created_date',
    ]
    search_fields = ['title', 'subject']
    readonly_fields = [
        'total_recipients',
        'successful_sends',
        'failed_sends',
        'created_date',
        'updated_date',
        'sent_date',
        'campaign_preview',
        'recipient_preview'
    ]
    fieldsets = (
        ('Campaign Details', {
            'fields': ('title', 'subject', 'campaign_type', 'content')
        }),
        ('Status & Scheduling', {
            'fields': ('status', 'scheduled_date', 'sent_date')
        }),
        ('Related Content', {
            'fields': (
                'related_post_id',
                'related_class_id',
                'related_product_id'
            ),
            'classes': ('collapse',)
        }),
        ('Delivery Statistics', {
            'fields': (
                'total_recipients',
                'successful_sends',
                'failed_sends',
                'recipient_preview'
            )
        }),
        ('Preview', {
            'fields': ('campaign_preview',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        }),
    )
    actions = [
        'duplicate_campaign',
        'schedule_campaign',
        'mark_as_draft',
        'export_campaign_report'
    ]
    list_per_page = 25
    date_hierarchy = 'created_date'

    def status_badge(self, obj):
        status_colors = {
            'draft': '#6c757d',
            'scheduled': '#007bff',
            'sending': '#ffc107',
            'sent': '#28a745',
            'failed': '#dc3545',
        }
        color = status_colors.get(obj.status, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 5px 12px; border-radius: 3px; font-weight: bold; '
            'text-transform: uppercase; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def delivery_stats(self, obj):
        if obj.total_recipients > 0:
            success_rate = (obj.successful_sends / obj.total_recipients) * 100
            color = '#28a745' if success_rate >= 95 else '#ffc107' if success_rate >= 80 else '#dc3545'
            
            # FIX: Calculate percentage first, then pass as string
            success_rate_str = f'{success_rate:.1f}'
            
            return format_html(
                '<div style="text-align: center;">'
                '<div style="font-weight: bold; color: {};">{}%</div>'
                '<div style="font-size: 11px; color: #6c757d;">'
                '{}/{} sent</div>'
                '</div>',
                color, success_rate_str, obj.successful_sends, obj.total_recipients
            )
        return mark_safe('<span style="color: #6c757d;">Not sent</span>')
    delivery_stats.short_description = 'Delivery Rate'

    def action_buttons(self, obj):
        buttons = []
        
        if obj.status in ['draft', 'scheduled']:
            send_url = reverse('admin:newsletter_send_campaign', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{send_url}" '
                f'style="background-color: #28a745; color: white; '
                f'padding: 5px 10px; text-decoration: none; border-radius: 3px;">📤 Send Now</a>'
            )
        
        preview_url = reverse('admin:newsletter_preview_campaign', args=[obj.id])
        buttons.append(
            f'<a class="button" href="{preview_url}" target="_blank" '
            f'style="background-color: #007bff; color: white; '
            f'padding: 5px 10px; text-decoration: none; border-radius: 3px;">👁️ Preview</a>'
        )
        
        report_url = reverse('admin:newsletter_campaign_report', args=[obj.id])
        buttons.append(
            f'<a class="button" href="{report_url}" '
            f'style="background-color: #6c757d; color: white; '
            f'padding: 5px 10px; text-decoration: none; border-radius: 3px;">📊 Report</a>'
        )
        
        return mark_safe(' '.join(buttons))
    action_buttons.short_description = 'Actions'

    def campaign_preview(self, obj):
        if obj.content:
            return mark_safe(
                f'<div style="border: 1px solid #ddd; padding: 15px; '
                f'border-radius: 5px; max-height: 400px; overflow-y: auto;">'
                f'{obj.content}</div>'
            )
        return mark_safe("No content")
    campaign_preview.short_description = 'Email Preview'

    def recipient_preview(self, obj):
        if obj.pk:
            subscribers = obj.get_target_subscribers()[:10]
            subscriber_list = '<br>'.join([
                f'• {s.email} ({s.get_preferences_display()})'
                for s in subscribers
            ])
            total = obj.get_target_subscribers().count()
            
            return mark_safe(
                f'<div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">'
                f'<h4 style="margin-top: 0;">Target Recipients (showing 10 of {total})</h4>'
                f'<div style="font-family: monospace; font-size: 12px;">{subscriber_list}</div>'
                f'</div>'
            )
        return mark_safe("Save campaign to see recipients")
    recipient_preview.short_description = 'Target Recipients'

    # Custom Actions
    @admin.action(description='📋 Duplicate campaign')
    def duplicate_campaign(self, request, queryset):
        for campaign in queryset:
            campaign.pk = None
            campaign.title = f"Copy of {campaign.title}"
            campaign.status = 'draft'
            campaign.scheduled_date = None
            campaign.sent_date = None
            campaign.total_recipients = 0
            campaign.successful_sends = 0
            campaign.failed_sends = 0
            campaign.save()
        
        self.message_user(
            request,
            f'{queryset.count()} campaign(s) duplicated successfully.',
            messages.SUCCESS
        )

    @admin.action(description='📅 Schedule for tomorrow')
    def schedule_campaign(self, request, queryset):
        tomorrow = timezone.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        
        updated = queryset.filter(status='draft').update(
            status='scheduled',
            scheduled_date=tomorrow
        )
        
        self.message_user(
            request,
            f'{updated} campaign(s) scheduled for {tomorrow.strftime("%Y-%m-%d %H:%M")}.',
            messages.SUCCESS
        )

    @admin.action(description='📝 Mark as draft')
    def mark_as_draft(self, request, queryset):
        updated = queryset.exclude(status='sent').update(status='draft')
        self.message_user(
            request,
            f'{updated} campaign(s) marked as draft.',
            messages.INFO
        )

    @admin.action(description='📊 Export campaign report')
    def export_campaign_report(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="campaign_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Campaign Title', 'Type', 'Status', 'Total Recipients',
            'Successful', 'Failed', 'Success Rate', 'Sent Date'
        ])
        
        for campaign in queryset:
            success_rate = 0
            if campaign.total_recipients > 0:
                success_rate = (campaign.successful_sends / campaign.total_recipients) * 100
            
            writer.writerow([
                campaign.title,
                campaign.get_campaign_type_display(),
                campaign.get_status_display(),
                campaign.total_recipients,
                campaign.successful_sends,
                campaign.failed_sends,
                f'{success_rate:.1f}%',
                campaign.sent_date.strftime('%Y-%m-%d %H:%M') if campaign.sent_date else 'N/A'
            ])
        
        return response

    # Custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:campaign_id>/send/',
                self.admin_site.admin_view(self.send_campaign_view),
                name='newsletter_send_campaign',
            ),
            path(
                '<int:campaign_id>/preview/',
                self.admin_site.admin_view(self.preview_campaign_view),
                name='newsletter_preview_campaign',
            ),
            path(
                '<int:campaign_id>/report/',
                self.admin_site.admin_view(self.campaign_report_view),
                name='newsletter_campaign_report',
            ),
        ]
        return custom_urls + urls

    def send_campaign_view(self, request, campaign_id):
        campaign = get_object_or_404(Campaign, pk=campaign_id)
        
        if request.method == 'POST':
            # Get target subscribers
            subscribers = campaign.get_target_subscribers()
            campaign.total_recipients = subscribers.count()
            campaign.status = 'sending'
            campaign.save()
            
            # Send emails
            success_count = 0
            failed_count = 0
            
            for subscriber in subscribers:
                try:
                    # Replace this with your actual email sending logic
                    send_mail(
                        campaign.subject,
                        campaign.content,  # You might want to use HTML email here
                        settings.DEFAULT_FROM_EMAIL,
                        [subscriber.email],
                        fail_silently=False,
                    )
                    EmailLog.objects.create(
                        campaign=campaign,
                        subscriber=subscriber,
                        success=True
                    )
                    success_count += 1
                except Exception as e:
                    EmailLog.objects.create(
                        campaign=campaign,
                        subscriber=subscriber,
                        success=False,
                        error_message=str(e)
                    )
                    failed_count += 1
            
            campaign.successful_sends = success_count
            campaign.failed_sends = failed_count
            campaign.status = 'sent'
            campaign.sent_date = timezone.now()
            campaign.save()
            
            messages.success(
                request,
                f'Campaign sent! Success: {success_count}, Failed: {failed_count}'
            )
            return redirect('admin:newsletter_campaign_changelist')
        
        recipients = campaign.get_target_subscribers()
        context = {
            'campaign': campaign,
            'recipients': recipients,
            'recipient_count': recipients.count(),
            'title': f'Send Campaign: {campaign.title}',
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
            'has_permission': True,
        }
        return render(request, 'newsletter/admin/newsletter/send_campaign.html', context)

    def preview_campaign_view(self, request, campaign_id):
        campaign = get_object_or_404(Campaign, pk=campaign_id)
        return HttpResponse(campaign.content)

    def campaign_report_view(self, request, campaign_id):
        campaign = get_object_or_404(Campaign, pk=campaign_id)
        logs = campaign.email_logs.select_related('subscriber').order_by('-sent_date')
        
        # Calculate statistics
        total = logs.count()
        successful = logs.filter(success=True).count()
        failed = logs.filter(success=False).count()
        success_rate = (successful / total * 100) if total > 0 else 0
        
        context = {
            'campaign': campaign,
            'logs': logs,
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate,
            'title': f'Campaign Report: {campaign.title}',
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
            'has_permission': True,
        }
        return render(request, 'admin/newsletter/campaign_report.html', context)


# ============================================================================
# EMAIL LOG ADMIN
# ============================================================================

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'campaign_link',
        'subscriber_email',
        'sent_date',
        'success_badge',
        'error_preview'
    ]
    list_filter = [
        'success',
        'sent_date',
        'campaign__campaign_type',
    ]
    search_fields = [
        'subscriber__email',
        'campaign__title',
        'error_message'
    ]
    readonly_fields = [
        'campaign',
        'subscriber',
        'sent_date',
        'success',
        'error_message'
    ]
    list_per_page = 100
    date_hierarchy = 'sent_date'

    def has_add_permission(self, request):
        return False  # Logs are created automatically

    def has_change_permission(self, request, obj=None):
        return False  # Logs should not be edited

    def campaign_link(self, obj):
        if obj.campaign:
            url = reverse('admin:newsletter_campaign_change', args=[obj.campaign.id])
            return format_html(
                '<a href="{}" style="font-weight: bold;">{}</a>',
                url, obj.campaign.title
            )
        return mark_safe("N/A")
    campaign_link.short_description = 'Campaign'

    def subscriber_email(self, obj):
        if obj.subscriber:
            url = reverse('admin:newsletter_subscriber_change', args=[obj.subscriber.id])
            return format_html('<a href="{}">{}</a>', url, obj.subscriber.email)
        return mark_safe('<span style="color: #dc3545;">Deleted Subscriber</span>')
    subscriber_email.short_description = 'Subscriber'

    def success_badge(self, obj):
        if obj.success:
            return mark_safe(
                '<span style="color: #28a745; font-weight: bold;">✓ Success</span>'
            )
        return mark_safe(
            '<span style="color: #dc3545; font-weight: bold;">✗ Failed</span>'
        )
    success_badge.short_description = 'Status'

    def error_preview(self, obj):
        if obj.error_message:
            preview = obj.error_message[:50]
            if len(obj.error_message) > 50:
                preview += '...'
            return format_html(
                '<span style="color: #dc3545; font-family: monospace; font-size: 11px;">{}</span>',
                preview
            )
        return mark_safe('<span style="color: #28a745;">—</span>')
    error_preview.short_description = 'Error'


# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================

admin.site.site_header = "Newsletter Management System"
admin.site.site_title = "Newsletter Admin"
admin.site.index_title = "Welcome to Newsletter Administration"