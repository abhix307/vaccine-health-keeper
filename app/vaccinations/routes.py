"""Vaccination CRUD, search/filter, and printable report."""
from datetime import date, datetime

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func, select

from ..extensions import db
from ..forms import VaccinationForm
from ..helpers import get_owned_or_404
from ..models import Vaccination
from ..services import (STATUS_LABELS, _status_sql_condition, statuses_for)

vaccinations_bp = Blueprint("vaccinations", __name__)


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return "invalid"


@vaccinations_bp.route("/")
@login_required
def index():
    today = date.today()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    date_from_raw = request.args.get("date_from", "").strip()
    date_to_raw = request.args.get("date_to", "").strip()

    filter_error = None
    stmt = select(Vaccination).where(Vaccination.user_id == current_user.id)

    if query:
        # Parameterised LIKE - no injection; escape wildcard characters.
        like = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        stmt = stmt.where(Vaccination.vaccine_name.ilike(like, escape="\\"))

    if status_filter:
        if status_filter not in STATUS_LABELS:
            filter_error = "Unknown status filter; it was ignored."
            status_filter = ""
        else:
            stmt = stmt.where(_status_sql_condition(status_filter, today, current_user.id))

    date_from = _parse_date(date_from_raw)
    date_to = _parse_date(date_to_raw)
    if date_from == "invalid" or date_to == "invalid":
        filter_error = "Dates must use the YYYY-MM-DD format; invalid values were ignored."
        date_from = date_from if date_from != "invalid" else None
        date_to = date_to if date_to != "invalid" else None
    if date_from and date_to and date_from > date_to:
        filter_error = "Start date is after end date; the range was ignored."
        date_from = date_to = None
    if date_from:
        stmt = stmt.where(Vaccination.vaccination_date >= date_from)
    if date_to:
        stmt = stmt.where(Vaccination.vaccination_date <= date_to)

    has_filters = bool(query or status_filter or date_from or date_to)

    total = db.session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar() or 0

    stmt = stmt.order_by(
        Vaccination.vaccination_date.desc(), Vaccination.id.desc()
    )
    vaccinations = db.session.execute(
        stmt.limit(current_app.config["ITEMS_PER_PAGE"]).offset((page - 1) * current_app.config["ITEMS_PER_PAGE"])
    ).scalars().all()

    statuses = statuses_for(vaccinations, today)

    per_page = current_app.config["ITEMS_PER_PAGE"]
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "vaccinations/list.html",
        vaccinations=vaccinations,
        statuses=statuses,
        page=page,
        total_pages=total_pages,
        total=total,
        query=query,
        status_filter=status_filter,
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
        has_filters=has_filters,
        filter_error=filter_error,
        status_labels=STATUS_LABELS,
    )


@vaccinations_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = VaccinationForm()
    if form.validate_on_submit():
        record = Vaccination(
            user_id=current_user.id,
            vaccine_name=form.vaccine_name.data.strip(),
            dose_number=int(form.dose_number.data),
            vaccination_date=form.vaccination_date.data,
            next_dose_date=form.next_dose_date.data or None,
            notes=(form.notes.data or "").strip() or None,
        )
        db.session.add(record)
        db.session.commit()
        flash(f"Vaccination record for {record.vaccine_name} (dose {record.dose_number}) added.", "success")
        return redirect(url_for("vaccinations.detail", record_id=record.id))
    return render_template("vaccinations/form.html", form=form, mode="new")


@vaccinations_bp.route("/<int:record_id>")
@login_required
def detail(record_id):
    record = get_owned_or_404(Vaccination, record_id)
    status = statuses_for([record])[record.id]
    return render_template("vaccinations/detail.html", record=record, status=status,
                           status_label=STATUS_LABELS[status])


@vaccinations_bp.route("/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit(record_id):
    record = get_owned_or_404(Vaccination, record_id)
    form = VaccinationForm(obj=record)
    if request.method == "GET":
        # SelectField coerces to str; render the stored int correctly.
        form.dose_number.data = str(record.dose_number)
    if form.validate_on_submit():
        record.vaccine_name = form.vaccine_name.data.strip()
        record.dose_number = int(form.dose_number.data)
        record.vaccination_date = form.vaccination_date.data
        record.next_dose_date = form.next_dose_date.data or None
        record.notes = (form.notes.data or "").strip() or None
        db.session.commit()
        flash("Vaccination record updated.", "success")
        return redirect(url_for("vaccinations.detail", record_id=record.id))
    return render_template("vaccinations/form.html", form=form, mode="edit", record=record)


@vaccinations_bp.route("/<int:record_id>/delete", methods=["POST"])
@login_required
def delete(record_id):
    record = get_owned_or_404(Vaccination, record_id)
    db.session.delete(record)
    db.session.commit()
    flash("Vaccination record deleted.", "info")
    return redirect(url_for("vaccinations.index"))


@vaccinations_bp.route("/report")
@login_required
def report():
    """Print-friendly full vaccination history for the current user only."""
    today = date.today()
    records = db.session.execute(
        select(Vaccination)
        .where(Vaccination.user_id == current_user.id)
        .order_by(Vaccination.vaccination_date.desc(), Vaccination.id.desc())
    ).scalars().all()
    statuses = statuses_for(records, today)
    return render_template("vaccinations/report.html", records=records,
                           statuses=statuses, status_labels=STATUS_LABELS,
                           printed_on=today)
