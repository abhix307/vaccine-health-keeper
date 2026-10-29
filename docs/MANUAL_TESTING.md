# Manual testing checklist

Run these against a local instance (`python run.py` → http://localhost:5000).
Automated coverage lives in `tests/` (`python -m pytest`).

## Public pages
- [ ] `/` renders hero, feature cards, CTAs; nav collapses to a hamburger < 992px.
- [ ] "Create free account" and "Sign in" buttons lead to working pages.
- [ ] Unknown URL (e.g. `/nope`) shows the styled 404 page with useful links.
- [ ] `/healthz` returns `{"status": "ok"}`.

## Registration & login
- [ ] Register with short password (<8 chars) → inline error, no account created.
- [ ] Mismatched confirmation → inline error.
- [ ] Invalid email (`abc@`) → inline error.
- [ ] Register twice with same email (try different case) → "already exists" error.
- [ ] Successful registration lands on the dashboard with a welcome flash.
- [ ] Login with wrong password → generic "Invalid email or password." (401), no user enumeration hint.
- [ ] Logout via nav button → flash + landing page; `/dashboard/` then redirects to login.
- [ ] While logged out, visiting `/vaccinations/` redirects to `/login?next=...` and returns you there after login.

## Vaccinations CRUD
- [ ] Add record: all fields save; you land on the detail page.
- [ ] Add with future "date administered" → rejected with clear error.
- [ ] Add with next-dose date ≤ administered date → rejected.
- [ ] Leave next-dose date empty → saves; status shows **Administered**.
- [ ] Edit a record → values pre-filled (including dose number); changes persist.
- [ ] Delete → confirmation modal → record disappears; direct URL now 404s.
- [ ] List is ordered newest-first; >8 records produce working pagination (filters preserved across pages).

## Statuses & reminders (set dates relative to today)
- [ ] next-dose = yesterday, no dose 2 recorded → **Overdue** (red).
- [ ] next-dose = today → **Due today**.
- [ ] next-dose = tomorrow → **Upcoming**.
- [ ] Record dose 2 of the same vaccine → dose 1's status flips to **Administered** and leaves the reminder list.
- [ ] Dashboard counts match: total = every record; upcoming/due/overdue as above.

## Search, filters, report
- [ ] Search `hep` matches "Hepatitis B" case-insensitively; `%` as query matches nothing (wildcards escaped).
- [ ] Status filter shows only that status; date-range filter bounds by administered date.
- [ ] Combine search + status + range → correct intersection; "Filters active" + **Clear filters** works.
- [ ] Reversed range (from > to) or junk dates → warning banner, filter ignored, no crash.
- [ ] `/vaccinations/report`: browser Print Preview hides nav/footer/buttons, prints the table + header.

## Health profile / allergies / contacts
- [ ] Save profile with all-empty fields → OK; DOB in future → rejected; invalid blood group impossible via UI.
- [ ] Age appears once a valid DOB is saved.
- [ ] Add allergy with each severity → card border colour matches (green/amber/red).
- [ ] Contact phone: `+91 98765 43210`, `(555) 010-9999`, `044 20 7946 0958` accepted; `abcd`, `12` rejected.
- [ ] `tel:` links on contact cards.
- [ ] Delete both types → modal confirm → gone; empty states render.

## Cross-user isolation (two browsers / one incognito)
- [ ] As user B, open user A's record URL → styled 404, no data.
- [ ] As user B, POST to A's edit/delete endpoints (curl with B's CSRF token) → 404, A's data unchanged.
- [ ] B's dashboard/list/report never mention A's data.

## Account settings
- [ ] Delete account with wrong password → error, nothing deleted.
- [ ] Delete with correct password → modal confirm → logged out, flash, login with old credentials now fails.

## Responsiveness & a11y
- [ ] Mobile (≤ 576px): stat cards 2×2, tables scroll, nav collapses.
- [ ] Tab through a page: visible focus rings everywhere; skip link works.
- [ ] Flash messages auto-dismiss after ~6s (success/info) and have a close button.
- [ ] Submit a form: button shows spinner and disables until navigation.
