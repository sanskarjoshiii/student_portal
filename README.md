# 🎟️ EventHub — Campus Events Portal (Python / Django)

A **full-stack web application built entirely in Python using Django**. Students browse, search and register for campus **seminars, workshops and competitions**, and admins schedule and manage those events — with a real **admin-approval workflow over email**.

> This is the **Python/Django** version of EventHub. Everything here — the web pages, the backend logic, the database, authentication, and emails — is Python.

---

## 🚀 How to run it (step by step)

### 1. Prerequisites
- **Python 3.10+** (tested on 3.12) — check with `python --version`

That's it. The database is **SQLite**, which comes built into Python — no separate database to install.

### 2. Open a terminal in the project folder
```bash
cd student_portal
```

### 3. Create a virtual environment (isolates the project's packages)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```
You'll know it worked when your prompt starts with `(venv)`.

### 4. Install the dependencies
```bash
pip install -r requirements.txt
```

### 5. Create the database tables
```bash
python manage.py migrate
```

### 6. Add sample data (1 admin, 1 student, 11 events)
```bash
python manage.py seed
```

### 7. Start the server
```bash
python manage.py runserver
```
Open **http://127.0.0.1:8000** 🎉

### 8. Demo logins
```
Admin:    admin@eventhub.test   /  Admin@123
Student:  student@eventhub.test /  Student@123
```

### Handy commands
| Command | What it does |
|---|---|
| `python manage.py runserver` | Start the app (http://127.0.0.1:8000) |
| `python manage.py seed` | Reset the database to fresh sample data |
| `python manage.py test` | Run the 20 automated tests |
| `python manage.py createsuperuser` | Make your own admin login for `/django-admin/` |

---

## 📌 What is this project?

- **A campus events portal** — students find events and register in one click.
- **Two kinds of users:**
  - **Students** — browse, search, filter, register, and manage their registrations.
  - **Admins** — everything students can do **plus** create/edit/delete events and see who registered.
- **Becoming an admin is approved, not automatic.** An admin sign-up sends an **email to a "system head"** who approves or rejects it. On approval, a **temporary password is emailed** to the requester, who is then **forced to set their own password** on first login.
- **Multiple admins** can each manage their own events, and view everyone's events.
- **Two admin experiences:** a custom dashboard for day-to-day work, **and** Django's built-in admin panel at `/django-admin/`.

---

## 🧱 Tech stack (all Python)

| Layer | Technology | Why |
|---|---|---|
| Language | **Python 3** | The whole app |
| Web framework | **Django 5** | Handles URLs, views, forms, sessions, templates, the admin panel |
| Database | **SQLite** | Built into Python — zero setup |
| ORM | **Django ORM** | Talk to the database using Python classes, not SQL |
| Templates | **Django Template Language** | Renders the HTML pages |
| Auth | **Django auth** | Password hashing, login sessions, permissions |
| Email | **Django `send_mail`** | The approval + password emails |
| Config | **python-dotenv** | Loads settings from a `.env` file |
| Styling | **Plain CSS** (self-written) | The warm, minimal look |

### Project structure
```
student_portal/
├─ manage.py                 # Django's command-line tool
├─ requirements.txt          # Python dependencies
├─ config/                   # Project settings
│  ├─ settings.py            # Database, email, apps, middleware
│  └─ urls.py                # Top-level URL routing
├─ portal/                   # The main app (all our code)
│  ├─ models.py              # User, Event, Registration (database tables)
│  ├─ views.py               # The logic behind each page
│  ├─ urls.py                # URL → view mapping
│  ├─ forms.py               # Signup / event / password forms + validation
│  ├─ emails.py              # Approval token + email builders
│  ├─ middleware.py          # Forces temp-password users to change it
│  ├─ admin.py               # Registers models in Django's admin panel
│  ├─ tests.py               # 20 automated tests
│  └─ management/commands/seed.py   # `python manage.py seed`
├─ templates/                # HTML pages
└─ static/css/style.css      # Styling
```

---

## ⭐ Important features (what + tech + how)

### 1. Browse, search & filter events
**What:** The home page lists all events. You can search by text and filter by category, department and time (upcoming/past), then sort.
**Tech:** Django views + the **Django ORM** (`Q` objects for the search).
**How:** `home()` in `portal/views.py` reads the query parameters and builds a database query — `Q(title__icontains=...) | Q(description__icontains=...)` for search, and `.filter(...)` for each dropdown. The template renders the results as cards.

### 2. Accounts & login
**What:** Register, log in, log out. Protected pages redirect to login.
**Tech:** **Django's authentication system** + a **custom User model**.
**How:** We use a custom `User` (in `models.py`) that logs in with **email instead of a username**. Django hashes passwords automatically and stores the login in a session cookie. The `@login_required` decorator protects pages.

### 3. Student sign-up with college & age
**What:** Students provide their **college** and **age** at sign-up; admins can see these later.
**Tech:** **Django Forms** for validation.
**How:** `StudentSignupForm` validates the fields (e.g. age must be 15–100) before the user is created.

### 4. Registering for events (no duplicates, respects capacity)
**What:** One-click register; you can't register twice; full events are blocked.
**Tech:** A database **`unique_together` constraint** + checks in the view.
**How:** The `Registration` model has `unique_together = ("event", "user")`, so the database itself blocks duplicates. The view also compares the registration count against the event's `capacity`.

### 5. Admin-approval workflow (the standout feature)
**What:** Signing up as an admin emails an approval request to the system head, who approves/rejects from a link. On approval, a temporary password is emailed to the requester.
**Tech:** Django's **`signing`** module (a secure, expiring token) + **`send_mail`**.
**How:** In `emails.py`, `make_approval_token()` creates a signed token valid for 10 days. It's put in a link and emailed to the system head. The `admin_approval` view verifies the token, shows Approve/Reject buttons, and on approval generates a random password, promotes the user to admin, and emails the password.

### 6. Forced password change on first login
**What:** A new admin who logs in with the temporary password must set their own before doing anything else.
**Tech:** A **custom Django middleware**.
**How:** Approval sets `must_change_password = True`. `ForcePasswordChangeMiddleware` (in `middleware.py`) runs on every request and redirects such users to the change-password page until they submit a new password.

### 7. Multi-admin dashboard (ownership-scoped)
**What:** A dashboard with three tabs — **My Scheduled Events** (edit/delete), **Registrations** (who signed up, with college & age, **CSV export**), and **All Events** (read-only). Admins can only edit their own events.
**Tech:** Django views + ORM queries filtered by `created_by`; Python's **`csv`** module for the export.
**How:** Each event records `created_by`. The dashboard queries "my" vs "all" accordingly, and edit/delete/registrant views check ownership before allowing the action.

### 8. Django's built-in admin panel
**What:** A ready-made admin interface at **`/django-admin/`** to manage users, events and registrations.
**Tech:** **Django admin** (`portal/admin.py`).
**How:** We register the models with Django admin — it auto-builds full create/read/update/delete screens. Log in with a superuser (`admin@eventhub.test / Admin@123` from the seed).

### 9. Email (console by default, real email optional)
**What:** Approval and password emails. With no email configured, they print to the terminal so you can still test everything.
**Tech:** Django's email backends.
**How:** `settings.py` uses the **console backend** by default (prints emails). Fill in `SMTP_*` in a `.env` file (e.g. Gmail with an App Password) to send real email — no code change.

---

## 🧪 Testing

The project ships with **20 automated tests** (`portal/tests.py`) using Django's test framework. They cover listing/search/filters, sign-up (incl. college/age validation), login, event registration rules (duplicates + capacity), the full admin-approval + forced-password-change flow, and ownership checks.

```bash
python manage.py test
```

Django spins up a temporary test database and captures emails in memory, so running tests never touches your real data or sends real email.

---

## 🗺️ Pages at a glance

| URL | Who | What |
|---|---|---|
| `/` | Everyone | Home — events with search & filters |
| `/events/<id>/` | Everyone | Event details + register |
| `/register/` | Everyone | Sign up (Student or request Admin) |
| `/login/`, `/logout/` | Everyone | Auth |
| `/admin-approval/?token=…` | System head (email link) | Approve/reject an admin request |
| `/change-password/` | Logged-in | Set a new password (forced for new admins) |
| `/my-registrations/` | Students | Your registrations, with cancel |
| `/dashboard/` | Admins | Custom dashboard (my / registrations / all) |
| `/dashboard/events/new/` etc. | Admins | Create / edit / delete events, registrants + CSV |
| `/django-admin/` | Superuser | Django's built-in admin panel |

---

## 🔧 Optional: send real emails (Gmail)

Copy `.env.example` to `.env` and fill in:
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your16charapppassword   # Google Account → App Passwords
SMTP_FROM=EventHub <your-gmail@gmail.com>
SYSTEM_HEAD_EMAIL=who-approves@gmail.com
```
Restart the server. Without these, emails are printed to the terminal.

---

*EventHub (Python / Django) — Seminars · Workshops · Competitions.*
