from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, FormView, ListView, DetailView
from django.contrib import messages
from django.db.models import Q, Count, Avg, Prefetch
from django.core.paginator import Paginator
from .models import Instructor, Achievement, Testimonial, InstructorReview
from apps.classes.models import KarateClass
from apps.accounts.models import BeltProgress
from apps.blog.models import BlogPost
from apps.gallery.models import GalleryImage
from .forms import ContactForm


class InstructorListView(ListView):
    """Enhanced instructor listing with filters and search"""
    model = Instructor
    template_name = "core/instructors.html"
    context_object_name = "instructors"
    paginate_by = 12
    
    def get_queryset(self):
        qs = Instructor.objects.select_related().prefetch_related(
            'achievements',
            'testimonials'
        ).annotate(
            achievement_count=Count('achievements'),
            testimonial_count=Count('testimonials', filter=Q(testimonials__is_approved=True)),
            avg_rating=Avg('reviews__teaching_quality')
        )
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(bio__icontains=search) |
                Q(specialization__icontains=search)
            )
        
        # Filter by rank
        rank = self.request.GET.get('rank', '')
        if rank:
            qs = qs.filter(rank=rank)
        
        # Filter by specialization
        specialization = self.request.GET.get('specialization', '')
        if specialization:
            qs = qs.filter(specialization=specialization)
        
        # Filter by availability
        available_only = self.request.GET.get('available', '')
        if available_only:
            qs = qs.filter(is_available=True)
        
        # Sorting
        sort = self.request.GET.get('sort', 'default')
        if sort == 'name':
            qs = qs.order_by('name')
        elif sort == 'experience':
            qs = qs.order_by('-experience_years')
        elif sort == 'rating':
            qs = qs.order_by('-avg_rating')
        else:
            qs = qs.order_by('display_order', '-is_featured', '-created_at')
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Our Instructors"
        context['description'] = "Meet our world-class karate instructors"
        
        # Add filter options
        context['rank_choices'] = Instructor.BELT_RANKS
        context['specialization_choices'] = Instructor.SPECIALIZATIONS
        
        # Current filters
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'rank': self.request.GET.get('rank', ''),
            'specialization': self.request.GET.get('specialization', ''),
            'available': self.request.GET.get('available', ''),
            'sort': self.request.GET.get('sort', 'default'),
        }
        
        # Stats
        context['total_instructors'] = Instructor.objects.count()
        context['available_instructors'] = Instructor.objects.filter(is_available=True).count()
        
        return context


class InstructorDetailView(DetailView):
    """Enhanced instructor detail with reviews and stats"""
    model = Instructor
    template_name = "core/instructor_detail.html"
    context_object_name = "instructor"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    
    def get_queryset(self):
        # Don't slice in Prefetch - fetch all and slice in template
        return Instructor.objects.select_related().prefetch_related(
            Prefetch('achievements', queryset=Achievement.objects.order_by('-date')),
            Prefetch('testimonials', queryset=Testimonial.objects.filter(is_approved=True)),
            Prefetch('reviews', queryset=InstructorReview.objects.filter(is_approved=True).select_related('user')),
            'availability_slots'
        ).annotate(
            avg_teaching=Avg('reviews__teaching_quality'),
            avg_communication=Avg('reviews__communication'),
            avg_technique=Avg('reviews__technique'),
            avg_motivation=Avg('reviews__motivation'),
            total_reviews=Count('reviews', filter=Q(reviews__is_approved=True))
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instructor = self.object
        
        # Slice achievements in context (limit to 5 most recent)
        context['recent_achievements'] = instructor.achievements.all()[:5]
        
        # Slice testimonials in context (limit to 6)
        context['recent_testimonials'] = instructor.testimonials.all()[:6]
        
        # Classes taught by this instructor
        context['classes'] = KarateClass.objects.filter(
            instructor=instructor
        ).select_related('instructor').prefetch_related('schedules').order_by('schedules')[:6]
        
        # Calculate overall rating
        if instructor.total_reviews > 0:
            ratings = [
                instructor.avg_teaching or 0,
                instructor.avg_communication or 0,
                instructor.avg_technique or 0,
                instructor.avg_motivation or 0
            ]
            context['overall_rating'] = round(sum(ratings) / 4, 1)
        else:
            context['overall_rating'] = 0
        
        # Similar instructors
        context['similar_instructors'] = Instructor.objects.filter(
            specialization=instructor.specialization
        ).exclude(pk=instructor.pk).select_related()[:3]
        
        return context


class HomePageView(TemplateView):
    """Enhanced homepage with better queries"""
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Featured instructors with stats
        context['instructors'] = Instructor.objects.filter(
            is_featured=True
        ).annotate(
            achievement_count=Count('achievements')
        ).order_by('display_order')[:3]

        # Latest achievements (featured first)
        context['achievements'] = Achievement.objects.select_related(
            'instructor'
        ).filter(
            is_featured=True
        ).order_by('-date')[:5]

        # Featured testimonials only
        context['testimonials'] = Testimonial.objects.filter(
            is_approved=True,
            is_featured=True
        ).select_related('instructor').order_by('-created_at')[:6]

        # Upcoming classes with instructor info (optimized)
        context['classes'] = KarateClass.objects.select_related(
            'instructor'
        ).prefetch_related(
            'schedules'
        ).order_by('schedules')[:6]

        # Belt progression ordered by rank
        context['belts'] = BeltProgress.objects.all().order_by('current_belt')

        # Latest news posts
        context['news'] = BlogPost.objects.select_related(
            'author'
        ).order_by('-created_at')[:3]

        # Gallery images
        context['gallery'] = GalleryImage.objects.order_by('-uploaded_at')[:9]
        
        # Site stats
        context['stats'] = {
            'total_members': 5000,  # Update with actual count
            'total_dojos': 50,
            'total_instructors': Instructor.objects.count(),
            'years_legacy': 30,
        }

        return context


class AboutView(TemplateView):
    """Enhanced about page"""
    template_name = "core/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # All instructors with annotations
        context['instructors'] = Instructor.objects.annotate(
            achievement_count=Count('achievements'),
            student_count=Count('reviews', filter=Q(reviews__is_verified=True))
        ).order_by('display_order')

        # Key achievements only
        context['achievements'] = Achievement.objects.filter(
            is_featured=True
        ).select_related('instructor').order_by('-date')[:8]

        # Top testimonials
        context['testimonials'] = Testimonial.objects.filter(
            is_approved=True
        ).order_by('-rating', '-created_at')[:6]

        # Gallery preview
        context['gallery'] = GalleryImage.objects.order_by('-uploaded_at')[:9]
        
        # Organization stats
        context['org_stats'] = {
            'total_students': 5000,
            'active_instructors': Instructor.objects.filter(is_available=True).count(),
            'dojos': 50,
            'medals': Achievement.objects.filter(achievement_type='competition').count(),
        }

        return context


class ContactView(FormView):
    """Enhanced contact form"""
    template_name = "core/contact.html"
    form_class = ContactForm
    success_url = "/contact/"

    def form_valid(self, form):
        # Process form (send email, save to DB, etc.)
        # TODO: Implement email sending logic
        
        messages.success(
            self.request, 
            "Thank you for contacting us! We'll respond within 24 hours."
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            "Please correct the errors below and try again."
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Contact info
        context['contact_info'] = {
            'email': 'info@kenyakarate.or.ke',
            'phone_primary': '+254 700 123 456',
            'phone_secondary': '+254 733 456 789',
            'address': 'Nyayo National Stadium, Nairobi, Kenya',
            'po_box': 'P.O. Box 12345-00100',
        }
        
        # Operating hours
        context['hours'] = {
            'weekday': '6:00 AM - 9:00 PM',
            'saturday': '8:00 AM - 6:00 PM',
            'sunday': '9:00 AM - 5:00 PM',
        }
        
        return context