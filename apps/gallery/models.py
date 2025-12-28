from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


class GalleryCategory(models.Model):
    """Category for organizing gallery images"""
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Font Awesome icon class")
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Gallery Categories"
        ordering = ['display_order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('gallery:category', kwargs={'slug': self.slug})
    
    @property
    def image_count(self):
        return self.images.count()


class GalleryImage(models.Model):
    """Individual gallery image with metadata"""
    category = models.ForeignKey(
        GalleryCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='images'
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    image = models.ImageField(upload_to='gallery/%Y/%m/')
    thumbnail = models.ImageField(upload_to='gallery/thumbnails/%Y/%m/', blank=True, null=True)
    
    # Video support
    video_url = models.URLField(
        blank=True, 
        null=True, 
        help_text="YouTube or Vimeo URL"
    )
    
    # Metadata
    caption = models.TextField(blank=True, null=True, help_text="Short description")
    photographer = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    event_date = models.DateField(blank=True, null=True, help_text="Date when photo was taken")
    
    # Organization
    is_featured = models.BooleanField(default=False, help_text="Feature on homepage and category pages")
    is_public = models.BooleanField(default=True, help_text="Make visible to public")
    display_order = models.IntegerField(default=0)
    
    # SEO
    meta_description = models.CharField(max_length=160, blank=True, null=True)
    
    # Statistics
    view_count = models.IntegerField(default=0)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', '-display_order', '-uploaded_at']
        indexes = [
            models.Index(fields=['-uploaded_at']),
            models.Index(fields=['is_featured', '-uploaded_at']),
            models.Index(fields=['category', '-uploaded_at']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate slug from title
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while GalleryImage.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Generate meta description if not provided
        if not self.meta_description and self.caption:
            self.meta_description = self.caption[:160]
        
        super().save(*args, **kwargs)
        
        # Generate thumbnail after saving
        if self.image and not self.thumbnail:
            self.create_thumbnail()
    
    def create_thumbnail(self, size=(400, 400)):
        """Create a thumbnail version of the image"""
        if not self.image:
            return
        
        try:
            # Open the image
            img = Image.open(self.image.path)
            
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            # Resize image
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save thumbnail
            thumb_io = BytesIO()
            img.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            
            # Generate filename
            thumb_filename = f"thumb_{self.image.name.split('/')[-1]}"
            if not thumb_filename.lower().endswith('.jpg'):
                thumb_filename = thumb_filename.rsplit('.', 1)[0] + '.jpg'
            
            # Save to model
            self.thumbnail.save(
                thumb_filename,
                InMemoryUploadedFile(
                    thumb_io, None, thumb_filename, 'image/jpeg',
                    sys.getsizeof(thumb_io), None
                ),
                save=False
            )
            super(GalleryImage, self).save(update_fields=['thumbnail'])
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('gallery:image_detail', kwargs={'pk': self.pk})
    
    def increment_views(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    @property
    def is_video(self):
        """Check if this is a video entry"""
        return bool(self.video_url)
    
    @property
    def display_image(self):
        """Return thumbnail if available, otherwise original image"""
        return self.thumbnail if self.thumbnail else self.image


# Optional: Add this model if you want tagging functionality
class GalleryTag(models.Model):
    """Optional tagging system for gallery images"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    images = models.ManyToManyField(GalleryImage, related_name='tags', blank=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    @property
    def image_count(self):
        return self.images.count()