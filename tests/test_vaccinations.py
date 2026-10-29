"""Vaccination CRUD, validation, search, filters, pagination, report."""
from datetime import date, timedelta

from tests.conftest import add_vaccination

TODAY = date.today()


def vax_data(**over):
    data = {
        "vaccine_name": "Hepatitis B",
        "dose_number": "1",
        "vaccination_date": (TODAY - timedelta(days=10)).isoformat(),
        "next_dose_date": (TODAY + timedelta(days=50)).isoformat(),
        "notes": "Left arm",
    }
    data.update(over)
    return data


def test_create_vaccination(client, logged_in, app, db):
    resp = client.post("/vaccinations/new", data=vax_data(), follow_redirects=False)
    assert resp.status_code == 302
    from app.models import Vaccination
    with app.app_context():
        rec = db.session.execute(db.select(Vaccination)).scalar_one()
        assert rec.vaccine_name == "Hepatitis B"
        assert rec.dose_number == 1
        assert rec.user_id == logged_in.id
        assert rec.next_dose_date == TODAY + timedelta(days=50)
        assert rec.notes == "Left arm"


def test_create_requires_fields_and_valid_dates(client, logged_in):
    # Missing required fields
    resp = client.post("/vaccinations/new", data={}, follow_redirects=False)
    assert resp.status_code == 200
    assert "This field is required" in resp.get_data(as_text=True)

    # Future administration date rejected
    resp = client.post("/vaccinations/new",
                       data=vax_data(vaccination_date=(TODAY + timedelta(days=5)).isoformat(),
                                     next_dose_date=""))
    assert "cannot be in the future" in resp.get_data(as_text=True)

    # Next dose before/equal to vaccination date rejected
    resp = client.post("/vaccinations/new",
                       data=vax_data(next_dose_date=(TODAY - timedelta(days=11)).isoformat()))
    assert "must be after the date administered" in resp.get_data(as_text=True)

    resp = client.post("/vaccinations/new",
                       data=vax_data(next_dose_date=(TODAY - timedelta(days=10)).isoformat()))
    assert "must be after the date administered" in resp.get_data(as_text=True)


def test_create_allows_empty_next_dose_date(client, logged_in, app, db):
    resp = client.post("/vaccinations/new", data=vax_data(next_dose_date=""))
    assert resp.status_code == 302
    from app.models import Vaccination
    with app.app_context():
        rec = db.session.execute(db.select(Vaccination)).scalar_one()
        assert rec.next_dose_date is None


def test_list_ordered_newest_first_and_paginates(client, logged_in, app, db):
    with app.app_context():
        for i in range(12):
            add_vaccination(logged_in.id, name=f"Vax{i}",
                            vdate=TODAY - timedelta(days=i * 10))
    page1 = client.get("/vaccinations/").get_data(as_text=True)
    assert "Vax0" in page1 and "Vax11" not in page1
    assert "pagination" in page1
    page2 = client.get("/vaccinations/?page=2").get_data(as_text=True)
    assert "Vax11" in page2 and "Vax0" not in page2
    # Page 0 is coerced to page 1
    assert client.get("/vaccinations/?page=0").status_code == 200


def test_detail_edit_delete_roundtrip(client, logged_in, app, db):
    with app.app_context():
        rec = add_vaccination(logged_in.id, name="Typhoid", dose=2)
        rid = rec.id

    # Detail
    html = client.get(f"/vaccinations/{rid}").get_data(as_text=True)
    assert "Typhoid" in html and "Dose 2" in html

    # Edit
    resp = client.post(f"/vaccinations/{rid}/edit",
                       data=vax_data(vaccine_name="Typhoid Booster", dose_number="3",
                                     next_dose_date="", notes="Updated"))
    assert resp.status_code == 302
    with app.app_context():
        from app.models import Vaccination
        rec = db.session.get(Vaccination, rid)
        assert rec.vaccine_name == "Typhoid Booster"
        assert rec.dose_number == 3
        assert rec.next_dose_date is None
        assert rec.notes == "Updated"

    # Delete
    resp = client.post(f"/vaccinations/{rid}/delete")
    assert resp.status_code == 302
    with app.app_context():
        from app.models import Vaccination
        assert db.session.get(Vaccination, rid) is None

    # Detail now 404s
    assert client.get(f"/vaccinations/{rid}").status_code == 404


def test_delete_only_via_post(client, logged_in, app, db):
    with app.app_context():
        rec = add_vaccination(logged_in.id)
        rid = rec.id
    assert client.get(f"/vaccinations/{rid}/delete").status_code == 405
    with app.app_context():
        from app.models import Vaccination
        assert db.session.get(Vaccination, rid) is not None


def test_search_by_name(client, logged_in, app, db):
    with app.app_context():
        add_vaccination(logged_in.id, name="Hepatitis B")
        add_vaccination(logged_in.id, name="Influenza")
    html = client.get("/vaccinations/?q=hepa").get_data(as_text=True)
    assert "Hepatitis B" in html and "Influenza" not in html
    # No results -> friendly empty state
    html = client.get("/vaccinations/?q=zzzznotfound").get_data(as_text=True)
    assert "No records match your filters" in html
    # LIKE wildcards in the query are escaped, not treated as patterns:
    # searching for a literal "%" must match nothing.
    add = client.get("/vaccinations/?q=%25")  # literal %
    assert add.status_code == 200
    assert "No records match your filters" in add.get_data(as_text=True)


def test_status_filters(client, logged_in, app, db):
    with app.app_context():
        add_vaccination(logged_in.id, name="OverdueVax", vdate=TODAY - timedelta(days=100),
                        ndate=TODAY - timedelta(days=5))
        add_vaccination(logged_in.id, name="DueVax", vdate=TODAY - timedelta(days=100),
                        ndate=TODAY)
        add_vaccination(logged_in.id, name="UpcomingVax", vdate=TODAY - timedelta(days=10),
                        ndate=TODAY + timedelta(days=30))
        add_vaccination(logged_in.id, name="DoneVax", vdate=TODAY - timedelta(days=10))

    def names_for(status):
        html = client.get(f"/vaccinations/?status={status}").get_data(as_text=True)
        return html

    html = names_for("overdue")
    assert "OverdueVax" in html and "DueVax" not in html and "UpcomingVax" not in html and "DoneVax" not in html
    html = names_for("due_today")
    assert "DueVax" in html and "OverdueVax" not in html
    html = names_for("upcoming")
    assert "UpcomingVax" in html and "DueVax" not in html
    html = names_for("administered")
    assert "DoneVax" in html and "OverdueVax" not in html


def test_unknown_status_filter_ignored_with_warning(client, logged_in):
    html = client.get("/vaccinations/?status=bogus").get_data(as_text=True)
    assert "Unknown status filter" in html
    assert client.get("/vaccinations/?status=bogus").status_code == 200


def test_date_range_filter(client, logged_in, app, db):
    with app.app_context():
        add_vaccination(logged_in.id, name="OldVax", vdate=date(2020, 1, 15))
        add_vaccination(logged_in.id, name="NewVax", vdate=date(2024, 6, 15))
    html = client.get("/vaccinations/?date_from=2024-01-01&date_to=2024-12-31").get_data(as_text=True)
    assert "NewVax" in html and "OldVax" not in html


def test_invalid_date_range_handled(client, logged_in):
    # Non-date values ignored with warning
    html = client.get("/vaccinations/?date_from=banana").get_data(as_text=True)
    assert "YYYY-MM-DD" in html
    # Reversed range ignored with warning
    html = client.get("/vaccinations/?date_from=2024-12-31&date_to=2024-01-01").get_data(as_text=True)
    assert "Start date is after end date" in html


def test_combined_filters(client, logged_in, app, db):
    with app.app_context():
        add_vaccination(logged_in.id, name="Hepatitis B", vdate=date(2024, 3, 1),
                        ndate=date(2024, 9, 1))
        add_vaccination(logged_in.id, name="Hepatitis A", vdate=date(2023, 3, 1))
        add_vaccination(logged_in.id, name="Influenza", vdate=date(2024, 4, 1))
    html = client.get("/vaccinations/?q=hepatitis&date_from=2024-01-01&date_to=2024-12-31&status=overdue").get_data(as_text=True)
    assert "Hepatitis B" in html
    assert "Hepatitis A" not in html
    assert "Influenza" not in html


def test_clear_filters_link_present_when_filtering(client, logged_in):
    html = client.get("/vaccinations/?q=x").get_data(as_text=True)
    assert "Clear filters" in html


def test_report_lists_only_own_records(client, logged_in, other_user, app, db):
    with app.app_context():
        add_vaccination(logged_in.id, name="MineVax")
        add_vaccination(other_user.id, name="TheirsVax")
    resp = client.get("/vaccinations/report")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "MineVax" in html
    assert "TheirsVax" not in html
    assert "Vaccination History Report" in html


def test_empty_state_when_no_records(client, logged_in):
    html = client.get("/vaccinations/").get_data(as_text=True)
    assert "No vaccination records yet" in html
