"""
Seed the database with an admin, a student, and ~11 sample events.
Run with:  python manage.py seed
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from portal.models import User, Event, Registration


def days_from_now(n, hour=10):
    d = timezone.now() + timedelta(days=n)
    return d.replace(hour=hour, minute=0, second=0, microsecond=0)


class Command(BaseCommand):
    help = "Reset the database to fresh sample data."

    def handle(self, *args, **options):
        Registration.objects.all().delete()
        Event.objects.all().delete()
        User.objects.all().delete()
        self.stdout.write("Cleared existing data.")

        admin = User.objects.create_superuser(
            email="admin@eventhub.test", password="Admin@123", name="Site Admin",
        )
        admin.role = "admin"
        admin.save()

        student = User.objects.create_user(
            email="student@eventhub.test", password="Student@123", name="Sam Student",
            college="City Engineering College", age=20,
        )
        self.stdout.write("Created admin + demo student.")

        events_data = [
            ("Intro to Machine Learning", "A beginner-friendly seminar covering the fundamentals of machine learning: supervised vs unsupervised learning, common algorithms, and where to start.", "Seminar", "Computer Science", "Auditorium A", days_from_now(7), 120, "AI Club", "#4f46e5"),
            ("Hands-on React Workshop", "Build your first interactive web app in this 3-hour hands-on workshop. We'll cover components, state, and hooks. Bring a laptop.", "Workshop", "Computer Science", "Lab 204", days_from_now(10, 14), 40, "Web Dev Society", "#10b981"),
            ("Annual Hackathon 2026", "24 hours. Any idea. Form a team and build something amazing. Prizes for the top three teams plus special category awards.", "Competition", "All", "Innovation Center", days_from_now(21, 9), 200, "Student Council", "#f59e0b"),
            ("Robotics Design Challenge", "Design and program a robot to complete an obstacle course. Teams of up to four. Kits provided on the day.", "Competition", "Mechanical", "Engineering Hall", days_from_now(14, 11), 60, "Robotics Club", "#ef4444"),
            ("Circuit Design with PCB", "A practical workshop on designing printed circuit boards from schematic to layout using open-source tools.", "Workshop", "Electronics", "Lab 110", days_from_now(5, 15), 30, "Electronics Guild", "#0ea5e9"),
            ("Startup Pitch Night", "Pitch your startup idea to a panel of investors and mentors. Five minutes each. Great networking opportunity.", "Seminar", "Business", "Business School Atrium", days_from_now(12, 18), 80, "Entrepreneurship Cell", "#8b5cf6"),
            ("UI/UX Design Sprint", "Learn the design thinking process and run a mini design sprint. Perfect for anyone interested in product design.", "Workshop", "Design", "Design Studio 1", days_from_now(9, 13), 25, "Design Collective", "#ec4899"),
            ("Bridge Building Contest", "Build the strongest bridge using only the provided materials. Bridges are load-tested live. Individual or pairs.", "Competition", "Civil", "Structures Lab", days_from_now(18, 10), 50, "Civil Engineering Society", "#14b8a6"),
            ("Renewable Energy Seminar", "Industry experts discuss the future of solar, wind, and grid storage. Q&A session included. Open to all.", "Seminar", "Electrical", "Auditorium B", days_from_now(3, 16), None, "Energy Forum", "#e8894e"),
            ("Git & GitHub Crash Course", "A past workshop introducing version control with Git and collaboration on GitHub.", "Workshop", "Computer Science", "Lab 201", days_from_now(-12, 14), 40, "Web Dev Society", "#10b981"),
            ("Data Science Symposium", "A concluded seminar on real-world data science case studies from healthcare to finance.", "Seminar", "Computer Science", "Auditorium A", days_from_now(-30, 10), 150, "AI Club", "#4f46e5"),
        ]

        created = []
        for (title, desc, cat, dept, venue, date, cap, org, color) in events_data:
            created.append(Event.objects.create(
                title=title, description=desc, category=cat, department=dept,
                venue=venue, date=date, capacity=cap, organizer=org,
                banner_color=color, created_by=admin,
            ))
        self.stdout.write(f"Inserted {len(created)} sample events.")

        Registration.objects.create(event=created[0], user=student)
        Registration.objects.create(event=created[1], user=student)
        self.stdout.write("Registered demo student for 2 events.")

        self.stdout.write(self.style.SUCCESS("\nSeed complete!"))
        self.stdout.write("  Admin login:   admin@eventhub.test / Admin@123")
        self.stdout.write("  Student login: student@eventhub.test / Student@123")
