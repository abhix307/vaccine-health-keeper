"""Model-level constraints, relationships, and cascade behaviour."""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (Allergy, EmergencyContact, HealthProfile, User,
                        Vaccination)
from tests.conftest import add_vaccination, make_user


def test_email_unique_constraint(app, db):
    with app.app_context():
        make_user(email="dupe@example.com")
        dupe = User(name="Second", email="dupe@example.com")
        dupe.set_password("Whatever123!")
        db.session.add(dupe)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_vaccination_requires_user(app, db):
    with app.app_context():
        bad = Vaccination(user_id=None, vaccine_name="Orphan", dose_number=1,
                          vaccination_date=date.today())
        db.session.add(bad)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_dates_are_real_date_types(app, db, user):
    with app.app_context():
        rec = add_vaccination(user.id, vdate=date(2025, 6, 1), ndate=date(2026, 6, 1))
        fresh = db.session.get(Vaccination, rec.id)
        assert isinstance(fresh.vaccination_date, date)
        assert isinstance(fresh.next_dose_date, date)
        assert isinstance(fresh.created_at.isoformat(), str)


def test_user_relationships(app, db, user):
    with app.app_context():
        add_vaccination(user.id, name="Rel1")
        add_vaccination(user.id, name="Rel2")
        db.session.add(Allergy(user_id=user.id, allergen="X", severity="Mild"))
        db.session.add(EmergencyContact(user_id=user.id, name="C", relationship="R",
                                        phone_number="555-1234"))
        db.session.add(HealthProfile(user_id=user.id, blood_group="B+"))
        db.session.commit()
        fresh = db.session.get(User, user.id)
        assert len(fresh.vaccinations) == 2
        assert len(fresh.allergies) == 1
        assert len(fresh.emergency_contacts) == 1
        assert fresh.health_profile.blood_group == "B+"


def test_health_profile_unique_per_user(app, db, user):
    with app.app_context():
        db.session.add(HealthProfile(user_id=user.id, blood_group="A+"))
        db.session.commit()
        db.session.add(HealthProfile(user_id=user.id, blood_group="O-"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_deleting_user_cascades_all_records(app, db):
    with app.app_context():
        u = make_user(email="cascade@example.com")
        add_vaccination(u.id, name="Gone")
        db.session.add(Allergy(user_id=u.id, allergen="Gone", severity="Mild"))
        db.session.add(EmergencyContact(user_id=u.id, name="Gone", relationship="Gone",
                                        phone_number="555-0000"))
        db.session.add(HealthProfile(user_id=u.id))
        db.session.commit()
        uid = u.id
        db.session.delete(u)
        db.session.commit()

        assert db.session.execute(db.select(Vaccination).where(Vaccination.user_id == uid)).scalars().all() == []
        assert db.session.execute(db.select(Allergy).where(Allergy.user_id == uid)).scalars().all() == []
        assert db.session.execute(db.select(EmergencyContact).where(EmergencyContact.user_id == uid)).scalars().all() == []
        assert db.session.execute(db.select(HealthProfile).where(HealthProfile.user_id == uid)).scalars().all() == []


def test_repr_does_not_leak_personal_data(app, db, user):
    with app.app_context():
        rec = add_vaccination(user.id, name="PrivateVax")
        assert "PrivateVax" not in repr(rec)
        assert user.email not in repr(user)
        assert user.name not in repr(user)


def test_profile_age_calculation(app, db, user):
    with app.app_context():
        prof = HealthProfile(user_id=user.id, date_of_birth=date(2000, 1, 1))
        db.session.add(prof)
        db.session.commit()
        assert prof.age is not None and prof.age >= 25
        empty = HealthProfile(user_id=None)
        # no dob -> None
        assert empty.age is None
