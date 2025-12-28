from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # Main blog views
    path('', views.BlogListView.as_view(), name='post_list'),
    path('search/', views.SearchView.as_view(), name='search'),
    
    # Category and Tag views
    path('category/<slug:slug>/', views.CategoryListView.as_view(), name='category_list'),
    path('tag/<slug:slug>/', views.TagListView.as_view(), name='tag_list'),
    
    # Post detail (must be last to avoid conflicts)
    path('<slug:slug>/', views.BlogDetailView.as_view(), name='post_detail'),
    
    # AJAX/API endpoints
    path('api/post/<slug:slug>/like/', views.toggle_like, name='toggle_like'),
    path('api/newsletter/subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),
]