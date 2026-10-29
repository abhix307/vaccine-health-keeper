"""Status/reminder calculation, with an injected reference date.

Covers: yesterday/today/tomorrow boundaries, missing next-dose dates,
series continuation (a recorded next dose marks the previous reminder
as administered), and dashboard aggregation.
"""
from datetime import date

from tests.conftest import add_vaccination

REF = date(2026, 3, 15)  # deterministic "today" for these tests


def test_status_boundaries(app, db, user):
    from app.services import status_for
    with app.app_context():
        overdue = add_vaccination(user.id, name="A", vdate=date(2026, 1, 1),
                                  ndate=date(2026, 3, 14))   # yesterday
        due = add_vaccination(user.id, name="B", vdate=date(2026, 1, 1),
                              ndate=date(2026, 3, 15))       # exactly today
        upcoming = add_vaccination(user.id, name="C", vdate=date(2026, 1, 1),
                                   ndate=date(2026, 3, 16))  # tomorrow
        none_next = add_vaccination(user.id, name="D", vdate=date(2026, 1, 1),
                                    ndate=None)

        assert status_for(overdue, REF) == "overdue"
        assert status_for(due, REF) == "due_today"
        assert status_for(upcoming, REF) == "upcoming"
        assert status_for(none_next, REF) == "administered"


def test_recorded_next_dose_clears_overdue(app, db, user):
    """If dose 2 was actually administered, dose 1's past due-date is no
    longer overdue — the series moved on."""
    from app.services import status_for
    with app.app_context():
        dose1 = add_vaccination(user.id, name="MMR", dose=1, vdate=date(2025, 1, 1),
                                ndate=date(2026, 1, 1))  # long past
        add_vaccination(user.id, name="MMR", dose=2, vdate=date(2026, 1, 5), ndate=None)
        assert status_for(dose1, REF) == "administered"


def test_one_dose_does_not_complete_series(app, db, user):
    """A single administered dose with a future next-dose date is NOT
    'completed' — it is upcoming."""
    from app.services import status_for
    with app.app_context():
        dose1 = add_vaccination(user.id, name="HepB", dose=1, vdate=date(2026, 2, 1),
                                ndate=date(2026, 8, 1))
        assert status_for(dose1, REF) == "upcoming"


def test_name_matching_for_series_is_case_insensitive(app, db, user):
    from app.services import status_for
    with app.app_context():
        dose1 = add_vaccination(user.id, name="Td booster", dose=1, vdate=date(2025, 1, 1),
                                ndate=date(2026, 1, 1))
        add_vaccination(user.id, name="TD BOOSTER", dose=2, vdate=date(2026, 1, 5))
        assert status_for(dose1, REF) == "administered"


def test_statuses_for_batch_matches_single(app, db, user):
    from app.services import statuses_for
    with app.app_context():
        a = add_vaccination(user.id, name="A", vdate=date(2026, 1, 1), ndate=date(2026, 3, 14))
        b = add_vaccination(user.id, name="B", vdate=date(2026, 1, 1), ndate=None)
        result = statuses_for([a, b], REF)
        assert result == {a.id: "overdue", b.id: "administered"}


def test_statuses_for_is_user_scoped(app, db, user, other_user):
    """Batch status must not treat ANOTHER user's dose 2 as continuing
    this user's series."""
    from app.services import statuses_for
    with app.app_context():
        mine = add_vaccination(user.id, name="SameVax", dose=1, vdate=date(2025, 1, 1),
                               ndate=date(2026, 1, 1))
        add_vaccination(other_user.id, name="SameVax", dose=2, vdate=date(2026, 2, 1))
        result = statuses_for([mine], REF)
        assert result[mine.id] == "overdue"  # still overdue for THIS user


def test_dashboard_stats(app, db, user):
    from app.services import dashboard_stats
    with app.app_context():
        add_vaccination(user.id, name="OD", vdate=date(2026, 1, 1), ndate=date(2026, 3, 1))
        add_vaccination(user.id, name="DT", vdate=date(2026, 1, 1), ndate=REF)
        add_vaccination(user.id, name="UP", vdate=date(2026, 1, 1), ndate=date(2026, 4, 1))
        add_vaccination(user.id, name="Done", vdate=date(2026, 1, 1), ndate=None)
        stats = dashboard_stats(user.id, REF)
        assert stats == {"total": 4, "upcoming": 1, "due_today": 1, "overdue": 1}


def test_reminders_ordering_and_membership(app, db, user):
    from app.services import reminders
    with app.app_context():
        add_vaccination(user.id, name="UP", vdate=date(2026, 1, 1), ndate=date(2026, 4, 1))
        add_vaccination(user.id, name="OD", vdate=date(2026, 1, 1), ndate=date(2026, 3, 1))
        add_vaccination(user.id, name="DT", vdate=date(2026, 1, 1), ndate=REF)
        add_vaccination(user.id, name="Done", vdate=date(2026, 1, 1), ndate=None)
        rems = reminders(user.id, REF)
        names = [v.vaccine_name for v, s in rems]
        statuses = [s for v, s in rems]
        assert names == ["OD", "DT", "UP"]          # overdue first, then due, then upcoming
        assert statuses == ["overdue", "due_today", "upcoming"]


def test_dashboard_page_shows_stats_and_reminders(client, logged_in, app, db):
    from datetime import timedelta
    today = date.today()
    with app.app_context():
        add_vaccination(logged_in.id, name="OverdueShot", vdate=today - timedelta(days=200),
                        ndate=today - timedelta(days=10))
    html = client.get("/dashboard/").get_data(as_text=True)
    assert "OverdueShot" in html
    assert "Overdue" in html
    assert "Doses administered" in html


def test_no_next_dose_records_handled_everywhere(client, logged_in, app, db):
    with app.app_context():
        add_vaccination(logged_in.id, name="SoloShot", ndate=None)
    for url in ("/dashboard/", "/vaccinations/", "/vaccinations/report"):
        resp = client.get(url)
        assert resp.status_code == 200
        assert "SoloShot" in resp.get_data(as_text=True)
