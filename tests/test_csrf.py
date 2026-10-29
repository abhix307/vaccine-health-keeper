"""CSRF protection tests (run with CSRF explicitly ENABLED)."""
import pytest

from app import create_app
from app.extensions import db as _db
from config import TestingConfig
from tests.conftest import add_vaccination, csrf_token_from, make_user


class CsrfConfig(TestingConfig):
    WTF_CSRF_ENABLED = True


@pytest.fixture()
def csrf_app():
    app = create_app(CsrfConfig())
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def csrf_client(csrf_app):
    return csrf_app.test_client()


def _login_with_csrf(client):
    user = make_user(email="csrf@example.com")
    html = client.get("/login").get_data(as_text=True)
    token = csrf_token_from(html)
    resp = client.post("/login", data={"email": user.email, "password": "Str0ngPass!123",
                                       "csrf_token": token})
    assert resp.status_code == 302
    return user


def test_post_without_csrf_token_is_rejected(csrf_client, csrf_app):
    _login_with_csrf(csrf_client)
    resp = csrf_client.post("/vaccinations/new", data={
        "vaccine_name": "NoToken", "dose_number": "1",
        "vaccination_date": "2026-01-01", "next_dose_date": "", "notes": "",
    })
    assert resp.status_code == 400
    with csrf_app.app_context():
        from app.models import Vaccination
        assert _db.session.execute(_db.select(Vaccination)).scalar_one_or_none() is None


def test_post_with_wrong_csrf_token_is_rejected(csrf_client):
    _login_with_csrf(csrf_client)
    resp = csrf_client.post("/health/allergies/new", data={
        "allergen": "Evil", "severity": "Mild", "notes": "",
        "csrf_token": "totally-wrong-token",
    })
    assert resp.status_code == 400


def test_post_with_valid_csrf_token_succeeds(csrf_client, csrf_app):
    user = _login_with_csrf(csrf_client)
    html = csrf_client.get("/health/allergies/new").get_data(as_text=True)
    token = csrf_token_from(html)
    resp = csrf_client.post("/health/allergies/new", data={
        "allergen": "Latex", "severity": "Mild", "notes": "", "csrf_token": token,
    })
    assert resp.status_code == 302
    with csrf_app.app_context():
        from app.models import Allergy
        assert _db.session.execute(_db.select(Allergy)).scalar_one() is not None


def test_logout_without_csrf_token_is_rejected(csrf_client):
    _login_with_csrf(csrf_client)
    resp = csrf_client.post("/logout", data={})
    assert resp.status_code == 400
    # still logged in
    assert csrf_client.get("/dashboard/").status_code == 200


def test_delete_without_csrf_token_does_not_delete(csrf_client, csrf_app):
    user = _login_with_csrf(csrf_client)
    with csrf_app.app_context():
        rec = add_vaccination(user.id, name="Protected")
        rid = rec.id
    resp = csrf_client.post(f"/vaccinations/{rid}/delete", data={})
    assert resp.status_code == 400
    with csrf_app.app_context():
        from app.models import Vaccination
        assert _db.session.get(Vaccination, rid) is not None
