from django.urls import path
from .views import (
    HomePageView, 
    AboutView, 
    ContactView,
    InstructorListView,
    InstructorDetailView
)

app_name = 'core'

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("about/", AboutView.as_view(), name="about"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("instructors/", InstructorListView.as_view(), name="instructor_list"),
    path("instructors/<slug:slug>/", InstructorDetailView.as_view(), name="instructor_detail"),
]