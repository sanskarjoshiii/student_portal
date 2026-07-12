from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager for our email-as-username custom user model."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("role", "student")
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """
    A user logs in with their EMAIL (not a username). Students can register
    directly; admins must be approved by the system head.
    """
    ROLE_CHOICES = [("student", "Student"), ("admin", "Admin")]
    REQUEST_CHOICES = [
        ("none", "None"),
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    # Remove username; use email instead.
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=80)

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="student")

    # Student profile fields.
    college = models.CharField(max_length=120, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    # Admin-access request lifecycle.
    admin_request_status = models.CharField(
        max_length=10, choices=REQUEST_CHOICES, default="none"
    )
    requested_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    # Forces a password change on next login (temporary admin password).
    must_change_password = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Event(models.Model):
    CATEGORY_CHOICES = [
        ("Seminar", "Seminar"),
        ("Workshop", "Workshop"),
        ("Competition", "Competition"),
    ]
    DEPARTMENT_CHOICES = [
        ("All", "All"),
        ("Computer Science", "Computer Science"),
        ("Electronics", "Electronics"),
        ("Mechanical", "Mechanical"),
        ("Civil", "Civil"),
        ("Electrical", "Electrical"),
        ("Business", "Business"),
        ("Design", "Design"),
    ]

    title = models.CharField(max_length=160)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    department = models.CharField(max_length=40, choices=DEPARTMENT_CHOICES, default="All")
    venue = models.CharField(max_length=160)
    date = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True)
    organizer = models.CharField(max_length=120, blank=True)
    banner_color = models.CharField(max_length=7, default="#e8894e")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="events"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return self.title

    @property
    def registered_count(self):
        return self.registrations.count()

    @property
    def spots_left(self):
        if self.capacity is None:
            return None
        return max(0, self.capacity - self.registered_count)

    @property
    def is_full(self):
        return self.capacity is not None and self.registered_count >= self.capacity

    @property
    def is_past(self):
        return self.date < timezone.now()


class Registration(models.Model):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="registrations"
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user cannot register twice for the same event.
        unique_together = ("event", "user")
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.user.email} → {self.event.title}"
