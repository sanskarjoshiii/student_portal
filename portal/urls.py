from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("events/<int:pk>/", views.event_detail, name="event_detail"),
    path("events/<int:pk>/register/", views.register_event, name="register_event"),
    path("registrations/<int:pk>/cancel/", views.cancel_registration, name="cancel_registration"),
    path("my-registrations/", views.my_registrations, name="my_registrations"),

    # Auth
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),

    # Admin-approval (system head, via emailed link)
    path("admin-approval/", views.admin_approval, name="admin_approval"),

    # Admin area
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/events/new/", views.event_create, name="event_create"),
    path("dashboard/events/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("dashboard/events/<int:pk>/delete/", views.event_delete, name="event_delete"),
    path("dashboard/events/<int:pk>/registrants/", views.event_registrants, name="event_registrants"),
    path("dashboard/events/<int:pk>/registrants.csv", views.event_registrants_csv, name="event_registrants_csv"),
]
