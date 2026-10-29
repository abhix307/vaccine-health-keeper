"""Configuration regression tests."""
import pytest


def test_production_config_requires_secret_key(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg.Config, "SECRET_KEY", None)
    with pytest.raises(RuntimeError):
        cfg.ProductionConfig()


def test_dev_fallback_secret_key_is_stable_across_processes(monkeypatch):
    """Two processes (e.g. two gunicorn workers) must derive the SAME
    dev fallback key, otherwise CSRF tokens/sessions break across workers."""
    import config as cfg
    monkeypatch.setattr(cfg.Config, "SECRET_KEY", None)
    a = cfg.DevelopmentConfig()
    b = cfg.DevelopmentConfig()
    assert a.SECRET_KEY
    assert a.SECRET_KEY == b.SECRET_KEY
    assert len(bytes.fromhex(a.SECRET_KEY)) >= 32


def test_postgres_url_scheme_is_normalized(monkeypatch):
    import config as cfg
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:5432/db")
    assert cfg._database_uri() == "postgresql://u:p@host:5432/db"


def test_samesite_none_forces_secure_cookies(monkeypatch):
    """SameSite=None is only valid (and only safe) together with Secure."""
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "None")
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    import importlib
    import config as cfg
    importlib.reload(cfg)
    try:
        assert cfg.Config.SESSION_COOKIE_SAMESITE == "None"
        assert cfg.Config.SESSION_COOKIE_SECURE is True
        assert cfg.Config.REMEMBER_COOKIE_SECURE is True
    finally:
        monkeypatch.delenv("SESSION_COOKIE_SAMESITE", raising=False)
        importlib.reload(cfg)


def test_samesite_defaults_to_lax():
    import config as cfg
    assert cfg.Config.SESSION_COOKIE_SAMESITE == "Lax"


def test_production_forces_secure_cookies_by_default(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg.Config, "SECRET_KEY", "x" * 64)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    prod = cfg.ProductionConfig()
    assert prod.SECRET_KEY == "x" * 64
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.DEBUG is False
