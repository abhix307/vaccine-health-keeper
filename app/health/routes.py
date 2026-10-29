"""Health profile, allergies, and emergency contacts.

All queries and mutations are strictly scoped to ``current_user.id``;
records are fetched through ``get_owned_or_404`` so cross-user access
returns a safe 404.
"""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db
from ..forms import AllergyForm, EmergencyContactForm, HealthProfileForm
from ..helpers import get_owned_or_404
from ..models import Allergy, EmergencyContact, HealthProfile

health_bp = Blueprint("health", __name__)


# --- Health profile --------------------------------------------------------

@health_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile = db.session.execute(
        select(HealthProfile).where(HealthProfile.user_id == current_user.id)
    ).scalar_one_or_none()

    form = HealthProfileForm(obj=profile)
    if form.validate_on_submit():
        if profile is None:
            profile = HealthProfile(user_id=current_user.id)
            db.session.add(profile)
        profile.date_of_birth = form.date_of_birth.data or None
        profile.blood_group = form.blood_group.data or None
        profile.health_notes = (form.health_notes.data or "").strip() or None
        db.session.commit()
        flash("Health profile saved.", "success")
        return redirect(url_for("health.profile"))
    return render_template("health/profile.html", form=form, profile=profile)


# --- Allergies ---------------------------------------------------------------

@health_bp.route("/allergies")
@login_required
def allergies():
    items = db.session.execute(
        select(Allergy).where(Allergy.user_id == current_user.id)
        .order_by(Allergy.created_at.desc(), Allergy.id.desc())
    ).scalars().all()
    return render_template("health/allergies.html", allergies=items)


@health_bp.route("/allergies/new", methods=["GET", "POST"])
@login_required
def allergy_new():
    form = AllergyForm()
    if form.validate_on_submit():
        item = Allergy(
            user_id=current_user.id,
            allergen=form.allergen.data.strip(),
            severity=form.severity.data,
            notes=(form.notes.data or "").strip() or None,
        )
        db.session.add(item)
        db.session.commit()
        flash(f"Allergy '{item.allergen}' added.", "success")
        return redirect(url_for("health.allergies"))
    return render_template("health/allergy_form.html", form=form, mode="new")


@health_bp.route("/allergies/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def allergy_edit(item_id):
    item = get_owned_or_404(Allergy, item_id)
    form = AllergyForm(obj=item)
    if form.validate_on_submit():
        item.allergen = form.allergen.data.strip()
        item.severity = form.severity.data
        item.notes = (form.notes.data or "").strip() or None
        db.session.commit()
        flash("Allergy updated.", "success")
        return redirect(url_for("health.allergies"))
    return render_template("health/allergy_form.html", form=form, mode="edit", item=item)


@health_bp.route("/allergies/<int:item_id>/delete", methods=["POST"])
@login_required
def allergy_delete(item_id):
    item = get_owned_or_404(Allergy, item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Allergy deleted.", "info")
    return redirect(url_for("health.allergies"))


# --- Emergency contacts ------------------------------------------------------

@health_bp.route("/contacts")
@login_required
def contacts():
    items = db.session.execute(
        select(EmergencyContact).where(EmergencyContact.user_id == current_user.id)
        .order_by(EmergencyContact.created_at.desc(), EmergencyContact.id.desc())
    ).scalars().all()
    return render_template("health/contacts.html", contacts=items)


@health_bp.route("/contacts/new", methods=["GET", "POST"])
@login_required
def contact_new():
    form = EmergencyContactForm()
    if form.validate_on_submit():
        item = EmergencyContact(
            user_id=current_user.id,
            name=form.name.data.strip(),
            relationship=form.relationship.data.strip(),
            phone_number=form.phone_number.data.strip(),
        )
        db.session.add(item)
        db.session.commit()
        flash(f"Emergency contact '{item.name}' added.", "success")
        return redirect(url_for("health.contacts"))
    return render_template("health/contact_form.html", form=form, mode="new")


@health_bp.route("/contacts/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def contact_edit(item_id):
    item = get_owned_or_404(EmergencyContact, item_id)
    form = EmergencyContactForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data.strip()
        item.relationship = form.relationship.data.strip()
        item.phone_number = form.phone_number.data.strip()
        db.session.commit()
        flash("Emergency contact updated.", "success")
        return redirect(url_for("health.contacts"))
    return render_template("health/contact_form.html", form=form, mode="edit", item=item)


@health_bp.route("/contacts/<int:item_id>/delete", methods=["POST"])
@login_required
def contact_delete(item_id):
    item = get_owned_or_404(EmergencyContact, item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Emergency contact deleted.", "info")
    return redirect(url_for("health.contacts"))
