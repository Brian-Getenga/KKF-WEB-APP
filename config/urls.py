from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Core and main site
    path("", include(("apps.core.urls", "core"), namespace="core")),

    # User accounts
    path("accounts/", include(("apps.accounts.urls", "accounts"), namespace="accounts")),
    path("accounts/", include("allauth.urls")),  # Django Allauth routes

    # Classes / dojo schedule
    path("classes/", include(("apps.classes.urls", "classes"), namespace="classes")),

    # Store / e-commerce
    path("store/", include(("apps.store.urls", "store"), namespace="store")),

    # Blog / news
    path("blog/", include(("apps.blog.urls", "blog"), namespace="blog")),

    # Gallery
    path("gallery/", include(("apps.gallery.urls", "gallery"), namespace="gallery")),
    # newsletter
   path("", include(("apps.newsletter.urls", "newsletter"), namespace="newsletter")),
   



    # Default favicon and redirects
    path("favicon.ico", RedirectView.as_view(url="/static/images/logo.png")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Media and static serving (development only)
#if settings.DEBUG:
 #   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
  #  urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
