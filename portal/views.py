import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .emails import (
    generate_password,
    make_approval_token,
    read_approval_token,
    send_admin_request_to_head,
    send_password_to_user,
    send_rejection_to_user,
)
from .forms import (
    AdminRequestForm,
    ChangePasswordForm,
    EventForm,
    LoginForm,
    StudentSignupForm,
)
from .models import Event, Registration, User


# ---------------------------------------------------------------------------
# Public: events listing + detail
# ---------------------------------------------------------------------------
def home(request):
    events = Event.objects.select_related("created_by").all()

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()
    department = request.GET.get("department", "").strip()
    when = request.GET.get("when", "").strip()
    sort = request.GET.get("sort", "date-asc").strip()

    if search:
        events = events.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if category and category != "All":
        events = events.filter(category=category)
    if department and department != "All":
        events = events.filter(department=department)

    now = timezone.now()
    if when == "upcoming":
        events = events.filter(date__gte=now)
    elif when == "past":
        events = events.filter(date__lt=now)

    events = events.order_by("-date" if sort == "date-desc" else "date")
    events = list(events)
    if sort == "popular":
        events.sort(key=lambda e: e.registered_count, reverse=True)

    context = {
        "events": events,
        "count": len(events),
        "search": search,
        "category": category,
        "department": department,
        "when": when,
        "sort": sort,
        "categories": [c[0] for c in Event.CATEGORY_CHOICES],
        "departments": [d[0] for d in Event.DEPARTMENT_CHOICES],
        "has_filters": any([search, category, department, when]) or sort != "date-asc",
    }
    return render(request, "portal/home.html", context)


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    my_registration = None
    if request.user.is_authenticated:
        my_registration = Registration.objects.filter(
            event=event, user=request.user
        ).first()
    return render(request, "portal/event_detail.html", {
        "event": event,
        "my_registration": my_registration,
    })


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------
@login_required
def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method != "POST":
        return redirect("event_detail", pk=pk)

    if event.is_past:
        messages.error(request, "This event has already ended.")
        return redirect("event_detail", pk=pk)

    if Registration.objects.filter(event=event, user=request.user).exists():
        messages.info(request, "You are already registered for this event.")
        return redirect("event_detail", pk=pk)

    if event.is_full:
        messages.error(request, "This event is full.")
        return redirect("event_detail", pk=pk)

    Registration.objects.create(event=event, user=request.user)
    messages.success(request, f"You're registered for “{event.title}”.")
    return redirect("event_detail", pk=pk)


@login_required
def cancel_registration(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    if registration.user != request.user and request.user.role != "admin":
        messages.error(request, "You cannot cancel this registration.")
        return redirect("my_registrations")
    if request.method == "POST":
        registration.delete()
        messages.success(request, "Registration cancelled.")
    return redirect(request.POST.get("next") or "my_registrations")


@login_required
def my_registrations(request):
    registrations = (
        Registration.objects.filter(user=request.user)
        .select_related("event")
        .order_by("-registered_at")
    )
    return render(request, "portal/my_registrations.html", {"registrations": registrations})


# ---------------------------------------------------------------------------
# Auth: signup (student or admin request), login, logout, change password
# ---------------------------------------------------------------------------
def register(request):
    role = request.POST.get("role") if request.method == "POST" else request.GET.get("role", "student")
    role = "admin" if role == "admin" else "student"

    if role == "admin":
        form = AdminRequestForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            # Pending user with NO usable password (they can't log in yet).
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                password=None,
                name=form.cleaned_data["name"],
                role="student",
                admin_request_status="pending",
                requested_at=timezone.now(),
            )
            user.set_unusable_password()
            user.save()
            token = make_approval_token(user.id)
            send_admin_request_to_head(user, token)
            return render(request, "portal/register_pending.html", {
                "system_head": settings.SYSTEM_HEAD_EMAIL,
            })
        return render(request, "portal/register.html", {"form": form, "role": "admin"})

    # Student signup (with college + age)
    form = StudentSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            name=form.cleaned_data["name"],
            college=form.cleaned_data["college"],
            age=form.cleaned_data["age"],
            role="student",
        )
        login(request, user)
        messages.success(request, f"Welcome, {user.name}!")
        return redirect("home")
    return render(request, "portal/register.html", {"form": form, "role": "student"})


def login_view(request):
    form = LoginForm(request.POST or None)
    next_url = request.GET.get("next", "")
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        password = form.cleaned_data["password"]

        # Block pending admin requests with a clear message.
        pending = User.objects.filter(email=email, admin_request_status="pending").first()
        if pending:
            messages.error(
                request,
                "Your admin access request is awaiting approval. "
                "You'll receive your password by email once approved.",
            )
            return render(request, "portal/login.html", {"form": form})

        user = authenticate(request, email=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "portal/login.html", {"form": form})

        login(request, user)
        if user.must_change_password:
            return redirect("change_password")
        return redirect(next_url or "home")
    return render(request, "portal/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def change_password(request):
    form = ChangePasswordForm(request.POST or None)
    forced = request.user.must_change_password
    if request.method == "POST" and form.is_valid():
        if not request.user.check_password(form.cleaned_data["current_password"]):
            messages.error(request, "Your current password is incorrect.")
        else:
            request.user.set_password(form.cleaned_data["new_password"])
            request.user.must_change_password = False
            request.user.save()
            update_session_auth_hash(request, request.user)  # stay logged in
            messages.success(request, "Password updated.")
            return redirect("admin_dashboard" if request.user.role == "admin" else "home")
    return render(request, "portal/change_password.html", {"form": form, "forced": forced})


# ---------------------------------------------------------------------------
# Admin-approval workflow (system head clicks the emailed link)
# ---------------------------------------------------------------------------
def admin_approval(request):
    token = request.GET.get("token") or request.POST.get("token")
    try:
        user_id = read_approval_token(token)
    except signing.SignatureExpired:
        return render(request, "portal/admin_approval.html",
                      {"error": "This approval link has expired (valid for 10 days)."})
    except (signing.BadSignature, TypeError):
        return render(request, "portal/admin_approval.html",
                      {"error": "This approval link is invalid."})

    user = User.objects.filter(id=user_id).first()
    if not user:
        return render(request, "portal/admin_approval.html",
                      {"error": "This request no longer exists."})

    # Already decided?
    if user.admin_request_status in ("approved", "rejected"):
        return render(request, "portal/admin_approval.html", {
            "user_obj": user, "result": user.admin_request_status, "already": True,
        })

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            password = generate_password()
            user.set_password(password)
            user.role = "admin"
            user.is_staff = True  # can also use Django's /admin/
            user.admin_request_status = "approved"
            user.must_change_password = True
            user.decided_at = timezone.now()
            user.save()
            send_password_to_user(user, password)
            return render(request, "portal/admin_approval.html",
                          {"user_obj": user, "result": "approved"})
        elif action == "reject":
            user.admin_request_status = "rejected"
            user.decided_at = timezone.now()
            user.save()
            send_rejection_to_user(user)
            return render(request, "portal/admin_approval.html",
                          {"user_obj": user, "result": "rejected"})

    return render(request, "portal/admin_approval.html", {"user_obj": user, "token": token})


# ---------------------------------------------------------------------------
# Admin area (approved admins) — ownership-scoped
# ---------------------------------------------------------------------------
def admin_required(view):
    """Decorator: only logged-in admins may proceed."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != "admin":
            messages.error(request, "Admin access required.")
            return redirect("home")
        return view(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    tab = request.GET.get("tab", "my")
    my_events = Event.objects.filter(created_by=request.user).order_by("date")
    my_reg_total = Registration.objects.filter(event__created_by=request.user).count()

    context = {
        "tab": tab,
        "my_events": my_events,
        "my_events_count": my_events.count(),
        "my_reg_total": my_reg_total,
    }

    if tab == "all":
        context["all_events"] = Event.objects.select_related("created_by").order_by("date")
    elif tab == "registrations":
        context["registrations"] = (
            Registration.objects.filter(event__created_by=request.user)
            .select_related("user", "event")
            .order_by("-registered_at")
        )
    return render(request, "portal/admin_dashboard.html", context)


@admin_required
def event_create(request):
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.created_by = request.user
        event.save()
        messages.success(request, "Event created.")
        return redirect("admin_dashboard")
    return render(request, "portal/event_form.html", {"form": form, "mode": "new"})


@admin_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.created_by_id and event.created_by_id != request.user.id:
        messages.error(request, "You can only edit events you created.")
        return redirect("admin_dashboard")
    form = EventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Event updated.")
        return redirect("admin_dashboard")
    return render(request, "portal/event_form.html", {"form": form, "mode": "edit", "event": event})


@admin_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.created_by_id and event.created_by_id != request.user.id:
        messages.error(request, "You can only delete events you created.")
        return redirect("admin_dashboard")
    if request.method == "POST":
        title = event.title
        event.delete()  # cascades to registrations
        messages.success(request, f"Deleted “{title}” and its registrations.")
    return redirect("admin_dashboard")


@admin_required
def event_registrants(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.created_by_id and event.created_by_id != request.user.id:
        messages.error(request, "You can only view registrants for events you created.")
        return redirect("admin_dashboard")
    registrations = (
        Registration.objects.filter(event=event).select_related("user").order_by("registered_at")
    )
    return render(request, "portal/registrants.html", {
        "event": event, "registrations": registrations,
    })


@admin_required
def event_registrants_csv(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.created_by_id and event.created_by_id != request.user.id:
        return redirect("admin_dashboard")
    registrations = (
        Registration.objects.filter(event=event).select_related("user").order_by("registered_at")
    )
    response = HttpResponse(content_type="text/csv")
    slug = "".join(c if c.isalnum() else "-" for c in event.title).lower()
    response["Content-Disposition"] = f'attachment; filename="registrants-{slug}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "College", "Age", "Registered At"])
    for r in registrations:
        writer.writerow([
            r.user.name, r.user.email, r.user.college or "",
            r.user.age or "", r.registered_at.isoformat(),
        ])
    return response
