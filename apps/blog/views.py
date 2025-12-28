from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import BlogPost, Comment, Category, Tag, PostView, PostLike, Newsletter
from .forms import CommentForm, NewsletterForm


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class BlogListView(ListView):
    """Enhanced blog list with filtering and search"""
    model = BlogPost
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 12

    def get_queryset(self):
        queryset = BlogPost.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category').prefetch_related('tags')
        
        # Search functionality
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(excerpt__icontains=search_query)
            )
        
        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Tag filter
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        
        # Sort options
        sort = self.request.GET.get('sort', '-published_at')
        if sort in ['-published_at', '-views_count', 'title']:
            queryset = queryset.order_by(sort)
        
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        )
        context['popular_tags'] = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        ).order_by('-post_count')[:10]
        context['featured_posts'] = BlogPost.objects.filter(
            status='published',
            featured=True,
            published_at__lte=timezone.now()
        ).select_related('author', 'category')[:3]
        context['search_query'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_tag'] = self.request.GET.get('tag', '')
        return context


class BlogDetailView(DetailView):
    """Enhanced blog detail with analytics and interactions"""
    model = BlogPost
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        return BlogPost.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category').prefetch_related(
            'tags',
            Prefetch(
                'comments',
                queryset=Comment.objects.filter(
                    approved=True,
                    parent__isnull=True
                ).select_related('author').prefetch_related(
                    Prefetch(
                        'replies',
                        queryset=Comment.objects.filter(approved=True).select_related('author')
                    )
                )
            )
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Track view (only once per IP per day)
        ip_address = get_client_ip(self.request)
        today = timezone.now().date()
        
        view_exists = PostView.objects.filter(
            post=obj,
            ip_address=ip_address,
            viewed_at__date=today
        ).exists()
        
        if not view_exists:
            PostView.objects.create(
                post=obj,
                ip_address=ip_address,
                user=self.request.user if self.request.user.is_authenticated else None
            )
            obj.increment_views()
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        
        # Comments
        context['comment_form'] = CommentForm()
        context['comment_count'] = post.comments.filter(approved=True).count()
        
        # Related posts
        context['related_posts'] = post.get_related_posts()
        
        # Reading time
        context['reading_time'] = post.get_reading_time()
        
        # User interactions
        if self.request.user.is_authenticated:
            context['user_has_liked'] = PostLike.objects.filter(
                post=post,
                user=self.request.user
            ).exists()
        else:
            context['user_has_liked'] = False
        
        # Like count
        context['likes_count'] = post.likes.count()
        
        # Next/Previous posts
        context['next_post'] = BlogPost.objects.filter(
            status='published',
            published_at__lt=post.published_at
        ).order_by('-published_at').first()
        
        context['previous_post'] = BlogPost.objects.filter(
            status='published',
            published_at__gt=post.published_at
        ).order_by('published_at').first()
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle comment submission"""
        self.object = self.get_object()
        
        if not self.object.allow_comments:
            messages.error(request, "Comments are disabled for this post.")
            return redirect(self.object.get_absolute_url())
        
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = self.object
            
            if request.user.is_authenticated:
                comment.author = request.user
            else:
                # Require name for guest comments
                if not comment.name:
                    messages.error(request, "Please provide your name.")
                    return self.get(request, *args, **kwargs)
            
            # Handle parent comment for threading
            parent_id = request.POST.get('parent_id')
            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id, post=self.object)
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    pass
            
            comment.save()
            messages.success(request, "Your comment has been posted!")
            return redirect(self.object.get_absolute_url() + '#comments')
        
        messages.error(request, "There was an error with your comment. Please try again.")
        return self.get(request, *args, **kwargs)


@require_POST
@login_required
def toggle_like(request, slug):
    """Toggle like on a blog post"""
    post = get_object_or_404(BlogPost, slug=slug, status='published')
    
    like, created = PostLike.objects.get_or_create(
        post=post,
        user=request.user
    )
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'likes_count': post.likes.count()
    })


@require_POST
def subscribe_newsletter(request):
    """Handle newsletter subscription"""
    form = NewsletterForm(request.POST)
    
    if form.is_valid():
        email = form.cleaned_data['email']
        name = form.cleaned_data.get('name', '')
        
        newsletter, created = Newsletter.objects.get_or_create(
            email=email,
            defaults={'name': name, 'is_active': True}
        )
        
        if not created:
            if not newsletter.is_active:
                newsletter.is_active = True
                newsletter.unsubscribed_at = None
                newsletter.save()
                message = "Welcome back! You've been resubscribed to our newsletter."
            else:
                message = "You're already subscribed to our newsletter."
        else:
            message = "Thank you for subscribing to our newsletter!"
        
        # Handle HTMX requests
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': True, 'message': message})
        
        messages.success(request, message)
    else:
        error_message = "Please provide a valid email address."
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': False, 'message': error_message})
        messages.error(request, error_message)
    
    # Redirect back to referring page or blog list
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('blog:post_list')


class CategoryListView(ListView):
    """List posts by category"""
    model = BlogPost
    template_name = "blog/category_list.html"
    context_object_name = "posts"
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return BlogPost.objects.filter(
            category=self.category,
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class TagListView(ListView):
    """List posts by tag"""
    model = BlogPost
    template_name = "blog/tag_list.html"
    context_object_name = "posts"
    paginate_by = 12

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return BlogPost.objects.filter(
            tags=self.tag,
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author', 'category').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


class SearchView(ListView):
    """Dedicated search view with advanced filtering"""
    model = BlogPost
    template_name = "blog/search_results.html"
    context_object_name = "posts"
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            return BlogPost.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query) |
                Q(tags__name__icontains=query) |
                Q(category__name__icontains=query),
                status='published',
                published_at__lte=timezone.now()
            ).select_related('author', 'category').prefetch_related('tags').distinct()
        return BlogPost.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context