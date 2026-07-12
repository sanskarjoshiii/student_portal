from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Event, Registration


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "name", "role", "admin_request_status", "is_staff")
    list_filter = ("role", "admin_request_status", "is_staff")
    search_fields = ("email", "name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "college", "age", "role")}),
        ("Admin request", {"fields": ("admin_request_status", "must_change_password",
                                       "requested_at", "decided_at")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",
                                     "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "role"),
        }),
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "department", "date", "capacity", "created_by")
    list_filter = ("category", "department")
    search_fields = ("title", "description", "venue")
    date_hierarchy = "date"


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "registered_at")
    search_fields = ("event__title", "user__email", "user__name")
