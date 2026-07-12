"""URL configuration for the EventHub project."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django's built-in admin site (for the superuser / system head)
    path("django-admin/", admin.site.urls),
    # Our app
    path("", include("portal.urls")),
]
