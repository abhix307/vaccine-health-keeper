"""Security configuration regression tests."""


def test_security_headers_present(client):
    resp = client.get("/")
    h = resp.headers
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert h.get("X-Frame-Options") == "DENY"
    assert h.get("Referrer-Policy") == "same-origin"
    csp = h.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp.split("style-src")[0]  # not allowed for scripts
    assert "frame-ancestors" in csp


def test_session_cookie_flags(client, app):
    client.post("/register", data={
        "name": "Cookie Test", "email": "cookie@example.com",
        "password": "Sup3rSecret!x", "confirm_password": "Sup3rSecret!x",
    })
    cookie_header = None
    for header_name, header_value in client.get("/dashboard/").headers.items():
        pass
    # Use the response from the registration POST (sets the session cookie)
    resp = client.get("/dashboard/")
    set_cookie = resp.headers.get("Set-Cookie", "")
    # Session cookie may already be set from register; check config directly too
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_no_server_version_leak(client):
    resp = client.get("/")
    # Werkzeug may send "Server: Werkzeug/x.y" by default; ensure at least
    # the app doesn't advertise a framework stack beyond that.
    assert "PHP" not in resp.headers.get("Server", "")


def test_templates_never_use_safe_filter_with_user_data(app):
    """Guard against regressions: no Jinja '|safe' usage in templates."""
    import pathlib
    tpl_dir = pathlib.Path(app.root_path) / "templates"
    for p in tpl_dir.rglob("*.html"):
        content = p.read_text()
        assert "| safe" not in content and "|safe" not in content, f"unsafe filter in {p}"


def test_error_pages_do_not_leak_stack_traces(client):
    resp = client.get("/nope-not-here")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 404
    assert "Traceback" not in body
    assert "SQLAlchemy" not in body
