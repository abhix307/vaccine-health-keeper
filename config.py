"""Application configuration.

All sensitive/environment-specific values come from environment variables
(loaded from a local .env file when present). Nothing secret is hardcoded.
"""
import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


def _database_uri() -> str:
    uri = os.environ.get("DATABASE_URL")
    if not uri:
        instance_dir = os.path.join(basedir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        uri = "sqlite:///" + os.path.join(instance_dir, "app.db")
    # Heroku-style postgres URLs are not understood by SQLAlchemy directly.
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return uri


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session / cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Must be True behind HTTPS in production (set via env var).
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # UI
    ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", "8"))
    REMINDER_WINDOW_DAYS = int(os.environ.get("REMINDER_WINDOW_DAYS", "60"))


class DevelopmentConfig(Config):
    DEBUG = True

    def __init__(self):
        super().__init__()
        if not self.SECRET_KEY:
            # Local-development fallback: persist a generated key inside
            # instance/ (gitignored) so multiple workers/processes share the
            # same key. Production REQUIRES SECRET_KEY in the environment.
            key_file = os.path.join(basedir, "instance", "secret_key.dev")
            if os.path.exists(key_file):
                with open(key_file, "r", encoding="utf-8") as fh:
                    self.SECRET_KEY = fh.read().strip()
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_hex(32)
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                with open(key_file, "w", encoding="utf-8") as fh:
                    fh.write(self.SECRET_KEY)
                os.chmod(key_file, 0o600)


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "testing-only-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # in-memory, isolated per test run
    WTF_CSRF_ENABLED = False  # toggled on in the dedicated CSRF tests
    SESSION_COOKIE_SECURE = False
    ITEMS_PER_PAGE = 8


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

    def __init__(self):
        super().__init__()
        if not self.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production."
            )
        # Fail safe: force secure cookies unless explicitly disabled
        # (e.g. when running plain HTTP behind a local proxy during setup).
        if os.environ.get("SESSION_COOKIE_SECURE") is None:
            self.SESSION_COOKIE_SECURE = True
            self.REMEMBER_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development").lower()
    if env not in config_by_name:
        env = "development"
    return config_by_name[env]()
