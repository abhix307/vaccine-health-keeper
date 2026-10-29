"""Seed SYNTHETIC demo data for local demonstration.

Safety rules:
* Creates the demo user ONLY if that exact email does not already exist.
* Never modifies or deletes existing users or records.
* All names/dates are fictional. No real patient information anywhere.

Usage:  python scripts/seed_demo.py
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (Allergy, EmergencyContact, HealthProfile, User,  # noqa: E402
                        Vaccination)

DEMO_EMAIL = "demo@example.com"  # RFC 2606 documentation domain, never a real inbox
DEMO_PASSWORD = "DemoPass123!"
TODAY = date.today()


def seed(app):
    with app.app_context():
        db.create_all()
        existing = db.session.execute(
            db.select(User).where(User.email == DEMO_EMAIL)
        ).scalar_one_or_none()
        if existing:
            print(f"Demo user already exists (id={existing.id}); nothing changed.")
            return

        user = User(name="Demo Person", email=DEMO_EMAIL)
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        db.session.flush()

        vaccinations = [
            ("Hepatitis B", 1, TODAY - timedelta(days=200), TODAY - timedelta(days=20), "City Clinic"),
            ("Hepatitis B", 2, TODAY - timedelta(days=20), TODAY + timedelta(days=140), "Second dose per nurse's schedule"),
            ("Td Booster", 1, TODAY - timedelta(days=400), TODAY, "Due today sample"),
            ("MMR", 1, TODAY - timedelta(days=700), TODAY - timedelta(days=30), "Overdue sample"),
            ("Influenza", 1, TODAY - timedelta(days=90), None, "Annual shot, no next dose booked"),
        ]
        for name, dose, vdate, ndate, note in vaccinations:
            db.session.add(Vaccination(
                user_id=user.id, vaccine_name=name, dose_number=dose,
                vaccination_date=vdate, next_dose_date=ndate, notes=note,
            ))

        db.session.add(HealthProfile(
            user_id=user.id, date_of_birth=date(1995, 4, 12),
            blood_group="O+", health_notes="Synthetic demo profile. No real medical information.",
        ))
        db.session.add(Allergy(user_id=user.id, allergen="Penicillin", severity="Severe",
                               notes="Fictional demo entry."))
        db.session.add(Allergy(user_id=user.id, allergen="Peanuts", severity="Mild"))
        db.session.add(EmergencyContact(user_id=user.id, name="Demo Friend",
                                        relationship="Friend", phone_number="+91 90000 00000"))

        db.session.commit()
        print(f"Created synthetic demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print("(Login credentials are for a fictional account with fictional data.)")


if __name__ == "__main__":
    seed(create_app())
