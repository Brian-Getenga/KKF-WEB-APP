from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import (
    Instructor, Achievement, Testimonial, 
    InstructorAvailability, InstructorReview
)


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'rank', 'specialization', 'experience_years',
        'availability_status', 'featured_badge', 'student_count',
        'rating_display', 'created_at'
    ]
    list_filter = [
        'rank', 'specialization', 'is_available', 
        'is_featured', 'created_at'
    ]
    search_fields = ['name', 'bio', 'email']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['total_students', 'rating', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'rank', 'specialization')
        }),
        ('Bio & Description', {
            'fields': ('bio', 'short_bio', 'video_intro_url')
        }),
        ('Professional Details', {
            'fields': ('experience_years', 'certifications')
        }),
        ('Media', {
            'fields': ('photo',)
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'social_links'),
            'classes': ('collapse',)
        }),
        ('Availability & Capacity', {
            'fields': ('is_available', 'max_students', 'total_students')
        }),
        ('Display Options', {
            'fields': ('is_featured', 'display_order', 'rating')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_available', 'mark_as_unavailable', 'mark_as_featured']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _student_count=Count('reviews', distinct=True),
            _avg_rating=Avg('reviews__teaching_quality')
        )
    
    def availability_status(self, obj):
    # Define color and symbol
     if obj.is_available:
        color = '#7ccf00'
        symbol = '✓ Available'
     else:
        color = '#999'
        symbol = '✗ Unavailable'
    
    # Use format_html correctly
     return format_html(
        '<span style="color: {}; font-weight: bold;">{}</span>',
        color,
        symbol
    )

    availability_status.short_description = 'Status'

    def featured_badge(self, obj):
     if getattr(obj, 'is_featured', False):
        return format_html(
            '<span style="color:{}; background-color:{}; padding:2px 6px; border-radius:4px;">{}</span>',
            'white', '#007bff', 'Featured'
        )
     return ''

    def student_count(self, obj):
        return obj._student_count if hasattr(obj, '_student_count') else 0
    student_count.short_description = 'Students'
    student_count.admin_order_field = '_student_count'
    
    from django.utils.html import format_html

    def rating_display(self, obj):
    # Safely format rating as 2 decimals
     rating = f"{obj.rating:.2f}"  # Convert to string first

    # Optionally color code based on rating
     color = "#7ccf00" if obj.rating >= 4.5 else "#999"

     return format_html(
        '<span style="color: {}; font-weight: bold;">{}</span>',
        color,
        rating
    )

    rating_display.short_description = 'Rating'

    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} instructors marked as available.')
    mark_as_available.short_description = 'Mark as available'
    
    def mark_as_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} instructors marked as unavailable.')
    mark_as_unavailable.short_description = 'Mark as unavailable'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} instructors marked as featured.')
    mark_as_featured.short_description = 'Mark as featured'


class InstructorAvailabilityInline(admin.TabularInline):
    model = InstructorAvailability
    extra = 1
    fields = ['day_of_week', 'start_time', 'end_time', 'is_active', 'notes']


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'achievement_type', 'instructor', 'date',
        'location', 'featured_badge', 'created_at'
    ]
    list_filter = [
        'achievement_type', 'is_featured', 'date', 'created_at'
    ]
    search_fields = ['title', 'description', 'location']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['students']
    
    fieldsets = (
        ('Achievement Details', {
            'fields': ('title', 'description', 'achievement_type', 'date', 'location')
        }),
        ('Related People', {
            'fields': ('instructor', 'students')
        }),
        ('Media & Links', {
            'fields': ('image', 'external_link')
        }),
        ('Display Options', {
            'fields': ('is_featured', 'highlight_color')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_featured', 'mark_as_not_featured']
    
    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html(
                '<span style="background: {}; padding: 3px 8px; border-radius: 3px; color: black; font-weight: bold;">★ FEATURED</span>',
                obj.highlight_color
            )
        return '—'
    featured_badge.short_description = 'Featured'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} achievements marked as featured.')
    mark_as_featured.short_description = 'Mark as featured'
    
    def mark_as_not_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} achievements unmarked as featured.')
    mark_as_not_featured.short_description = 'Remove from featured'


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'belt_rank', 'rating_stars', 'instructor',
        'approval_status', 'featured_badge', 'created_at'
    ]
    list_filter = [
        'is_approved', 'is_featured', 'rating',
        'instructor', 'created_at'
    ]
    search_fields = ['name', 'message', 'title']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'belt_rank', 'photo', 'user')
        }),
        ('Testimonial Content', {
            'fields': ('title', 'message', 'rating')
        }),
        ('Relations', {
            'fields': ('instructor',)
        }),
        ('Moderation', {
            'fields': ('is_approved', 'approved_at', 'is_featured', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_testimonials', 'unapprove_testimonials', 'mark_as_featured']
    
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color: #FFCD00; font-size: 16px;">{}</span>',
            stars
        )
    rating_stars.short_description = 'Rating'
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html(
                '<span style="color: #7ccf00; font-weight: bold;">✓ Approved</span>'
            )
        return format_html(
            '<span style="color: #fb2c36; font-weight: bold;">✗ Pending</span>'
        )
    approval_status.short_description = 'Status'
    
    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html(
                '<span style="background: #FFCD00; padding: 3px 8px; border-radius: 3px; font-weight: bold;">★ FEATURED</span>'
            )
        return '—'
    featured_badge.short_description = 'Featured'
    
    def approve_testimonials(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_approved=True, approved_at=timezone.now())
        self.message_user(request, f'{updated} testimonials approved.')
    approve_testimonials.short_description = 'Approve selected testimonials'
    
    def unapprove_testimonials(self, request, queryset):
        updated = queryset.update(is_approved=False, approved_at=None)
        self.message_user(request, f'{updated} testimonials unapproved.')
    unapprove_testimonials.short_description = 'Unapprove selected testimonials'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} testimonials marked as featured.')
    mark_as_featured.short_description = 'Mark as featured'


@admin.register(InstructorAvailability)
class InstructorAvailabilityAdmin(admin.ModelAdmin):
    list_display = [
        'instructor', 'day_of_week_display', 'time_slot',
        'active_status', 'notes'
    ]
    list_filter = ['day_of_week', 'is_active', 'instructor']
    search_fields = ['instructor__name', 'notes']
    
    def day_of_week_display(self, obj):
        return obj.get_day_of_week_display()
    day_of_week_display.short_description = 'Day'
    
    def time_slot(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
    time_slot.short_description = 'Time'
    
    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #7ccf00;">● Active</span>')
        return format_html('<span style="color: #999;">○ Inactive</span>')
    active_status.short_description = 'Status'


@admin.register(InstructorReview)
class InstructorReviewAdmin(admin.ModelAdmin):
    list_display = [
        'instructor', 'user', 'overall_rating_display',
        'verified_badge', 'approval_status', 'created_at'
    ]
    list_filter = [
        'is_verified', 'is_approved', 'instructor',
        'teaching_quality', 'created_at'
    ]
    search_fields = ['instructor__name', 'user__username', 'review_text']
    readonly_fields = ['created_at', 'updated_at', 'overall_rating']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Review Information', {
            'fields': ('instructor', 'user')
        }),
        ('Ratings (1-5)', {
            'fields': (
                'teaching_quality', 'communication',
                'technique', 'motivation'
            )
        }),
        ('Review Content', {
            'fields': ('review_text', 'pros', 'cons')
        }),
        ('Verification & Approval', {
            'fields': ('is_verified', 'is_approved')
        }),
        ('Metadata', {
            'fields': ('overall_rating', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reviews', 'verify_reviews']
    
    def overall_rating_display(self, obj):
        rating = obj.overall_rating
        stars = '★' * int(rating) + '☆' * (5 - int(rating))
        return format_html(
            '<span style="color: #FFCD00; font-size: 14px;">{}</span> <span style="color: #999;">({:.1f})</span>',
            stars, rating
        )
    overall_rating_display.short_description = 'Overall Rating'
    
    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="background: #2b7fff; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">✓ VERIFIED</span>'
            )
        return '—'
    verified_badge.short_description = 'Verified'
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: #7ccf00; font-weight: bold;">✓ Approved</span>')
        return format_html('<span style="color: #fb2c36; font-weight: bold;">✗ Pending</span>')
    approval_status.short_description = 'Status'
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews approved.')
    approve_reviews.short_description = 'Approve selected reviews'
    
    def verify_reviews(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} reviews verified as from real students.')
    verify_reviews.short_description = 'Verify selected reviews'