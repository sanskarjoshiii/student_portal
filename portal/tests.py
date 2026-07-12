"""
End-to-end tests for the EventHub Django app.
Run with:  python manage.py test
"""
from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .emails import make_approval_token
from .models import User, Event, Registration


def make_event(**kw):
    defaults = dict(
        title="Sample Event",
        description="A description that is long enough.",
        category="Seminar",
        department="Computer Science",
        venue="Hall A",
        date=timezone.now() + timedelta(days=5),
    )
    defaults.update(kw)
    return Event.objects.create(**defaults)


class EventListingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="a@x.com", password="pass1234", name="Admin", role="admin"
        )
        make_event(title="Machine Learning Seminar", category="Seminar",
                   created_by=self.admin)
        make_event(title="React Workshop", category="Workshop",
                   department="Design", created_by=self.admin)
        make_event(title="Old Event", category="Seminar",
                   date=timezone.now() - timedelta(days=10), created_by=self.admin)

    def test_home_lists_events(self):
        res = self.client.get(reverse("home"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Machine Learning Seminar")

    def test_search_filter(self):
        res = self.client.get(reverse("home"), {"search": "react"})
        self.assertContains(res, "React Workshop")
        self.assertNotContains(res, "Machine Learning Seminar")

    def test_category_filter(self):
        res = self.client.get(reverse("home"), {"category": "Workshop"})
        self.assertContains(res, "React Workshop")
        self.assertNotContains(res, "Machine Learning Seminar")

    def test_when_past_filter(self):
        res = self.client.get(reverse("home"), {"when": "past"})
        self.assertContains(res, "Old Event")
        self.assertNotContains(res, "React Workshop")


class AuthTests(TestCase):
    def test_student_signup_with_college_age(self):
        res = self.client.post(reverse("register"), {
            "role": "student", "name": "Sam", "email": "sam@x.com",
            "college": "City College", "age": 20, "password": "pass1234",
        })
        self.assertRedirects(res, reverse("home"))
        user = User.objects.get(email="sam@x.com")
        self.assertEqual(user.college, "City College")
        self.assertEqual(user.age, 20)

    def test_signup_missing_college_age_rejected(self):
        res = self.client.post(reverse("register"), {
            "role": "student", "name": "Sam", "email": "sam2@x.com",
            "password": "pass1234",
        })
        self.assertEqual(res.status_code, 200)  # re-rendered with errors
        self.assertFalse(User.objects.filter(email="sam2@x.com").exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@x.com", password="pass1234", name="A",
                                 college="C", age=19)
        res = self.client.post(reverse("register"), {
            "role": "student", "name": "B", "email": "dup@x.com",
            "college": "C", "age": 19, "password": "pass1234",
        })
        self.assertContains(res, "already exists")

    def test_login_and_logout(self):
        User.objects.create_user(email="l@x.com", password="pass1234", name="L",
                                 college="C", age=20)
        res = self.client.post(reverse("login"),
                               {"email": "l@x.com", "password": "pass1234"})
        self.assertRedirects(res, reverse("home"))
        # logged in
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


class RegistrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="a@x.com", password="pass1234",
                                               name="Admin", role="admin")
        self.student = User.objects.create_user(email="s@x.com", password="pass1234",
                                                 name="Stu", college="C", age=20)
        self.event = make_event(capacity=1, created_by=self.admin)

    def login_student(self):
        self.client.login(email="s@x.com", password="pass1234")

    def test_register_for_event(self):
        self.login_student()
        self.client.post(reverse("register_event", args=[self.event.pk]))
        self.assertTrue(Registration.objects.filter(event=self.event,
                                                     user=self.student).exists())

    def test_duplicate_registration_prevented(self):
        self.login_student()
        self.client.post(reverse("register_event", args=[self.event.pk]))
        self.client.post(reverse("register_event", args=[self.event.pk]))
        self.assertEqual(
            Registration.objects.filter(event=self.event, user=self.student).count(), 1
        )

    def test_capacity_enforced(self):
        # capacity is 1 — student takes the last spot, a second student is blocked
        self.login_student()
        self.client.post(reverse("register_event", args=[self.event.pk]))
        other = User.objects.create_user(email="o@x.com", password="pass1234",
                                         name="Other", college="C", age=21)
        self.client.login(email="o@x.com", password="pass1234")
        self.client.post(reverse("register_event", args=[self.event.pk]))
        self.assertEqual(Registration.objects.filter(event=self.event).count(), 1)

    def test_login_required_to_register(self):
        res = self.client.post(reverse("register_event", args=[self.event.pk]))
        self.assertEqual(res.status_code, 302)  # redirected to login
        self.assertFalse(Registration.objects.filter(event=self.event).exists())

    def test_cancel_registration(self):
        self.login_student()
        self.client.post(reverse("register_event", args=[self.event.pk]))
        reg = Registration.objects.get(event=self.event, user=self.student)
        self.client.post(reverse("cancel_registration", args=[reg.pk]))
        self.assertFalse(Registration.objects.filter(pk=reg.pk).exists())


class AdminApprovalTests(TestCase):
    def test_full_admin_request_flow(self):
        # 1. sign up as admin → pending user, email to head, cannot log in
        self.client.post(reverse("register"),
                         {"role": "admin", "name": "New Admin", "email": "na@x.com"})
        user = User.objects.get(email="na@x.com")
        self.assertEqual(user.admin_request_status, "pending")
        self.assertEqual(len(mail.outbox), 1)  # request emailed to head

        # pending user cannot log in
        res = self.client.post(reverse("login"),
                               {"email": "na@x.com", "password": "anything"})
        self.assertContains(res, "awaiting approval")

        # 2. system head approves via the tokenised link
        token = make_approval_token(user.id)
        res = self.client.post(reverse("admin_approval"),
                               {"token": token, "action": "approve"})
        self.assertContains(res, "approved")

        user.refresh_from_db()
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.must_change_password)

        # 3. the password email was sent — extract it
        approval_mail = mail.outbox[-1]
        self.assertIn("na@x.com", approval_mail.to)
        import re
        m = re.search(r"([A-Za-z0-9]{10}@\d{2})", approval_mail.body)
        self.assertIsNotNone(m)
        temp_password = m.group(1)

        # 4. log in with temp password → forced to change password
        res = self.client.post(reverse("login"),
                               {"email": "na@x.com", "password": temp_password})
        self.assertRedirects(res, reverse("change_password"))

        # 5. change the password
        res = self.client.post(reverse("change_password"), {
            "current_password": temp_password,
            "new_password": "MyNewPass1",
            "confirm_password": "MyNewPass1",
        })
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)

        # old temp password no longer works; new one does
        self.client.logout()
        self.assertFalse(self.client.login(email="na@x.com", password=temp_password))
        self.assertTrue(self.client.login(email="na@x.com", password="MyNewPass1"))

    def test_invalid_token_shows_error(self):
        res = self.client.get(reverse("admin_approval"), {"token": "not-real"})
        self.assertContains(res, "invalid")

    def test_reject_flow(self):
        self.client.post(reverse("register"),
                         {"role": "admin", "name": "Rej", "email": "rej@x.com"})
        user = User.objects.get(email="rej@x.com")
        token = make_approval_token(user.id)
        res = self.client.post(reverse("admin_approval"),
                               {"token": token, "action": "reject"})
        self.assertContains(res, "rejected")
        user.refresh_from_db()
        self.assertEqual(user.admin_request_status, "rejected")


class OwnershipTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@x.com", password="pass1234",
                                           name="A", role="admin")
        self.b = User.objects.create_user(email="b@x.com", password="pass1234",
                                           name="B", role="admin")
        self.student = User.objects.create_user(email="s@x.com", password="pass1234",
                                                 name="S", college="C", age=20)
        self.event = make_event(created_by=self.a)

    def test_non_admin_cannot_open_dashboard(self):
        self.client.login(email="s@x.com", password="pass1234")
        res = self.client.get(reverse("admin_dashboard"))
        self.assertRedirects(res, reverse("home"))

    def test_admin_can_create_event(self):
        self.client.login(email="a@x.com", password="pass1234")
        res = self.client.post(reverse("event_create"), {
            "title": "My Event", "description": "A long enough description here.",
            "category": "Workshop", "department": "Design", "venue": "Studio",
            "date": (timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "banner_color": "#e8894e",
        })
        self.assertRedirects(res, reverse("admin_dashboard"))
        self.assertTrue(Event.objects.filter(title="My Event",
                                             created_by=self.a).exists())

    def test_other_admin_cannot_edit_or_delete(self):
        self.client.login(email="b@x.com", password="pass1234")
        # edit
        res = self.client.post(reverse("event_edit", args=[self.event.pk]), {
            "title": "Hijacked", "description": "trying to edit someone else's.",
            "category": "Seminar", "department": "All", "venue": "X",
            "date": (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "banner_color": "#e8894e",
        })
        self.assertRedirects(res, reverse("admin_dashboard"))
        self.event.refresh_from_db()
        self.assertNotEqual(self.event.title, "Hijacked")
        # delete
        self.client.post(reverse("event_delete", args=[self.event.pk]))
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_owner_can_delete_and_registrations_cascade(self):
        Registration.objects.create(event=self.event, user=self.student)
        self.client.login(email="a@x.com", password="pass1234")
        self.client.post(reverse("event_delete", args=[self.event.pk]))
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())
        self.assertEqual(Registration.objects.count(), 0)
