"""Shared view helpers: ownership enforcement and safe redirects."""
from flask import abort, request, url_for
from flask_login import current_user

from .extensions import db


def get_owned_or_404(model, record_id):
    """Fetch a record by id, enforcing ownership by the current user.

    Returns a safe 404 for: malformed ids, missing records, AND records
    belonging to another user (so attackers cannot distinguish between
    'does not exist' and 'is not yours').
    """
    try:
        record_id = int(record_id)
    except (TypeError, ValueError):
        abort(404)
    if record_id <= 0 or record_id > 2**63 - 1:
        # Out-of-range ids would crash some drivers (e.g. SQLite OverflowError)
        abort(404)
    record = db.session.get(model, record_id)
    if record is None or record.user_id != current_user.id:
        abort(404)
    return record


def safe_redirect_target(default_endpoint="dashboard.index"):
    """Only allow relative same-site redirects (block open-redirect via next=)."""
    target = request.args.get("next") or ""
    if target.startswith("/") and not target.startswith("//") and "\\" not in target.split("?")[0]:
        # url_for to make sure it resolves to a known path prefix
        return target
    return url_for(default_endpoint)
