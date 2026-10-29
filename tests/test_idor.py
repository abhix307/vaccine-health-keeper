"""IDOR / cross-user authorization tests.

For EVERY resource and EVERY mutating operation, an authenticated user
must never be able to read, modify, or delete another user's records.
Safe response: 404 (does not leak existence).
"""
import pytest

from tests.conftest import add_vaccination, make_user


@pytest.fixture()
def victim_records(app, other_user):
    """Records owned by 'other_user' — the attack target."""
    from app.extensions import db
    from app.models import Allergy, EmergencyContact, HealthProfile
    vacc = add_vaccination(other_user.id, name="VictimVax")
    allergy = Allergy(user_id=other_user.id, allergen="VictimAllergen", severity="Mild")
    contact = EmergencyContact(user_id=other_user.id, name="VictimContact",
                               relationship="Nobody", phone_number="+1 555 000 1111")
    profile = HealthProfile(user_id=other_user.id, blood_group="A+",
                            health_notes="private victim notes")
    db.session.add_all([allergy, contact, profile])
    db.session.commit()
    return {"vacc": vacc.id, "allergy": allergy.id, "contact": contact.id,
            "profile": profile.id}


def test_cannot_view_other_users_vaccination(client, logged_in, victim_records):
    resp = client.get(f"/vaccinations/{victim_records['vacc']}")
    assert resp.status_code == 404
    assert "VictimVax" not in resp.get_data(as_text=True)


def test_cannot_edit_other_users_vaccination(client, logged_in, victim_records, app, db):
    resp = client.get(f"/vaccinations/{victim_records['vacc']}/edit")
    assert resp.status_code == 404
    resp = client.post(f"/vaccinations/{victim_records['vacc']}/edit",
                       data={"vaccine_name": "Hijacked", "dose_number": "9",
                             "vaccination_date": "2024-01-01", "next_dose_date": "", "notes": ""})
    assert resp.status_code == 404
    from app.models import Vaccination
    with app.app_context():
        rec = db.session.get(Vaccination, victim_records["vacc"])
        assert rec.vaccine_name == "VictimVax"  # unchanged


def test_cannot_delete_other_users_vaccination(client, logged_in, victim_records, app, db):
    resp = client.post(f"/vaccinations/{victim_records['vacc']}/delete")
    assert resp.status_code == 404
    from app.models import Vaccination
    with app.app_context():
        assert db.session.get(Vaccination, victim_records["vacc"]) is not None


def test_cannot_edit_other_users_allergy(client, logged_in, victim_records):
    assert client.get(f"/health/allergies/{victim_records['allergy']}/edit").status_code == 404
    resp = client.post(f"/health/allergies/{victim_records['allergy']}/edit",
                       data={"allergen": "Hacked", "severity": "Mild"})
    assert resp.status_code == 404


def test_cannot_delete_other_users_allergy(client, logged_in, victim_records, app, db):
    resp = client.post(f"/health/allergies/{victim_records['allergy']}/delete")
    assert resp.status_code == 404
    from app.models import Allergy
    with app.app_context():
        assert db.session.get(Allergy, victim_records["allergy"]) is not None


def test_cannot_edit_other_users_contact(client, logged_in, victim_records):
    assert client.get(f"/health/contacts/{victim_records['contact']}/edit").status_code == 404
    resp = client.post(f"/health/contacts/{victim_records['contact']}/edit",
                       data={"name": "Hacked", "relationship": "X", "phone_number": "555-0000"})
    assert resp.status_code == 404


def test_cannot_delete_other_users_contact(client, logged_in, victim_records, app, db):
    resp = client.post(f"/health/contacts/{victim_records['contact']}/delete")
    assert resp.status_code == 404
    from app.models import EmergencyContact
    with app.app_context():
        assert db.session.get(EmergencyContact, victim_records["contact"]) is not None


def test_other_users_data_never_leaks_into_views(client, logged_in, victim_records):
    for url in ("/dashboard/", "/vaccinations/", "/vaccinations/report",
                "/health/allergies", "/health/contacts", "/health/profile"):
        html = client.get(url).get_data(as_text=True)
        assert "VictimVax" not in html, url
        assert "VictimAllergen" not in html, url
        assert "VictimContact" not in html, url
        assert "private victim notes" not in html, url


def test_dashboard_stats_only_count_own_records(client, app, db):
    attacker = make_user(email="attacker@example.com")
    victim = make_user(email="victim2@example.com")
    with app.app_context():
        add_vaccination(victim.id, name="VictimOnly1")
        add_vaccination(victim.id, name="VictimOnly2")
    client.post("/login", data={"email": attacker.email, "password": "Str0ngPass!123"})
    html = client.get("/dashboard/").get_data(as_text=True)
    # Attacker sees zero administered doses, not the victim's two
    assert "VictimOnly" not in html
    assert '<div class="stat-value">0</div>' in html


def test_malformed_ids_are_safe_404(client, logged_in):
    # Non-integer / negative / huge ids
    for bad in ("abc", "-1", "99999999999999999999"):
        resp = client.get(f"/vaccinations/{bad}")
        assert resp.status_code in (404,), f"vaccinations/{bad}"
    # (Flask routing itself 404s non-int ids before our handler)
    resp = client.post("/health/allergies/0/delete")
    assert resp.status_code == 404
