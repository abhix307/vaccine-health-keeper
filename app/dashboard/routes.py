"""Dashboard and account settings."""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, logout_user

from ..extensions import db
from ..forms import DeleteAccountForm
from ..models import Allergy, EmergencyContact, HealthProfile, User
from ..services import dashboard_stats, recent_history, reminders

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    stats = dashboard_stats(current_user.id)
    upcoming = reminders(current_user.id, limit=8)
    recent = recent_history(current_user.id, limit=5)
    allergy_count = db.session.execute(
        db.select(db.func.count()).select_from(Allergy).where(Allergy.user_id == current_user.id)
    ).scalar() or 0
    contact_count = db.session.execute(
        db.select(db.func.count()).select_from(EmergencyContact).where(EmergencyContact.user_id == current_user.id)
    ).scalar() or 0
    return render_template(
        "dashboard/index.html",
        stats=stats,
        upcoming=upcoming,
        recent=recent,
        allergy_count=allergy_count,
        contact_count=contact_count,
    )


@dashboard_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.password.data):
            flash("Incorrect password. Account not deleted.", "danger")
            return render_template("dashboard/settings.html", form=form)
        user_id = current_user.id
        logout_user()
        user = db.session.get(User, user_id)
        db.session.delete(user)  # cascades to all owned records
        db.session.commit()
        flash("Your account and all associated records were permanently deleted.", "info")
        return redirect(url_for("index"))
    return render_template("dashboard/settings.html", form=form)
