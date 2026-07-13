"""
Django settings for EventHub (Python full-stack version).
Beginner-friendly: SQLite database, console email by default.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file if present.
load_dotenv(BASE_DIR / ".env")

# Fix outgoing-email TLS certificate verification on systems (especially
# Windows) where Python can't find the root certificates. `truststore` uses the
# operating system's trust store; `certifi` is a fallback CA bundle.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    try:
        import certifi
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except Exception:
        pass

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-0im*qiqo$h8f4i66nn7-_qn7=!k68wo%ol_ic49j*db6-q5h#(",
)

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]  # fine for local development / a submission

# Render sets RENDER_EXTERNAL_HOSTNAME to your app's public hostname.
# Django needs it in CSRF_TRUSTED_ORIGINS or every form POST returns a 403.
RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_HOST}"] if RENDER_HOST else []

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves static files (CSS/admin) in production without a separate server.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Forces users with a temporary password to change it before continuing.
    "portal.middleware.ForcePasswordChangeMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — SQLite locally, Postgres in production.
# If DATABASE_URL is set (Render), use it; otherwise fall back to SQLite.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
if os.getenv("DATABASE_URL"):
    import dj_database_url
    DATABASES["default"] = dj_database_url.config(
        conn_max_age=600, ssl_require=True
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
]

# Our custom user model (email login + student/admin fields)
AUTH_USER_MODEL = "portal.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Where `collectstatic` gathers files for WhiteNoise to serve in production.
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- EventHub custom settings ---

# Who approves admin-access requests.
SYSTEM_HEAD_EMAIL = os.getenv("SYSTEM_HEAD_EMAIL", "premajoshi1100@gmail.com")

# Base URL used to build links inside emails.
APP_URL = os.getenv("APP_URL", "http://127.0.0.1:8000")

# --- Email ---
# By default, emails are printed to the terminal (console backend) — great for
# development. Set SMTP_* in .env to send real email (e.g. Gmail).
if os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("SMTP_HOST")
    EMAIL_PORT = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("SMTP_USER")
    EMAIL_HOST_PASSWORD = os.getenv("SMTP_PASS")
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = os.getenv("SMTP_FROM", os.getenv("SMTP_USER"))
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "EventHub <no-reply@eventhub.test>"
