from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import GalleryImage, GalleryCategory, GalleryTag
from PIL import Image
import magic


class GalleryImageForm(forms.ModelForm):
    """Form for creating/editing gallery images"""
    
    # Optional: Uncomment after adding GalleryTag model
    # tags_input = forms.CharField(
    #     required=False,
    #     widget=forms.TextInput(attrs={
    #         'class': 'form-control',
    #         'placeholder': 'Enter tags separated by commas (e.g., training, competition, black-belt)'
    #     }),
    #     help_text='Separate multiple tags with commas'
    # )
    
    class Meta:
        model = GalleryImage
        fields = [
            'category',
            'title',
            'image',
            'video_url',
            'caption',
            'photographer',
            'location',
            'event_date',
            'is_featured',
            'is_public',
            'display_order',
            'meta_description'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/watch?v=...'
            }),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a caption to describe this image'
            }),
            'photographer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Photographer name'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Location where photo was taken'
            }),
            'event_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': 160,
                'placeholder': 'SEO description (max 160 characters)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make image field optional for updates
        if self.instance.pk:
            self.fields['image'].required = False
            
            # Uncomment after adding tags functionality
            # Pre-populate tags field if editing
            # if hasattr(self.instance, 'tags') and self.instance.tags.exists():
            #     tag_names = ', '.join([tag.name for tag in self.instance.tags.all()])
            #     self.fields['tags_input'].initial = tag_names
        
        # Add help text
        self.fields['image'].help_text = 'Supported formats: JPG, PNG, GIF (Max 10MB)'
        self.fields['video_url'].help_text = 'YouTube or Vimeo URL (optional)'
        self.fields['is_featured'].help_text = 'Featured images appear prominently on the gallery page'
        self.fields['display_order'].help_text = 'Lower numbers appear first (0 = highest priority)'
    
    def clean_image(self):
        """Validate uploaded image"""
        image = self.cleaned_data.get('image')
        
        if image:
            # Check file size (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError('Image file size must be less than 10MB.')
            
            # Validate image format
            try:
                img = Image.open(image)
                img.verify()
                
                # Check dimensions (minimum 300x300)
                if img.width < 300 or img.height < 300:
                    raise ValidationError('Image must be at least 300x300 pixels.')
                
                # Validate file type using python-magic
                image.seek(0)
                mime = magic.from_buffer(image.read(2048), mime=True)
                if mime not in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']:
                    raise ValidationError('Invalid image format. Please upload JPG, PNG, GIF, or WebP.')
                
                image.seek(0)  # Reset file pointer
                
            except Exception as e:
                raise ValidationError(f'Invalid image file: {str(e)}')
        
        return image
    
    def clean_video_url(self):
        """Validate video URL"""
        video_url = self.cleaned_data.get('video_url')
        
        if video_url:
            # Basic validation for YouTube and Vimeo
            valid_domains = ['youtube.com', 'youtu.be', 'vimeo.com']
            if not any(domain in video_url.lower() for domain in valid_domains):
                raise ValidationError('Please enter a valid YouTube or Vimeo URL.')
        
        return video_url
    
    # Uncomment after adding GalleryTag model
    # def clean_tags_input(self):
    #     """Clean and validate tags input"""
    #     tags_input = self.cleaned_data.get('tags_input', '').strip()
    #     
    #     if tags_input:
    #         # Split by comma and clean
    #         tag_names = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
    #         
    #         # Limit to 10 tags
    #         if len(tag_names) > 10:
    #             raise ValidationError('Maximum 10 tags allowed.')
    #         
    #         # Validate each tag length
    #         for tag_name in tag_names:
    #             if len(tag_name) > 50:
    #                 raise ValidationError(f'Tag "{tag_name}" is too long (max 50 characters).')
    #         
    #         return tag_names
    #     
    #     return []
    
    def save(self, commit=True):
        """Save the form"""
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
            # Uncomment after adding tags functionality
            # Handle tags
            # tag_names = self.cleaned_data.get('tags_input', [])
            # if tag_names:
            #     instance.tags.clear()
            #     for tag_name in tag_names:
            #         tag, created = GalleryTag.objects.get_or_create(
            #             name=tag_name,
            #             defaults={'slug': slugify(tag_name)}
            #         )
            #         instance.tags.add(tag)
        
        return instance


class GalleryCategoryForm(forms.ModelForm):
    """Form for creating/editing gallery categories"""
    
    class Meta:
        model = GalleryCategory
        fields = ['name', 'description', 'icon', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name (e.g., Training, Competitions)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of this category'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Font Awesome icon class (e.g., fa-camera)'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['icon'].help_text = 'Font Awesome icon class (optional)'
        self.fields['display_order'].help_text = 'Categories are sorted by this order'
        self.fields['is_active'].help_text = 'Inactive categories are hidden from public view'
    
    def clean_name(self):
        """Ensure category name is unique (case-insensitive)"""
        name = self.cleaned_data.get('name')
        
        # Check for duplicate (case-insensitive)
        existing = GalleryCategory.objects.filter(name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise ValidationError('A category with this name already exists.')
        
        return name


class BulkImageUploadForm(forms.Form):
    """Form for uploading multiple images at once"""
    
    category = forms.ModelChoiceField(
        queryset=GalleryCategory.objects.filter(is_active=True),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='Select category for all uploaded images'
    )
    
    images = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*'
        }),
        help_text='Select multiple images (Max 20 files, 10MB each)'
    )
    
    is_featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Mark all as featured'
    )
    
    is_public = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Make all public'
    )
    
    def clean_images(self):
        """Validate multiple image uploads"""
        images = self.files.getlist('images')
        
        if not images:
            raise ValidationError('Please select at least one image.')
        
        if len(images) > 20:
            raise ValidationError('Maximum 20 images can be uploaded at once.')
        
        for image in images:
            # Check file size
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(f'{image.name}: File size must be less than 10MB.')
            
            # Validate image format
            try:
                img = Image.open(image)
                img.verify()
                image.seek(0)
            except Exception:
                raise ValidationError(f'{image.name}: Invalid image file.')
        
        return images


class GallerySearchForm(forms.Form):
    """Form for searching gallery images"""
    
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title, caption, or location...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=GalleryCategory.objects.filter(is_active=True),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    featured_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Featured images only'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='From date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='To date'
    )
    
    order_by = forms.ChoiceField(
        required=False,
        choices=[
            ('-uploaded_at', 'Newest first'),
            ('uploaded_at', 'Oldest first'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('-view_count', 'Most viewed'),
        ],
        initial='-uploaded_at',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )