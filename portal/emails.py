"""
Email helpers for the admin-approval workflow.

Uses Django's built-in signing to create a secure, expiring approval token,
and Django's send_mail to deliver messages. With no SMTP configured, Django's
console backend prints emails to the terminal (see settings.py).
"""
import secrets
import string

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail

APPROVAL_SALT = "admin-approval"


def make_approval_token(user_id):
    """Signed token that authorises deciding on an admin request."""
    return signing.dumps({"user_id": user_id}, salt=APPROVAL_SALT)


def read_approval_token(token, max_age_days=10):
    """Return the user_id from a valid token, or raise signing.BadSignature /
    signing.SignatureExpired."""
    data = signing.loads(token, salt=APPROVAL_SALT, max_age=max_age_days * 86400)
    return data["user_id"]


def generate_password():
    """A readable temporary password like 'Kp7mBqx3@42'."""
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(10))
    return f"{core}@{secrets.randbelow(90) + 10}"


def send_admin_request_to_head(user, token):
    link = f"{settings.APP_URL}/admin-approval/?token={token}"
    send_mail(
        subject=f"EventHub — Admin access request from {user.name}",
        message=(
            f"A new admin access request has been submitted on EventHub.\n\n"
            f"Name:  {user.name}\n"
            f"Email: {user.email}\n\n"
            f"Review and approve or reject this request here:\n{link}\n\n"
            f"This link is valid for 10 days. If approved, a temporary password "
            f"is generated and emailed to the requester automatically."
        ),
        from_email=None,
        recipient_list=[settings.SYSTEM_HEAD_EMAIL],
        fail_silently=True,
    )


def send_password_to_user(user, password):
    link = f"{settings.APP_URL}/login/"
    send_mail(
        subject="EventHub — Your admin access has been approved",
        message=(
            f"Hi {user.name},\n\n"
            f"Your request for admin access on EventHub has been approved.\n\n"
            f"Your temporary login password is:\n\n    {password}\n\n"
            f"Log in here: {link}\n"
            f"Use your email ({user.email}) and the password above. You will be "
            f"asked to set your own password on first login."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_rejection_to_user(user):
    send_mail(
        subject="EventHub — Update on your admin access request",
        message=(
            f"Hi {user.name},\n\n"
            f"After review, your request for admin access on EventHub was not "
            f"approved at this time. You can still use EventHub as a student."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )
