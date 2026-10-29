"""Shared pytest fixtures.

Uses an isolated in-memory SQLite database and purely synthetic data.
No real patient information appears anywhere in the test suite.
"""
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.models import (Allergy, EmergencyContact, HealthProfile, User,  # noqa: E402
                        Vaccination)
from config import TestingConfig  # noqa: E402


@pytest.fixture()
def app():
    app = create_app(TestingConfig())
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


class CsrfEnabledConfig(TestingConfig):
    WTF_CSRF_ENABLED = True


@pytest.fixture()
def csrf_enabled_client():
    """Client for an app variant with CSRF protection ENABLED."""
    app = create_app(CsrfEnabledConfig())
    with app.app_context():
        _db.create_all()
        yield app.test_client()
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


def make_user(email="user@example.com", password="Str0ngPass!123", name="Test User"):
    user = User(name=name, email=email)
    user.set_password(password)
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def user(app):
    return make_user()


@pytest.fixture()
def other_user(app):
    return make_user(email="other@example.com", name="Other User")


@pytest.fixture()
def logged_in(client, user):
    """Log in the primary user; returns the user."""
    resp = client.post("/login", data={"email": user.email, "password": "Str0ngPass!123"})
    assert resp.status_code in (200, 302), "login should succeed"
    return user


def add_vaccination(user_id, name="TestVax", dose=1, vdate=None, ndate=None, notes=None):
    v = Vaccination(
        user_id=user_id, vaccine_name=name, dose_number=dose,
        vaccination_date=vdate or (date.today() - timedelta(days=30)),
        next_dose_date=ndate, notes=notes,
    )
    _db.session.add(v)
    _db.session.commit()
    return v


def csrf_token_from(html: str) -> str:
    """Extract the csrf_token hidden input value from a rendered page."""
    marker = 'name="csrf_token"'
    idx = html.find(marker)
    assert idx != -1, "csrf_token field not found in page"
    start = html.find('value="', idx) + len('value="')
    end = html.find('"', start)
    return html[start:end]
