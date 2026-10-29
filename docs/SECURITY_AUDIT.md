# Security audit — Vaccine & Health Record Keeper

Date: 2026-10-29 · Scope: application code, configuration, dependencies, and a live local
Gunicorn instance verified with cross-user (IDOR) attack attempts.

This audit distinguishes **tested protections** (automated regression tests exist) from
**risks that still require deployment-side review**. Standard libraries alone are *not*
treated as proof of security.

## 1. Findings fixed during development (with regression tests)

| # | Finding | Severity | Fix | Test |
|---|---|---|---|---|
| 1 | SQLite does not enforce `ON DELETE CASCADE` without `PRAGMA foreign_keys=ON`; deleting a user left orphaned health records | **High** (data integrity/privacy) | Per-connection pragma listener in `app/extensions.py` (SQLite-only; Postgres enforces FKs natively) | `test_models.py::test_deleting_user_cascades_all_records` |
| 2 | Dev fallback `SECRET_KEY` was generated per-process → two Gunicorn workers had different keys → all POSTs failed CSRF (400) in live verification | **High** (availability; would also break sessions) | Fallback key persisted to gitignored `instance/secret_key.dev` (mode 0600), shared by workers | `test_config.py::test_dev_fallback_secret_key_is_stable_across_processes` |
| 3 | Huge integer IDs (`/vaccinations/99999999999999999999`) crashed SQLite with `OverflowError` → 500 | Medium | Range check in `get_owned_or_404` → uniform 404 | `test_idor.py::test_malformed_ids_are_safe_404` |
| 4 | Phone regex rejected internationally common formats like `(555) 010-9999` | Low (usability) | Regex allows leading `(` | `test_health.py::test_contact_phone_validation_is_international_friendly` |
| 5 | Inline `onclick`/`<script>` prevented a strict CSP | Low | Moved to `static/js/main.js` with data-attributes; CSP now `script-src 'self'` | `test_security_headers.py` |
| 6 | Test/demo fixtures originally used `@example.invalid`, which `email_validator` rejects as a reserved special-use domain — forms could never validate | Low (test infra) | Switched to RFC 2606 documentation domain `example.com` | full suite green |

## 2. Tested protections (automated)

- **Password storage:** Werkzeug scrypt hashes; plaintext never stored, login verifies hash.
  Tests assert hash prefix and absence of plaintext. (`test_auth.py`)
- **IDOR / ownership:** every read, edit, delete of vaccination, allergy, contact returns a
  uniform 404 for another user's IDs — including POSTs *with valid CSRF tokens*; victim data
  verified unchanged; victim data never appears in attacker's dashboard, list, report.
  (`test_idor.py` — 10 tests, verified again live via curl against Gunicorn)
- **CSRF:** with CSRF enabled, POSTs without token, with wrong token, logout, and delete are
  all rejected with 400 and no state change; valid token succeeds. (`test_csrf.py`)
- **Auth enforcement:** all private routes redirect anonymous users to login; GET /logout → 405.
- **Generic auth errors:** wrong password and unknown email yield identical 401 + message
  (no user enumeration).
- **Open redirect:** `next=https://…`, `next=//…`, `next=/\…` all fall back to the dashboard;
  legitimate relative `next` honoured. (`test_auth.py::test_login_next_redirect_is_safe`)
- **SQL injection:** all queries use SQLAlchemy bind parameters; LIKE search escapes
  `%`, `_`, `\` (verified: searching literal `%` matches nothing). Filter params
  (status, dates) are validated/whitelisted before use.
- **XSS:** Jinja2 autoescaping; zero `|safe` usages — enforced by a regression test that
  greps all templates. Confirmation-modal bodies use `{% call %}` blocks so user content
  is escaped by the engine, not string-concatenated.
- **Server-side validation:** required fields, positive dose numbers, no future
  administration dates, next-dose strictly after administration date, DOB in the past,
  whitelisted blood groups & severities, phone pattern + digit-count floor. Client-side
  checks are convenience only; every rule is re-checked server-side.
- **Status engine boundaries:** yesterday/today/tomorrow and missing dates covered with an
  injected reference date; series continuation is case-insensitive and **user-scoped**
  (another user's dose 2 does not clear your overdue). (`test_status_logic.py`)
- **Model constraints:** unique email (case-insensitive at the form layer, DB unique
  constraint), non-nullable FKs, one HealthProfile per user (unique FK), real DATE/DATETIME
  columns, leak-free `__repr__`.
- **Error handling:** styled 400/403/404/500 pages with no stack traces or framework names.

## 3. Configuration & transport

- `SESSION_COOKIE_HTTPONLY=True`, `SameSite=Lax` always; `Secure` defaults to **True** in
  production unless explicitly overridden; `REMEMBER_COOKIE_*` mirrors it.
- Production config **fails fast** without `SECRET_KEY`; debug is off; dev fallback key is
  file-persisted with 0600 permissions and gitignored.
- Security headers on every response: strict-ish **CSP** (`default-src 'self'; script-src 'self';
  style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; base-uri 'self';
  form-action 'self'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: same-origin`, `Permissions-Policy` (no geo/camera/mic).
  *Note:* `style-src 'unsafe-inline'` is required by inline `style=` attributes/Bootstrap;
  tightening to nonces is future work.
- `.gitignore` excludes `.env`, `instance/` (DB + dev secret), caches, venvs.
- `.env.example` documents every variable; no secrets in the repo.
- HTTPS itself is terminated by the hosting platform/proxy — the app sets `Secure` cookies
  but cannot force TLS; deploy behind HTTPS.

## 4. Data handling & privacy

- All queries scoped by `current_user.id`; no global listings anywhere.
- Logging: no request bodies, query strings, or DB contents logged; model `__repr__`s emit
  IDs only; health-check logs failures without details.
- Demo/seed data is synthetic and idempotent (never updates existing rows); demo account uses
  a documentation-domain email.
- Account deletion (password-confirmed) cascades to all records; verified by test #1 above.

## 5. Dependencies

`pip-audit -r requirements.txt` (2026-10-29): **no known vulnerabilities**. Pinned versions:
Flask 3.1.3, Werkzeug 3.1.9, SQLAlchemy 2.1.6, Flask-SQLAlchemy 3.1.1, Flask-Login 0.6.3,
Flask-WTF 1.3.0, Flask-Migrate 4.1.0, email_validator 2.3.0, gunicorn 26.2.0, python-dotenv 1.2.4.

## 6. Residual risks — require deployment-side review (NOT claimed as solved)

| Risk | Notes |
|---|---|
| **No login rate limiting / lockout** | Online password guessing is not throttled. Add Flask-Limiter (e.g. 5 attempts/min/IP) before real-world use. |
| **No password reset** | Deliberately omitted (requires real email delivery). Users cannot recover accounts. |
| **HTTPS enforcement** | Depends on the host/proxy; add HSTS at the proxy once HTTPS is confirmed. |
| **Storage persistence** | SQLite is only safe on hosts with persistent disks. **Verify on the chosen host** that `instance/app.db` survives restarts *and* redeploys; otherwise use PostgreSQL via `DATABASE_URL`. Locally verified across Gunicorn restarts. |
| **Backups** | No automated backup exists in-repo; set up provider snapshots/`pg_dump` and **test restores**. |
| **Session revocation** | Changing `SECRET_KEY` invalidates all sessions (acceptable); there is no per-session revocation list. |
| **Sensitive-data at rest** | SQLite/Postgres data is not encrypted at rest by the app; rely on host disk encryption or add field-level encryption if required. |
| **DoS** | No request-size limits beyond framework defaults; platforms usually mitigate. |

## 7. Verification commands

```bash
python -m pytest                      # 80 tests incl. IDOR + CSRF suites
pip-audit -r requirements.txt         # dependency CVE scan
grep -rn "|safe\|| safe" app/templates/   # must return nothing
```
