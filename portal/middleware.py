from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """
    If a logged-in user must change their password (e.g. a newly approved admin
    who logged in with a temporary password), send them to the change-password
    page and keep them there until they do.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and getattr(user, "must_change_password", False):
            allowed = {
                reverse("change_password"),
                reverse("logout"),
            }
            # Allow static files and the allowed pages through.
            if request.path not in allowed and not request.path.startswith("/static/"):
                return redirect("change_password")
        return self.get_response(request)
