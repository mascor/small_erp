# CLAUDE.md — Small ERP Project Instructions

## Project Overview

Small ERP is a web-based mini-ERP application for managing revenue activities, costs, agents, and profit distribution for small service companies. The UI and domain language are in **Italian**; code is written in English.

- **Framework**: Flask 3.1.0 + SQLAlchemy 3.1.1
- **Database**: SQLite (file: `instance/erp.db`)
- **Auth**: Flask-Login + Flask-WTF (CSRF)
- **Python**: 3.12+
- **Tests**: pytest with coverage

---

## Essential Commands

```bash
# Install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Initialize database (creates tables + superadmin)
python init_db.py

# Seed demo data (idempotent)
python seed_demo.py

# Run development server
python run.py  # Listens on 127.0.0.1:5000

# Run tests
pytest
pytest --cov=app --cov-report=term-missing   # with coverage
pytest -m unit                                # fast unit tests only
pytest -m security                            # security tests
pytest tests/test_security.py -v             # specific file
```

---

## Project Structure

```
app/
├── __init__.py        # Flask app factory, config, security headers
├── models.py          # SQLAlchemy ORM models (all 6 tables)
├── auth.py            # Login/logout routes
├── dashboard.py       # Dashboard KPI view
├── activities.py      # Revenue activities CRUD (largest module ~420 LOC)
├── agents.py          # Agent management
├── users.py           # User management (superadmin only)
├── reports.py         # Monthly financial reports
├── audit.py           # Audit log viewer (superadmin only)
├── audit_service.py   # Audit logging service (called from all write routes)
├── services.py        # Business logic: financial calculations
├── i18n.py            # Italian/English translation dict
├── logging_config.py  # Rotating file logging setup
├── manual.py          # User manual route
└── templates/         # Jinja2 HTML templates
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── activities/    # index.html, form.html, detail.html
    ├── agents/
    ├── users/
    ├── reports/
    ├── audit/
    └── manual.html

tests/
├── conftest.py              # Shared fixtures (app, client, users, activity)
├── test_auth.py             # Auth flows
├── test_models.py           # ORM tests
├── test_services.py         # Business logic tests
├── test_routes.py           # Route/view tests
├── test_audit_service.py    # Audit logging tests
├── test_security.py         # 27 security test cases
├── test_ui.py               # Full UI/integration tests
├── test_init_db.py          # DB initialization tests
└── browser_test.py          # Selenium browser tests

init_db.py      # DB init + superadmin creation
seed_demo.py    # Demo data seeder
run.py          # App entry point
.env            # Environment variables (SECRET_KEY, SUPERADMIN_PASSWORD, etc.)
```

---

## Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Min 16 chars, cryptographically random |
| `SUPERADMIN_PASSWORD` | Yes | Admin password (read at login, not stored in DB) |
| `DATABASE_PATH` | Yes | SQLite DB path (e.g., `instance/erp.db`) |
| `LOG_DIR` | No | Log directory (default: `logs/`) |
| `FLASK_DEBUG` | No | `true` for dev, `false` for prod |

**Critical**: The superadmin password is **never stored** in the DB. It is read from `.env` at every login attempt. The DB stores only a random placeholder hash.

---

## Database Schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| username | String(80) UNIQUE | Login name |
| email | String(120) UNIQUE | Legacy field (hidden in UI) |
| password_hash | String(256) | Werkzeug PBKDF2-SHA256 |
| full_name | String(200) | |
| is_superadmin | Boolean | Controls admin access |
| is_active_user | Boolean | Soft delete flag |
| created_at, updated_at | DateTime | |

### `agents`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| first_name, last_name | String | |
| email | String | Optional |
| default_percentage | Numeric(5,2) | Commission rate 0–100 |
| is_active | Boolean | Soft delete |
| notes | Text | |

### `revenue_activities`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| title, description | String/Text | |
| date | Date | |
| status | Enum | `bozza`/`confermata`/`chiusa` |
| total_revenue | Numeric(12,2) | Max 999,999,999.99 |
| agent_id | FK → agents | Nullable |
| agent_percentage | Numeric(5,2) | Commission % for this activity |
| created_by | FK → users | Ownership for authorization |
| created_at, updated_at | DateTime | |

### `activity_costs`
| Column | Type | Notes |
|--------|------|-------|
| activity_id | FK → revenue_activities | CASCADE DELETE |
| category | Enum | `materiale`/`trasporto`/`consulenza`/`marketing`/`spese_vive`/`altro` |
| cost_type | Enum | `operativo`/`extra` |
| amount | Numeric(12,2) | |

### `activity_participants`
| Column | Type | Notes |
|--------|------|-------|
| activity_id | FK → revenue_activities | CASCADE DELETE |
| user_id | FK → users | Nullable (external participants allowed) |
| work_share | Numeric(5,2) | % weight for profit distribution |
| fixed_compensation | Numeric(12,2) | Flat payment |

### `audit_logs`
| Column | Type | Notes |
|--------|------|-------|
| user_id | FK → users | Nullable |
| action_type | Enum | `login`/`logout`/`create`/`update`/`delete`/`status_change`/`user_create`/`user_update` |
| entity_type | String | Model name |
| old_values, new_values | JSON text | State snapshots |
| ip_address | String(45) | IPv4/IPv6 |

---

## Authorization Rules

| Action | Regular User | Superadmin |
|--------|-------------|------------|
| View activities | Own only | All |
| Create activity | Yes | Yes |
| Edit/Delete activity | Own only | All |
| Manage agents | Yes | Yes |
| Manage users | No | Yes |
| View audit logs | No | Yes |
| View reports | Yes | Yes |

**IDOR protection**: `activities.py` always checks `activity.created_by == current_user.id` before allowing edit/delete. Do not remove or weaken this check.

---

## Financial Calculation Logic (services.py)

```
agent_commission     = total_revenue × agent_percentage / 100
total_costs          = operative_costs + extra_costs
net_margin           = total_revenue - total_costs - agent_commission
distributable        = net_margin - sum(fixed_compensations)
participant_share    = fixed_compensation + (distributable × work_share / total_shares)
```

- All monetary values use Python `Decimal` (never `float`)
- Rounding: `ROUND_HALF_UP` to 2 decimal places
- Input max: `999_999_999.99`; no negative values

---

## Security Requirements

These were all identified in a security audit (April 2026) — **do not regress**:

1. **Session fixation**: Call `session.clear()` before `login_user()` in auth.py
2. **Open redirect**: Validate `next` param with `url_for` comparison, block external URLs
3. **Logout via POST only**: The logout route must be POST with CSRF token
4. **CSRF**: All state-changing forms must include `{{ form.hidden_tag() }}` or `{{ csrf_token() }}`
5. **Security headers**: Set in `app/__init__.py` after-request hook — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
6. **Password policy**: Min 12 chars, 1 uppercase, 1 lowercase, 1 digit (enforced in users.py)
7. **Audit wildcard injection**: Strip `%` and `_` from username filter inputs
8. **Date injection**: Validate date inputs as ISO format before passing to queries
9. **No exception text in UI**: Use generic error messages; log the real exception server-side
10. **Decimal overflow**: Reject values > 999,999,999.99 in all numeric inputs

**Not yet implemented** (do not add without user approval):
- Rate limiting / account lockout
- `SESSION_COOKIE_SECURE=True` (needs HTTPS)
- Content Security Policy header
- Database encryption at rest

---

## Audit Logging

Every write operation must call `audit_service.log_action()`. Pattern:

```python
from app.audit_service import log_action

# Before edit: capture old state
old_vals = {'field': old_value}

# After successful DB commit:
log_action(
    action_type='update',          # create / update / delete / status_change
    entity_type='RevenueActivity',
    entity_id=activity.id,
    description='Short human-readable summary',
    old_values=old_vals,           # None for create
    new_values={'field': new_val}  # None for delete
)
```

---

## Internationalization (i18n.py)

- UI language toggled via `?lang=it` / `?lang=en` query param, stored in session
- Translation dict lives in `app/i18n.py`
- Templates use `{{ t('key') }}` helper (available as template global)
- Add new strings to **both** `it` and `en` dicts simultaneously
- Italian is the primary/default language

---

## Testing Guidelines

- Tests use an **in-memory SQLite DB** (separate from `instance/erp.db`)
- Do **not** mock SQLAlchemy — tests hit the real (test) DB
- Key fixtures in `conftest.py`:
  - `app` — test Flask app
  - `client` — test HTTP client
  - `superadmin_user` — user with `is_superadmin=True`
  - `operator_user` — regular user
  - `agent` — test agent
  - `revenue_activity` — activity with costs and participants
- Mark tests with: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.security`, etc.
- Run `pytest -m "not slow"` for quick feedback during development

---

## Logging

Three rotating log files in `logs/` (daily rotation, 30-day retention):
- `app.log` — INFO level
- `error.log` — ERROR level only
- `debug.log` — DEBUG level (verbose)

Log with: `import logging; logger = logging.getLogger(__name__)`

---

## Common Patterns

### Adding a new route
1. Add route function to the appropriate blueprint file in `app/`
2. Add template in `app/templates/<module>/`
3. Add i18n strings to `app/i18n.py` (both `it` and `en`)
4. Call `log_action()` for any write operation
5. Add tests in `tests/test_routes.py` or the relevant test file

### Adding a new model field
1. Add column to `app/models.py`
2. Update `init_db.py` if a migration is needed
3. Update `services.py` calculations if financial
4. Update audit snapshots (old_values/new_values) in affected routes
5. Update templates and i18n strings
6. Add tests

### Status transitions (activities)
Valid flow: `bozza` → `confermata` → `chiusa`  
Backwards transitions are allowed for superadmin only. Enforce in `activities.py`.

---

## What NOT to Change Without Discussion

- The superadmin authentication mechanism (env-based password, not DB-stored)
- The `session.clear()` before `login_user()` (session fixation protection)
- The IDOR ownership check in activity edit/delete routes
- Switching from `Decimal` to `float` for any monetary calculation
- The audit log schema (append-only by design)
