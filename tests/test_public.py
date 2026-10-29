"""Landing page, health check, and error pages."""


def test_landing_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Vaccination records" in html or "vaccination" in html.lower()
    assert "Create free account" in html
    assert "Sign in" in html


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_unknown_page_renders_404(client):
    resp = client.get("/this-page-does-not-exist")
    assert resp.status_code == 404
    assert "Page not found" in resp.get_data(as_text=True)


def test_private_pages_redirect_anonymous_to_login(client):
    for path in ("/dashboard/", "/vaccinations/", "/health/profile",
                 "/health/allergies", "/health/contacts", "/vaccinations/report",
                 "/dashboard/settings", "/vaccinations/new"):
        resp = client.get(path)
        assert resp.status_code == 302, f"{path} should redirect"
        assert "/login" in resp.headers["Location"], f"{path} should redirect to login"
