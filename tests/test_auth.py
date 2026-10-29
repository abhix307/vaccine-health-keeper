"""Registration, login, logout, password hashing, and redirect safety."""
from app.models import User
from tests.conftest import csrf_token_from


def register(client, **overrides):
    data = {
        "name": "New Person",
        "email": "new@example.com",
        "password": "Sup3rSecret!x",
        "confirm_password": "Sup3rSecret!x",
    }
    data.update(overrides)
    return client.post("/register", data=data, follow_redirects=False)


def test_register_success_creates_user_and_redirects(client, app, db):
    resp = register(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard/")
    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        assert user.email == "new@example.com"


def test_register_stores_hashed_password_not_plaintext(client, app, db):
    register(client, password="MyPlainPass99!", confirm_password="MyPlainPass99!")
    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        assert "MyPlainPass99!" not in (user.password_hash or "")
        assert user.password_hash.startswith(("pbkdf2:", "scrypt:", "argon2"))
        assert user.check_password("MyPlainPass99!")
        assert not user.check_password("wrong-password")


def test_register_duplicate_email_rejected(client, app, db, user):
    resp = register(client, email=user.email.upper())  # case-insensitive dup
    assert resp.status_code == 200  # re-rendered form with errors
    assert "already exists" in resp.get_data(as_text=True)


def test_register_validation_errors(client):
    # Missing fields
    resp = client.post("/register", data={}, follow_redirects=False)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "This field is required" in html

    # Mismatched confirmation
    resp = register(client, confirm_password="Different123!")
    assert "Passwords do not match" in resp.get_data(as_text=True)

    # Short password
    resp = register(client, password="short", confirm_password="short")
    assert "at least 8 characters" in resp.get_data(as_text=True)

    # Invalid email
    resp = register(client, email="not-an-email")
    assert "Invalid email address" in resp.get_data(as_text=True)


def test_login_success(client, user):
    resp = client.post("/login", data={"email": user.email, "password": "Str0ngPass!123"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard/")
    me = client.get("/dashboard/")
    assert me.status_code == 200


def test_login_wrong_password_returns_401_generic_error(client, user):
    resp = client.post("/login", data={"email": user.email, "password": "wrong"})
    assert resp.status_code == 401
    body = resp.get_data(as_text=True)
    assert "Invalid email or password" in body
    # Must not reveal whether the account exists
    assert "does not exist" not in body.lower()


def test_login_unknown_email_same_generic_error(client):
    resp = client.post("/login", data={"email": "ghost@example.com", "password": "whatever1"})
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.get_data(as_text=True)


def test_logout_requires_post_and_logs_out(client, logged_in):
    # GET logout not allowed
    resp = client.get("/logout")
    assert resp.status_code == 405
    resp = client.post("/logout")
    assert resp.status_code == 302
    # Now private pages redirect again
    assert client.get("/dashboard/").status_code == 302


def test_login_next_redirect_is_safe(client, user):
    # Open-redirect attempts must fall back to the dashboard
    evil = "/login?next=https://evil.example.com/phish"
    resp = client.post(evil, data={"email": user.email, "password": "Str0ngPass!123"})
    assert resp.headers["Location"].endswith("/dashboard/")
    client.post("/logout")

    evil2 = "/login?next=//evil.example.com"
    resp = client.post(evil2, data={"email": user.email, "password": "Str0ngPass!123"})
    assert resp.headers["Location"].endswith("/dashboard/")
    client.post("/logout")

    evil3 = "/login?next=/\\evil.example.com"
    resp = client.post(evil3, data={"email": user.email, "password": "Str0ngPass!123"})
    assert resp.headers["Location"].endswith("/dashboard/")
    client.post("/logout")

    # Legit relative redirect is honoured
    resp = client.post("/login?next=/health/allergies",
                       data={"email": user.email, "password": "Str0ngPass!123"})
    assert resp.headers["Location"].endswith("/health/allergies")


def test_registration_page_contains_csrf_field(csrf_enabled_client):
    html = csrf_enabled_client.get("/register").get_data(as_text=True)
    assert csrf_token_from(html)  # would raise if missing
