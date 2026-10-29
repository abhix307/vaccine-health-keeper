"""Health profile, allergies, emergency contacts CRUD + validation."""
from datetime import date, timedelta

TODAY = date.today()


# ---------- Health profile ----------

def test_profile_get_when_absent(client, logged_in):
    resp = client.get("/health/profile")
    assert resp.status_code == 200
    assert "All fields are optional" in resp.get_data(as_text=True)


def test_profile_create_and_update(client, logged_in, app, db):
    data = {
        "date_of_birth": "1990-05-20",
        "blood_group": "O+",
        "health_notes": "Synthetic note",
    }
    resp = client.post("/health/profile", data=data)
    assert resp.status_code == 302
    from app.models import HealthProfile
    with app.app_context():
        prof = db.session.execute(db.select(HealthProfile)).scalar_one()
        assert prof.date_of_birth == date(1990, 5, 20)
        assert prof.blood_group == "O+"
        assert prof.health_notes == "Synthetic note"

    # Update, not duplicate
    data["blood_group"] = "AB-"
    data["health_notes"] = "Changed"
    client.post("/health/profile", data=data)
    with app.app_context():
        profiles = db.session.execute(db.select(HealthProfile)).scalars().all()
        assert len(profiles) == 1
        assert profiles[0].blood_group == "AB-"


def test_profile_allows_all_empty(client, logged_in):
    resp = client.post("/health/profile", data={"date_of_birth": "", "blood_group": "", "health_notes": ""})
    assert resp.status_code == 302


def test_profile_validates_dob_and_blood_group(client, logged_in):
    resp = client.post("/health/profile",
                       data={"date_of_birth": (TODAY + timedelta(days=1)).isoformat(),
                             "blood_group": "", "health_notes": ""})
    html = resp.get_data(as_text=True)
    assert "must be in the past" in html

    resp = client.post("/health/profile",
                       data={"date_of_birth": "", "blood_group": "ZZ+", "health_notes": ""})
    assert "valid blood group" in resp.get_data(as_text=True)


# ---------- Allergies ----------

def test_allergy_crud(client, logged_in, app, db):
    from app.models import Allergy

    # Empty state
    html = client.get("/health/allergies").get_data(as_text=True)
    assert "No allergies recorded" in html

    # Create
    resp = client.post("/health/allergies/new",
                       data={"allergen": "Penicillin", "severity": "Severe", "notes": "Rash"})
    assert resp.status_code == 302
    with app.app_context():
        item = db.session.execute(db.select(Allergy)).scalar_one()
        item_id = item.id
        assert item.severity == "Severe"

    # List shows it
    html = client.get("/health/allergies").get_data(as_text=True)
    assert "Penicillin" in html and "Severe" in html

    # Edit
    resp = client.post(f"/health/allergies/{item_id}/edit",
                       data={"allergen": "Amoxicillin", "severity": "Moderate", "notes": ""})
    assert resp.status_code == 302
    with app.app_context():
        item = db.session.get(Allergy, item_id)
        assert item.allergen == "Amoxicillin"
        assert item.severity == "Moderate"
        assert item.notes is None

    # Delete
    resp = client.post(f"/health/allergies/{item_id}/delete")
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Allergy, item_id) is None


def test_allergy_validation(client, logged_in):
    resp = client.post("/health/allergies/new",
                       data={"allergen": "", "severity": "Mild"})
    assert "This field is required" in resp.get_data(as_text=True)

    resp = client.post("/health/allergies/new",
                       data={"allergen": "Dust", "severity": "Catastrophic"})
    assert "valid severity" in resp.get_data(as_text=True)


# ---------- Emergency contacts ----------

def test_contact_crud(client, logged_in, app, db):
    from app.models import EmergencyContact

    html = client.get("/health/contacts").get_data(as_text=True)
    assert "No emergency contacts yet" in html

    resp = client.post("/health/contacts/new",
                       data={"name": "Jane Doe", "relationship": "Sister",
                             "phone_number": "+91 98765 43210"})
    assert resp.status_code == 302
    with app.app_context():
        item = db.session.execute(db.select(EmergencyContact)).scalar_one()
        item_id = item.id

    resp = client.post(f"/health/contacts/{item_id}/edit",
                       data={"name": "Jane Doe", "relationship": "Sibling",
                             "phone_number": "(555) 010-9999"})
    assert resp.status_code == 302
    with app.app_context():
        item = db.session.get(EmergencyContact, item_id)
        assert item.phone_number == "(555) 010-9999"

    resp = client.post(f"/health/contacts/{item_id}/delete")
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(EmergencyContact, item_id) is None


def test_contact_phone_validation_is_international_friendly(client, logged_in):
    good_numbers = ["+91 98765 43210", "555-0100", "(555) 010-9999", "+1 (555) 010-9999",
                    "044 20 7946 0958", "+49 30 123456"]
    for number in good_numbers:
        resp = client.post("/health/contacts/new",
                           data={"name": "Valid Person", "relationship": "Friend",
                                 "phone_number": number})
        assert resp.status_code == 302, f"should accept {number}"

    bad_numbers = ["abcd", "12", "+", "12345678901234567890123456789012345", "call me maybe"]
    for number in bad_numbers:
        resp = client.post("/health/contacts/new",
                           data={"name": "Bad Phone", "relationship": "Friend",
                                 "phone_number": number})
        assert resp.status_code == 200, f"should reject {number}"
        assert "valid phone number" in resp.get_data(as_text=True) or "at least 5 digits" in resp.get_data(as_text=True)


def test_contact_requires_all_fields(client, logged_in):
    resp = client.post("/health/contacts/new", data={})
    html = resp.get_data(as_text=True)
    assert html.count("This field is required") >= 3
