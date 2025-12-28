# gallery/urls.py
from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.GalleryView.as_view(), name='gallery'),
    path('image/<int:pk>/', views.GalleryDetailView.as_view(), name='image_detail'),
    path('category/<slug:slug>/', views.CategoryGalleryView.as_view(), name='category'),
]