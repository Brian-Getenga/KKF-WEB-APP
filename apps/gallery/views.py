from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.db.models import Count, Q
from django.core.paginator import Paginator
from .models import GalleryImage, GalleryCategory


class GalleryView(ListView):
    """Enhanced gallery view with filtering, search, and pagination"""
    model = GalleryImage
    template_name = "gallery/gallery.html"
    context_object_name = "images"
    paginate_by = 24  # Show 24 images per page
    
    def get_queryset(self):
        queryset = GalleryImage.objects.select_related("category").order_by('-is_featured', '-uploaded_at')
        
        # Filter by category
        category_slug = self.request.GET.get("category")
        if category_slug and category_slug != 'all':
            queryset = queryset.filter(category__slug=category_slug)
        
        # Search functionality
        search = self.request.GET.get("search", "")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(caption__icontains=search) |
                Q(category__name__icontains=search)
            )
        
        # Filter by featured status
        featured_only = self.request.GET.get("featured", "")
        if featured_only:
            queryset = queryset.filter(is_featured=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all categories without annotation (use property instead)
        context["categories"] = GalleryCategory.objects.filter(
            is_active=True
        ).order_by('name')
        
        # Current filters
        context['current_category'] = self.request.GET.get("category", "")
        context['current_search'] = self.request.GET.get("search", "")
        
        # Statistics
        context['total_images'] = GalleryImage.objects.count()
        context['featured_count'] = GalleryImage.objects.filter(is_featured=True).count()
        
        return context


class GalleryDetailView(DetailView):
    """Detail view for individual gallery images"""
    model = GalleryImage
    template_name = "gallery/gallery_detail.html"
    context_object_name = "image"
    slug_field = "id"  # Using ID for simplicity, can change to slug if you add it
    slug_url_kwarg = "pk"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        image = self.object
        
        # Get related images from the same category
        if image.category:
            context['related_images'] = GalleryImage.objects.filter(
                category=image.category
            ).exclude(pk=image.pk).order_by('-uploaded_at')[:6]
        else:
            context['related_images'] = GalleryImage.objects.exclude(
                pk=image.pk
            ).order_by('-uploaded_at')[:6]
        
        # Get previous and next images
        all_images = GalleryImage.objects.order_by('-uploaded_at')
        image_list = list(all_images.values_list('id', flat=True))
        
        try:
            current_index = image_list.index(image.id)
            
            # Previous image
            if current_index > 0:
                context['previous_image'] = GalleryImage.objects.get(
                    id=image_list[current_index - 1]
                )
            
            # Next image
            if current_index < len(image_list) - 1:
                context['next_image'] = GalleryImage.objects.get(
                    id=image_list[current_index + 1]
                )
        except (ValueError, GalleryImage.DoesNotExist):
            pass
        
        return context


class CategoryGalleryView(ListView):
    """View for displaying images in a specific category"""
    model = GalleryImage
    template_name = "gallery/category_gallery.html"
    context_object_name = "images"
    paginate_by = 24
    
    def get_queryset(self):
        self.category = GalleryCategory.objects.get(slug=self.kwargs['slug'])
        return GalleryImage.objects.filter(
            category=self.category
        ).order_by('-is_featured', '-uploaded_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = GalleryCategory.objects.annotate(
            image_count=Count('images')
        ).filter(image_count__gt=0).order_by('name')
        return context