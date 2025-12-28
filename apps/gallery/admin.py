from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import GalleryCategory, GalleryImage


@admin.register(GalleryCategory)
class GalleryCategoryAdmin(admin.ModelAdmin):
    """Simple admin for Gallery Categories"""
    list_display = ['name', 'slug', 'image_count_display', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def image_count_display(self, obj):
        """Display image count"""
        count = obj.images.count()
        return f"{count} images"
    image_count_display.short_description = 'Images'


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    """Simple admin for Gallery Images"""
    list_display = [
        'thumbnail_preview', 
        'title', 
        'category', 
        'is_featured', 
        'is_public',
        'uploaded_at'
    ]
    list_display_links = ['thumbnail_preview', 'title']
    list_editable = ['is_featured', 'is_public']
    list_filter = ['is_featured', 'is_public', 'category', 'uploaded_at']
    search_fields = ['title', 'caption', 'location']
    date_hierarchy = 'uploaded_at'
    
    # Only fields that exist in the model
    fields = [
        'title',
        'category',
        'image',
        'thumbnail',
        'video_url',
        'caption',
        'photographer',
        'location',
        'event_date',
        'is_featured',
        'is_public',
        'display_order',
        'meta_description',
        'view_count',
        'uploaded_at',
    ]
    
    readonly_fields = ['thumbnail', 'view_count', 'uploaded_at']
    
    actions = [
        'mark_as_featured',
        'remove_featured',
        'mark_as_public',
        'mark_as_private',
    ]
    
    def thumbnail_preview(self, obj):
        """Small thumbnail preview in list view"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail.url
            )
        elif obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return "No image"
    thumbnail_preview.short_description = 'Preview'
    
    # Admin Actions
    def mark_as_featured(self, request, queryset):
        """Mark selected images as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} image(s) marked as featured.')
    mark_as_featured.short_description = 'Mark as featured'
    
    def remove_featured(self, request, queryset):
        """Remove featured status from selected images"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} image(s) removed from featured.')
    remove_featured.short_description = 'Remove featured status'
    
    def mark_as_public(self, request, queryset):
        """Mark selected images as public"""
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} image(s) marked as public.')
    mark_as_public.short_description = 'Make public'
    
    def mark_as_private(self, request, queryset):
        """Mark selected images as private"""
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} image(s) marked as private.')
    mark_as_private.short_description = 'Make private'
    
    def save_model(self, request, obj, form, change):
        """Save and generate thumbnail"""
        super().save_model(request, obj, form, change)
        # Thumbnail will be created automatically by the model's save method


# Optional: Register GalleryTag if you added it to models
# from .models import GalleryTag
# 
# @admin.register(GalleryTag)
# class GalleryTagAdmin(admin.ModelAdmin):
#     list_display = ['name', 'slug', 'image_count']
#     search_fields = ['name']
#     prepopulated_fields = {'slug': ('name',)}
#     
#     def image_count(self, obj):
#         return obj.images.count()
#     image_count.short_description = 'Images'