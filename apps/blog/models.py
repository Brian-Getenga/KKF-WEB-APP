from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinLengthValidator
from apps.accounts.models import User


class Category(models.Model):
    """Blog categories for better organization"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tags for flexible post categorization"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    """Enhanced blog post model with additional features"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    # Basic Info
    title = models.CharField(max_length=200, validators=[MinLengthValidator(5)])
    slug = models.SlugField(unique=True, blank=True, max_length=250)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blog_posts')
    
    # Content
    excerpt = models.CharField(max_length=300, blank=True, help_text="Brief description shown in listings")
    content = models.TextField(validators=[MinLengthValidator(50)])
    
    # Media
    image = models.ImageField(upload_to='blog/%Y/%m/', blank=True, null=True)
    image_alt = models.CharField(max_length=200, blank=True, help_text="Alt text for SEO")
    
    # Organization
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    featured = models.BooleanField(default=False, help_text="Show on homepage")
    allow_comments = models.BooleanField(default=True)
    
    # SEO
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    
    # Analytics
    views_count = models.PositiveIntegerField(default=0, editable=False)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['-published_at', 'status']),
            models.Index(fields=['slug']),
            models.Index(fields=['author', 'status']),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate slug
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Set published_at when first published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        # Auto-generate excerpt if empty
        if not self.excerpt and self.content:
            self.excerpt = self.content[:250] + '...' if len(self.content) > 250 else self.content
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])

    def get_reading_time(self):
        """Calculate estimated reading time in minutes"""
        word_count = len(self.content.split())
        minutes = word_count / 200  # Average reading speed
        return max(1, round(minutes))

    def get_related_posts(self, limit=3):
        """Get related posts based on tags and category"""
        related = BlogPost.objects.filter(
            status='published'
        ).exclude(id=self.id)
        
        # Prioritize same category and shared tags
        if self.category:
            related = related.filter(
                models.Q(category=self.category) | models.Q(tags__in=self.tags.all())
            )
        else:
            related = related.filter(tags__in=self.tags.all())
        
        return related.distinct()[:limit]

    @property
    def is_published(self):
        return self.status == 'published' and self.published_at and self.published_at <= timezone.now()

    def __str__(self):
        return self.title


class Comment(models.Model):
    """Enhanced comment model with threading support"""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Guest comment support
    name = models.CharField(max_length=100, blank=True, help_text="Name (for non-logged-in users)")
    email = models.EmailField(blank=True, help_text="Email (for non-logged-in users)")
    
    content = models.TextField(validators=[MinLengthValidator(3)])
    
    # Moderation
    approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'approved', 'parent']),
        ]

    def save(self, *args, **kwargs):
        # Set name from user if authenticated
        if self.author and not self.name:
            self.name = self.author.get_full_name() or self.author.username
        super().save(*args, **kwargs)

    def get_display_name(self):
        """Get the name to display for this comment"""
        if self.author:
            return self.author.get_full_name() or self.author.username
        return self.name or "Anonymous"

    def __str__(self):
        return f"{self.get_display_name()} on {self.post.title}"


class PostView(models.Model):
    """Track post views with IP tracking"""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='post_views')
    ip_address = models.GenericIPAddressField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['post', 'ip_address']),
            models.Index(fields=['-viewed_at']),
        ]

    def __str__(self):
        return f"{self.post.title} - {self.ip_address}"


class PostLike(models.Model):
    """Allow users to like posts"""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']
        indexes = [
            models.Index(fields=['post', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"


class Newsletter(models.Model):
    """Newsletter subscription model"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email