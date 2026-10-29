"""Vaccination status and reminder logic.

Rules (per record; each record is ONE administered dose):

* ``administered``  - no next dose is scheduled for this record, OR the next
                      dose in the series has already been recorded (a record
                      exists for the same vaccine with dose_number + 1).
* ``upcoming``      - next_dose_date is in the future and that dose has not
                      been recorded yet.
* ``due_today``     - next_dose_date equals the reference date.
* ``overdue``       - next_dose_date is before the reference date and the
                      dose has not been recorded.

The reference date is injectable so tests are deterministic.
We never assume a series schedule and never auto-fill next-dose dates;
only dates entered by the user (per their clinician's instructions) count.
"""
from datetime import date
from typing import Iterable, Optional

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import aliased

from .extensions import db
from .models import Vaccination

STATUS_ADMINISTERED = "administered"
STATUS_UPCOMING = "upcoming"
STATUS_DUE_TODAY = "due_today"
STATUS_OVERDUE = "overdue"

STATUS_LABELS = {
    STATUS_ADMINISTERED: "Administered",
    STATUS_UPCOMING: "Upcoming",
    STATUS_DUE_TODAY: "Due today",
    STATUS_OVERDUE: "Overdue",
}

STATUS_BADGES = {
    STATUS_ADMINISTERED: "bg-success-subtle text-success-emphasis border border-success-subtle",
    STATUS_UPCOMING: "bg-info-subtle text-info-emphasis border border-info-subtle",
    STATUS_DUE_TODAY: "bg-primary-subtle text-primary-emphasis border border-primary-subtle",
    STATUS_OVERDUE: "bg-danger-subtle text-danger-emphasis border border-danger-subtle",
}


def _next_dose_recorded_subquery(vacc: Vaccination):
    """EXISTS clause: has the following dose of the same vaccine been given?"""
    next_rec = aliased(Vaccination)
    return exists(
        select(next_rec.id).where(
            and_(
                next_rec.user_id == vacc.user_id,
                func.lower(next_rec.vaccine_name) == func.lower(vacc.vaccine_name),
                next_rec.dose_number == vacc.dose_number + 1,
            )
        )
    )


def status_for(vacc: Vaccination, today: Optional[date] = None) -> str:
    today = today or date.today()
    if vacc.next_dose_date is None:
        return STATUS_ADMINISTERED
    # Has the next dose already been recorded?
    recorded = db.session.execute(
        select(func.count()).where(
            and_(
                Vaccination.user_id == vacc.user_id,
                func.lower(Vaccination.vaccine_name) == func.lower(vacc.vaccine_name),
                Vaccination.dose_number == vacc.dose_number + 1,
            )
        )
    ).scalar()
    if recorded:
        return STATUS_ADMINISTERED
    if vacc.next_dose_date > today:
        return STATUS_UPCOMING
    if vacc.next_dose_date == today:
        return STATUS_DUE_TODAY
    return STATUS_OVERDUE


def statuses_for(
    vaccinations: Iterable[Vaccination], today: Optional[date] = None
) -> dict:
    """Batch-compute statuses to avoid N+1 queries."""
    today = today or date.today()
    result = {}
    vacc_list = list(vaccinations)
    user_id = vacc_list[0].user_id if vacc_list else None
    next_recorded = _recorded_next_doses(user_id) if user_id else set()
    for v in vacc_list:
        if v.next_dose_date is None:
            result[v.id] = STATUS_ADMINISTERED
        elif (v.vaccine_name.strip().lower(), v.dose_number + 1) in next_recorded:
            result[v.id] = STATUS_ADMINISTERED
        elif v.next_dose_date > today:
            result[v.id] = STATUS_UPCOMING
        elif v.next_dose_date == today:
            result[v.id] = STATUS_DUE_TODAY
        else:
            result[v.id] = STATUS_OVERDUE
    return result


def _recorded_next_doses(user_id: int) -> set:
    """Set of (lowercased vaccine name, dose number) recorded for ONE user."""
    rows = db.session.execute(
        select(
            func.lower(func.trim(Vaccination.vaccine_name)),
            Vaccination.dose_number,
        ).where(Vaccination.user_id == user_id)
    ).all()
    return {(name, dose) for name, dose in rows}


def _status_sql_condition(status: str, today: date, user_id: int):
    """SQL predicate for filtering by computed status."""
    v = Vaccination
    next_rec = aliased(Vaccination)
    followup_exists = exists(
        select(next_rec.id).where(
            and_(
                next_rec.user_id == v.user_id,
                func.lower(next_rec.vaccine_name) == func.lower(v.vaccine_name),
                next_rec.dose_number == v.dose_number + 1,
            )
        )
    )
    if status == STATUS_ADMINISTERED:
        return db.or_(v.next_dose_date.is_(None), followup_exists)
    not_recorded = ~followup_exists
    if status == STATUS_UPCOMING:
        return db.and_(v.next_dose_date.is_not(None), v.next_dose_date > today, not_recorded)
    if status == STATUS_DUE_TODAY:
        return db.and_(v.next_dose_date == today, not_recorded)
    if status == STATUS_OVERDUE:
        return db.and_(v.next_dose_date.is_not(None), v.next_dose_date < today, not_recorded)
    raise ValueError(f"unknown status: {status}")


def dashboard_stats(user_id: int, today: Optional[date] = None) -> dict:
    today = today or date.today()
    base = select(func.count()).select_from(Vaccination).where(Vaccination.user_id == user_id)

    def count_for(status: str) -> int:
        if status == STATUS_ADMINISTERED:
            # Total administered doses = every recorded dose.
            return db.session.execute(base).scalar() or 0
        cond = _status_sql_condition(status, today, user_id)
        return db.session.execute(base.where(cond)).scalar() or 0

    return {
        "total": count_for(STATUS_ADMINISTERED),
        "upcoming": count_for(STATUS_UPCOMING),
        "due_today": count_for(STATUS_DUE_TODAY),
        "overdue": count_for(STATUS_OVERDUE),
    }


def reminders(user_id: int, today: Optional[date] = None, limit: int = 10) -> list:
    """Upcoming / due-today / overdue reminders, soonest first."""
    today = today or date.today()
    conds = [
        _status_sql_condition(s, today, user_id)
        for s in (STATUS_OVERDUE, STATUS_DUE_TODAY, STATUS_UPCOMING)
    ]
    rows = (
        db.session.execute(
            select(Vaccination)
            .where(Vaccination.user_id == user_id, db.or_(*conds))
            .order_by(Vaccination.next_dose_date.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    result = []
    for v in rows:
        result.append((v, status_for(v, today)))
    # Sort: overdue first, then due today, then upcoming by date.
    order = {STATUS_OVERDUE: 0, STATUS_DUE_TODAY: 1, STATUS_UPCOMING: 2}
    result.sort(key=lambda item: (order[item[1]], item[0].next_dose_date))
    return result


def recent_history(user_id: int, limit: int = 5) -> list:
    return (
        db.session.execute(
            select(Vaccination)
            .where(Vaccination.user_id == user_id)
            .order_by(Vaccination.vaccination_date.desc(), Vaccination.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
