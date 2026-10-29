# 💉 VaccTrack — Vaccine & Health Record Keeper

A polished, responsive, database-driven web application that lets individual users securely
maintain their **vaccination history**, track **upcoming / due-today / overdue doses**, and manage a
**health profile**, **allergies**, and **emergency contacts**.

> **Scope disclaimer:** This is a student portfolio project. It is **not** a medical device, provides
> **no diagnosis or prescribing advice**, and never suggests dose schedules. Users enter dates exactly
> as instructed by a qualified healthcare professional or an authoritative national immunisation schedule.

---

## Features

- **Public landing page** with hero, feature overview, and login/register CTAs.
- **Accounts:** registration with unique email, Werkzeug-hashed passwords (scrypt), login/logout,
  per-account data isolation enforced server-side on *every* query.
- **Vaccinations:** full CRUD. Each record = one administered dose (name, dose number, date,
  optional next-dose date, notes). Newest-first ordering, pagination, search by name, filters
  (status + administered-date range, combinable), clear-filters action.
- **Status engine:** `administered` / `upcoming` / `due today` / `overdue`, computed from the
  server's current date (injectable for tests). A dose whose follow-up has been recorded is
  treated as *administered* (series moved on) — one dose never marks a series "completed".
- **Dashboard:** totals (administered / upcoming / due today / overdue), reminder list
  (overdue first), recent history, quick links.
- **Health profile:** optional date of birth (with derived age), blood group, health notes.
- **Allergies:** allergen, severity (Mild/Moderate/Severe), notes, colour-coded cards.
- **Emergency contacts:** name, relationship, internationally-lenient phone validation.
- **Printable vaccination report** with dedicated print CSS (nav/controls hidden).
- **UX:** Bootstrap 5 (vendored locally), mobile navigation, empty states, flash messages,
  confirmation modals for every destructive action, form loading states, keyboard focus
  indicators, skip link, inline SVG icon set, custom 404/403/400/500 pages.
- **Account deletion** (Settings) with password confirmation — cascades to all records.
- **Health-check endpoint:** `GET /healthz` for deployment platforms.
- **Demo seed script** with synthetic data only (cannot touch existing accounts).

## Technology stack

| Layer | Choice |
|---|---|
| Backend | Python 3, Flask 3 (modular app factory + blueprints) |
| Frontend | Server-rendered Jinja2 templates, Bootstrap 5.3 (vendored), vanilla JS, CSS3 |
| Database | SQLite (local dev) · PostgreSQL supported via `DATABASE_URL` |
| ORM / migrations | Flask-SQLAlchemy 3.1 (SQLAlchemy 2.x style), Flask-Migrate (Alembic) |
| Auth | Flask-Login sessions, Werkzeug password hashing (scrypt) |
| Forms / CSRF | Flask-WTF + WTForms, CSRFProtect on all POST routes |
| Config | python-dotenv, environment-based `Config` classes |
| Production server | Gunicorn |
| Tests | pytest + Flask test client (80 tests, isolated in-memory DB) |

## Architecture

```
vaccine-health-keeper/
├── app/
│   ├── __init__.py          # app factory, error pages, security headers, /healthz
│   ├── extensions.py        # db, login_manager, migrate, csrf + SQLite FK pragma
│   ├── models.py            # User, Vaccination, HealthProfile, Allergy, EmergencyContact
│   ├── forms.py             # all WTForms with server-side validation
│   ├── services.py          # status engine, dashboard stats, reminders (injectable date)
│   ├── helpers.py           # get_owned_or_404 (IDOR defense), safe redirects
│   ├── auth/routes.py       # register / login / logout
│   ├── dashboard/routes.py  # dashboard + account settings/deletion
│   ├── vaccinations/routes.py  # CRUD, search/filter/pagination, report
│   ├── health/routes.py     # profile, allergies, contacts
│   ├── templates/           # base, macros, per-blueprint pages, error pages
│   └── static/              # css/style.css, js/main.js, vendored Bootstrap, favicon
├── instance/                # local SQLite DB + dev fallback secret (gitignored)
├── migrations/              # Alembic migrations
├── scripts/seed_demo.py     # synthetic demo data (never overwrites)
├── tests/                   # pytest suite
├── config.py                # Dev / Test / Prod configs from env vars
├── run.py                   # dev entry point
├── wsgi.py                  # gunicorn entry point
├── Procfile                 # web: gunicorn wsgi:app
└── requirements.txt
```

### Data model

```
User (id, name, email UNIQUE, password_hash, created_at)
 ├── Vaccination      (user_id FK, vaccine_name, dose_number, vaccination_date,
 │                     next_dose_date NULL, notes NULL, created_at, updated_at)
 │                     index: (user_id, vaccination_date)
 ├── HealthProfile    (user_id FK UNIQUE — one per user — dob NULL, blood_group NULL,
 │                     health_notes NULL, updated_at)
 ├── Allergy          (user_id FK, allergen, severity, notes NULL, created_at)
 └── EmergencyContact (user_id FK, name, relationship, phone_number, created_at)
```

All foreign keys are `NOT NULL` with `ON DELETE CASCADE` (enforced on SQLite via
`PRAGMA foreign_keys=ON` per connection — see `extensions.py`), so no orphaned records can exist.
Dates are real `DATE`/`DATETIME` columns, never strings.

### Status rules (per record)

| Status | Condition (reference date = server today, injectable in tests) |
|---|---|
| Administered | `next_dose_date` is NULL, **or** a record exists for the same vaccine (case-insensitive) with `dose_number + 1` |
| Upcoming | `next_dose_date > today` and the follow-up dose is not recorded |
| Due today | `next_dose_date == today` and the follow-up dose is not recorded |
| Overdue | `next_dose_date < today` and the follow-up dose is not recorded |

## Installation

```bash
git clone <your-repo-url> && cd vaccine-health-keeper
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # then edit .env (see below)
```

### Environment variables (`.env`)

| Variable | Required | Notes |
|---|---|---|
| `FLASK_ENV` | no | `development` (default) / `testing` / `production` |
| `SECRET_KEY` | **yes in production** | `python -c "import secrets; print(secrets.token_hex(32))"`. In dev, a key is auto-generated into gitignored `instance/secret_key.dev` so multiple workers share one key. Production **fails fast** without it. |
| `DATABASE_URL` | no | Defaults to SQLite at `instance/app.db`. Use `postgresql://user:pass@host:5432/dbname` in production (recommended). `postgres://` URLs are normalised automatically. |
| `SESSION_COOKIE_SECURE` | no | Set `true` behind HTTPS (production defaults to `true` unless explicitly set). |
| `ITEMS_PER_PAGE` | no | Pagination size (default 8). |
| `REMINDER_WINDOW_DAYS` | no | Reserved for future reminder tuning (default 60). |

### Initialise the database

```bash
flask --app run.py db upgrade        # applies Alembic migrations (creates all tables)
python scripts/seed_demo.py          # optional synthetic demo data (idempotent, never overwrites)
```

Demo login (fictional data only): `demo@example.com` / `DemoPass123!`

### Run locally

```bash
python run.py                        # dev server → http://localhost:5000
# or production-style:
FLASK_ENV=production SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))") \
  gunicorn --bind 0.0.0.0:5000 wsgi:app
```

### Run tests

```bash
python -m pytest          # 80 tests — isolated in-memory SQLite, synthetic data only
```

## Deployment

The app is deployment-ready for any Python host:

- **Entry point:** `wsgi:app` (Gunicorn). A `Procfile` is included (`web: gunicorn wsgi:app --bind 0.0.0.0:$PORT`).
- **`/healthz`** returns `{"status":"ok"}` (200) for platform health checks, verifying DB connectivity.
- **Migrations:** run `flask db upgrade` as a release step (or on a platform that supports it).
- **Database choice — important:**
  - **SQLite** works only on hosts with a **persistent writable disk** (e.g. a VPS, Fly.io volume,
    Render *with* a persistent disk attached — check the plan). Many free tiers use an **ephemeral
    filesystem**: your health records would vanish on every redeploy/restart. Do not use those with SQLite.
  - **PostgreSQL** is the recommended production choice: set `DATABASE_URL` and the app uses it
    unchanged (SQLAlchemy handles both). Free Postgres tiers (e.g. Neon/Supabase-style services)
    generally persist data — verify the current terms of whichever provider you pick.
- **Production checklist:** `FLASK_ENV=production`, strong `SECRET_KEY` (env var, never in git),
  HTTPS terminated at the platform/proxy, `SESSION_COOKIE_SECURE=true`, debug disabled (default),
  backups configured (see below).

> **Honesty note:** this repository ships with deployment *configuration* (Procfile, health check,
> Postgres support, secure-by-default production config), but publishing to a specific external
> host requires an account/API token on that host. No external deployment was performed or
> claimed during development; the app was verified locally under Gunicorn.

### Backups, restore, retention, deletion

- **SQLite:** back up by copying `instance/app.db` (stop writes or use `sqlite3 app.db ".backup backup.db"` for a consistent snapshot). **Test restores** by pointing a staging copy at the backup.
- **PostgreSQL:** use `pg_dump` / provider snapshots; test restore into a scratch database periodically.
- **Retention:** data is kept until the user deletes it.
- **Account deletion:** Settings → *Delete my account* (password-confirmed) cascades to every record at the DB level.

## Security considerations

See [`docs/SECURITY_AUDIT.md`](docs/SECURITY_AUDIT.md) for the full audit. Highlights:

- Passwords hashed with Werkzeug **scrypt**; plaintext never stored or logged (`__repr__` of models is ID-only).
- **IDOR defense:** every record access goes through `get_owned_or_404` → uniform 404 for missing *and* foreign records (no existence leaks). Covered by dedicated cross-user tests for every resource and verb.
- **CSRF** on all POSTs (login, logout, CRUD, account deletion), tested with CSRF enabled.
- **SQL injection:** SQLAlchemy bind parameters only; LIKE searches escape `%`/`_`/`\`.
- **XSS:** Jinja2 autoescaping, no `|safe` filters anywhere (enforced by a regression test).
- **Open redirect:** `next=` only honoured for same-site relative paths (`https://`, `//`, `/\` rejected).
- **Cookies:** HttpOnly + SameSite=Lax; Secure in production; secret key required in production, shared dev fallback key persisted in gitignored `instance/` so multi-worker setups don't break CSRF.
- **Security headers:** CSP (`script-src 'self'`, no inline JS), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`.
- **Error pages** reveal nothing; debug mode off in production; `/healthz` does not expose internals.
- **Dependencies:** `pip-audit -r requirements.txt` → *no known vulnerabilities* (run 2026-10-29).

Remaining risks (require deployment-side action, documented in the audit): login **rate limiting**
(not implemented), HTTPS enforcement (platform/proxy responsibility), backup cadence, and
host filesystem persistence verification.

## Current limitations & future enhancements

- ❌ **Password reset:** deliberately **not implemented** — a secure reset needs real email
  delivery (token + provider). Faking it would be a security anti-pattern. Documented as future work.
- ❌ **Email/push notifications:** reminders are **in-app only**. No external notifications exist.
- ❌ No login rate limiting / account lockout (add e.g. Flask-Limiter before real-world use).
- ❌ No PDF export (print-to-PDF via the browser print dialog on `/vaccinations/report` works well).
- ❌ No multi-language support, no dark mode toggle (theme is light by design).
- Future ideas: vaccine series grouping view, iCal export of reminders, TOTP 2FA, audit log.

## Manual testing checklist

See [`docs/MANUAL_TESTING.md`](docs/MANUAL_TESTING.md).

## License / attribution

Student portfolio project. Bootstrap 5.3 is vendored under the MIT license (© Bootstrap team).
All demo data is synthetic.
