"""Application factory for Vaccine & Health Record Keeper."""
import logging
import os
from datetime import date

from flask import Flask, render_template

from .extensions import csrf, db, login_manager, migrate


def create_app(config_override=None):
    app = Flask(__name__, instance_relative_config=False)

    if config_override is not None:
        app.config.from_object(config_override)
    else:
        from config import get_config  # imported lazily: lives at project root
        app.config.from_object(get_config())

    os.makedirs(app.instance_path, exist_ok=True)

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Blueprints
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .health.routes import health_bp
    from .vaccinations.routes import vaccinations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(vaccinations_bp, url_prefix="/vaccinations")
    app.register_blueprint(health_bp, url_prefix="/health")

    # Template helpers -----------------------------------------------------
    @app.template_filter("datefmt")
    def datefmt(value, fmt="%d %b %Y"):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        return value.strftime(fmt)

    @app.template_filter("initials")
    def initials(name):
        parts = [p for p in (name or "").split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or "U"

    @app.context_processor
    def inject_globals():
        return {"today": date.today()}

    # Error pages -----------------------------------------------------------
    def _error_page(code, title, message):
        def handler(e):
            return render_template("errors/error.html", code=code,
                                   title=title, message=message), code
        return handler

    app.register_error_handler(404, _error_page(404, "Page not found",
        "We couldn't find that page. It may have been moved, or it may not be yours to view."))
    app.register_error_handler(403, _error_page(403, "Forbidden",
        "You don't have permission to perform that action."))
    app.register_error_handler(400, _error_page(400, "Bad request",
        "The server could not understand that request."))
    app.register_error_handler(500, _error_page(500, "Something went wrong",
        "An unexpected error occurred. No personal data is shown here."))

    # Logging: keep Flask's request logging but never log request bodies,
    # query strings with personal data, or database contents.
    if not app.debug and not app.testing:
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers if gunicorn_logger.handlers else app.logger.handlers
        app.logger.setLevel(gunicorn_logger.level or logging.INFO)

    # Security headers (CSP allows no inline scripts; inline style attrs are
    # permitted because 'unsafe-inline' is required for style-src only).
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'",
        )
        return response

    # Health check for deployment platforms
    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(db.text("SELECT 1"))
            return {"status": "ok"}, 200
        except Exception:
            app.logger.error("health check failed")  # no details in logs
            return {"status": "error"}, 503

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
