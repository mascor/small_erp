# Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every real bug, security gap, and code-quality issue found during production-readiness review, leaving all 388 tests green and the codebase deployable.

**Architecture:** The app is a Flask 3.1.0 + SQLAlchemy ERP with one superadmin and multiple regular users. All write operations go through blueprint routes; financial logic is centralized in `services.py`. Security headers and CSP are set in `app/__init__.py`'s after-request hook.

**Tech Stack:** Python 3.12, Flask 3.1.0, SQLAlchemy 3.1.1, SQLite, Flask-Login, Flask-WTF/CSRF, Flask-Limiter, Jinja2, vanilla CSS/JS.

---

## Issues Found (Executive Summary)

| # | Area | Severity | Description |
|---|------|----------|-------------|
| 1 | Security | **CRITICAL** | `edit_cost`, `delete_cost`, `edit_participant`, `delete_participant` routes lack superadmin authorization check — any authenticated user can call them |
| 2 | Security | **HIGH** | CSS `@import` from `fonts.googleapis.com` violates CSP `style-src 'self'` — fonts silently fail to load in production |
| 3 | Code quality | Medium | `audit_service.log_action` commits a separate transaction; if audit commit fails after business commit succeeds, the operation is silently unaudited |
| 4 | Code quality | Low | `calc_dashboard_stats` returns duplicate keys (`open_activities`/`open_activities_count`, `month_margin`/`month_net_margin`) |
| 5 | Code quality | Low | `_can_modify_activity(activity)` ignores its `activity` parameter — misleading signature |
| 6 | Code quality | Low | `edit_cost` route lacks error logging (unlike `add_cost`) |
| 7 | Docs/Ops | Low | README references `.env.example` which does not exist |

---

## File Map

| File | Change |
|------|--------|
| `app/activities.py` | Add superadmin checks to `edit_cost`, `delete_cost`, `edit_participant`, `delete_participant`; fix `_can_modify_activity` signature; add error logging to `edit_cost` |
| `app/services.py` | Remove duplicate keys from `calc_dashboard_stats` |
| `app/audit_service.py` | Add `_flush_only` parameter to avoid double-commit pattern; update callers (activities.py already commits before calling log_action — audit is appended to same session and committed together) |
| `app/static/css/style.css` | Remove Google Fonts `@import`; use system font stack |
| `app/__init__.py` | Update CSP to remove `font-src 'self'` restriction (not needed after removing Google Fonts) |
| `.env.example` | Create with all required/optional env vars documented |
| `tests/test_security.py` | Add tests for the four newly-protected routes |

---

## Task 1: Fix IDOR — Authorization on cost and participant sub-routes

**Files:**
- Modify: `app/activities.py` — `edit_cost` (line 337), `delete_cost` (line 384), `edit_participant` (line 469), `delete_participant` (line 507)

- [ ] **Step 1.1: Write failing security tests**

Add to `tests/test_security.py` (after existing tests):

```python
# ── Sub-route IDOR: edit_cost ──────────────────────────────────────────────

class TestCostSubrouteAuth:
    """Regular users must not be able to edit or delete activity costs."""

    def test_edit_cost_requires_superadmin(self, client, operator_user, activity_cost, revenue_activity):
        client.post('/login', data={'username': 'operator', 'password': 'Operator1234!'})
        resp = client.post(
            f'/activities/{revenue_activity.id}/costs/{activity_cost.id}/edit',
            data={
                'description': 'hacked',
                'amount': '1',
                'category': 'altro',
                'cost_type': 'operativo',
                'date': '2026-01-01',
                'line_type': 'generic',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'Non autorizzato' in resp.data or b'Not authorized' in resp.data

    def test_delete_cost_requires_superadmin(self, client, operator_user, activity_cost, revenue_activity):
        client.post('/login', data={'username': 'operator', 'password': 'Operator1234!'})
        resp = client.post(
            f'/activities/{revenue_activity.id}/costs/{activity_cost.id}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'Non autorizzato' in resp.data or b'Not authorized' in resp.data


class TestParticipantSubrouteAuth:
    """Regular users must not be able to edit or delete activity participants."""

    def test_edit_participant_requires_superadmin(self, client, operator_user, activity_participant, revenue_activity):
        client.post('/login', data={'username': 'operator', 'password': 'Operator1234!'})
        resp = client.post(
            f'/activities/{revenue_activity.id}/participants/{activity_participant.id}/edit',
            data={
                'user_id': str(operator_user.id),
                'work_share': '0',
                'fixed_compensation': '0',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'Non autorizzato' in resp.data or b'Not authorized' in resp.data

    def test_delete_participant_requires_superadmin(self, client, operator_user, activity_participant, revenue_activity):
        client.post('/login', data={'username': 'operator', 'password': 'Operator1234!'})
        resp = client.post(
            f'/activities/{revenue_activity.id}/participants/{activity_participant.id}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'Non autorizzato' in resp.data or b'Not authorized' in resp.data
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```bash
cd /opt/small_erp && python -m pytest tests/test_security.py::TestCostSubrouteAuth tests/test_security.py::TestParticipantSubrouteAuth -v
```

Expected: FAIL (4 tests) — the routes currently have no superadmin check.

- [ ] **Step 1.3: Add superadmin guard to the four routes**

In `app/activities.py`, make these four changes:

**`edit_cost` (around line 337)** — add guard at the top, before the auto-generated check:
```python
@activities_bp.route('/<int:id>/costs/<int:cost_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_cost(id, cost_id):
    if not current_user.is_superadmin:
        flash(tr('Non autorizzato.', 'Not authorized.'), 'error')
        return redirect(url_for('activities.detail', id=id))
    activity = db.get_or_404(RevenueActivity, id)
    cost = db.get_or_404(ActivityCost, cost_id)
    # ... rest unchanged
```

**`delete_cost` (around line 384)** — add guard at the top:
```python
@activities_bp.route('/<int:id>/costs/<int:cost_id>/delete', methods=['POST'])
@login_required
def delete_cost(id, cost_id):
    if not current_user.is_superadmin:
        flash(tr('Non autorizzato.', 'Not authorized.'), 'error')
        return redirect(url_for('activities.detail', id=id))
    cost = db.get_or_404(ActivityCost, cost_id)
    # ... rest unchanged
```

**`edit_participant` (around line 469)** — add guard at the top:
```python
@activities_bp.route('/<int:id>/participants/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
def edit_participant(id, pid):
    if not current_user.is_superadmin:
        flash(tr('Non autorizzato.', 'Not authorized.'), 'error')
        return redirect(url_for('activities.detail', id=id))
    activity = db.get_or_404(RevenueActivity, id)
    p = db.get_or_404(ActivityParticipant, pid)
    # ... rest unchanged
```

**`delete_participant` (around line 507)** — add guard at the top:
```python
@activities_bp.route('/<int:id>/participants/<int:pid>/delete', methods=['POST'])
@login_required
def delete_participant(id, pid):
    if not current_user.is_superadmin:
        flash(tr('Non autorizzato.', 'Not authorized.'), 'error')
        return redirect(url_for('activities.detail', id=id))
    p = db.get_or_404(ActivityParticipant, pid)
    # ... rest unchanged
```

- [ ] **Step 1.4: Run the new tests to confirm they pass**

```bash
cd /opt/small_erp && python -m pytest tests/test_security.py::TestCostSubrouteAuth tests/test_security.py::TestParticipantSubrouteAuth -v
```

Expected: PASS (4 tests).

- [ ] **Step 1.5: Run full test suite to check for regressions**

```bash
cd /opt/small_erp && python -m pytest -q
```

Expected: 392 passed (388 + 4 new).

- [ ] **Step 1.6: Commit**

```bash
git add app/activities.py tests/test_security.py
git commit -m "fix(security): add superadmin guard to edit/delete cost and participant routes

Regular users could IDOR-access cost and participant mutation endpoints.
All four sub-routes now check current_user.is_superadmin and redirect
with an error flash if the check fails, consistent with add_cost and
add_participant which already had this guard."
```

---

## Task 2: Fix CSP — Remove Google Fonts external import

**Context:** `app/static/css/style.css` starts with:
```css
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:...');
```
The CSP in `app/__init__.py` sets `style-src 'self'` and `font-src 'self'`, blocking this external request silently. Fonts never load in production.

**Fix strategy:** Replace Google Fonts with a high-quality system font stack that matches the editorial Italian Finance aesthetic. No external requests, no CSP change needed.

**Files:**
- Modify: `app/static/css/style.css` — remove `@import`, update `--font-display`, `--font-body`, `--font-mono` variables

- [ ] **Step 2.1: Write a test for the CSP header correctness**

Add to `tests/test_security.py`:

```python
class TestCSPFonts:
    """CSS must not request fonts from external origins blocked by CSP."""

    def test_style_css_has_no_external_import(self):
        import os
        css_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'css', 'style.css')
        with open(css_path) as f:
            content = f.read()
        assert 'googleapis.com' not in content, "Google Fonts @import violates CSP style-src 'self'"
        assert 'gstatic.com' not in content, "Google Fonts gstatic violates CSP font-src 'self'"
```

- [ ] **Step 2.2: Run test to confirm it fails**

```bash
cd /opt/small_erp && python -m pytest tests/test_security.py::TestCSPFonts -v
```

Expected: FAIL.

- [ ] **Step 2.3: Remove Google Fonts import from CSS**

In `app/static/css/style.css`, replace line 6 (the `@import` line) and update the font variables in `:root`:

Remove:
```css
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;0,9..144,700;1,9..144,400&family=JetBrains+Mono:wght@400;500&display=swap');
```

Update these three variables inside `:root { }`:
```css
  /* Typography — system font stack, no external requests */
  --font-display: 'Georgia', 'Palatino Linotype', 'Book Antiqua', Palatino, serif;
  --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'SF Mono', 'Menlo', 'Cascadia Code', 'Consolas', monospace;
```

- [ ] **Step 2.4: Run the CSP test to confirm it passes**

```bash
cd /opt/small_erp && python -m pytest tests/test_security.py::TestCSPFonts -v
```

Expected: PASS.

- [ ] **Step 2.5: Run full test suite**

```bash
cd /opt/small_erp && python -m pytest -q
```

Expected: all pass.

- [ ] **Step 2.6: Commit**

```bash
git add app/static/css/style.css tests/test_security.py
git commit -m "fix(security): remove Google Fonts @import that violated CSP style-src 'self'

External font request was silently blocked by the existing CSP.
Replace with a curated system font stack (Georgia/system-ui/monospace)
that preserves the editorial aesthetic without external network calls.
Add a test to prevent regression."
```

---

## Task 3: Code quality — Clean up activities.py minor issues

**Files:**
- Modify: `app/activities.py` — `_can_modify_activity` signature, `edit_cost` error logging

- [ ] **Step 3.1: Fix `_can_modify_activity` unused parameter**

The function takes `activity` but never uses it. Change:

```python
def _can_modify_activity(activity):
    """Check if current user can modify the activity (superadmin only)."""
    return current_user.is_superadmin
```

to:

```python
def _can_modify_activity():
    return current_user.is_superadmin
```

Update the three call sites in the same file:
- `edit` route: `if not _can_modify_activity(activity):` → `if not _can_modify_activity():`
- `delete` route: `if not _can_modify_activity(activity):` → `if not _can_modify_activity():`
- `bulk_delete` route: `if not _can_modify_activity(activity):` → `if not _can_modify_activity():`

- [ ] **Step 3.2: Add missing error logging to `edit_cost`**

In `edit_cost`, the `except` block around line 379 only flashes but doesn't log:
```python
        except (ValueError, KeyError, InvalidOperation) as e:
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')
```

Change to:
```python
        except (ValueError, KeyError, InvalidOperation) as e:
            logger.error(f'Error editing cost {cost_id} on activity {id}: {str(e)}', exc_info=True)
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')
```

- [ ] **Step 3.3: Run full test suite**

```bash
cd /opt/small_erp && python -m pytest -q
```

Expected: all pass.

- [ ] **Step 3.4: Commit**

```bash
git add app/activities.py
git commit -m "refactor(activities): drop unused param from _can_modify_activity, add edit_cost error logging"
```

---

## Task 4: Code quality — Remove duplicate keys from calc_dashboard_stats

**File:**
- Modify: `app/services.py:532-543`

The return dict in `calc_dashboard_stats` has:
- `open_activities` AND `open_activities_count` (same value)
- `month_margin` AND `month_net_margin` (same value)

Keep the keys used in templates. Check which key names templates and tests use:

- [ ] **Step 4.1: Find which duplicate key names are used**

```bash
grep -rn "open_activities_count\|open_activities\b\|month_net_margin\|month_margin\b" \
  /opt/small_erp/app/templates/ /opt/small_erp/tests/ --include="*.html" --include="*.py"
```

- [ ] **Step 4.2: Remove unused duplicate keys**

Based on the grep output:
- Keep whichever key the templates/tests reference; remove the other.
- If both appear in templates/tests, pick the more descriptive one and update the other references to match.

Example outcome (verify against grep results):
```python
return {
    'open_activities': open_activities,          # remove open_activities_count
    'month_revenue': month_revenue,
    'month_costs': month_costs,
    'month_margin': month_margin,                # remove month_net_margin
    'recent_activities': recent_activities,
    'top_agents': top_agents,
    'current_month': current_month,
    'current_year': current_year,
}
```

- [ ] **Step 4.3: Run full test suite**

```bash
cd /opt/small_erp && python -m pytest -q
```

Expected: all pass. If tests fail citing a removed key, update templates/tests to use the kept key name.

- [ ] **Step 4.4: Commit**

```bash
git add app/services.py app/templates/dashboard.html tests/
git commit -m "refactor(services): remove duplicate return keys from calc_dashboard_stats"
```

---

## Task 5: Ops — Create .env.example

**Context:** README.md setup instructions say `cp .env.example .env` but this file does not exist.

**File:**
- Create: `.env.example`

- [ ] **Step 5.1: Create .env.example**

```bash
cat > /opt/small_erp/.env.example << 'EOF'
# ── Required ───────────────────────────────────────────────────────────────
# Generate with: python -c 'import secrets; print(secrets.token_hex(32))'
SECRET_KEY=change-me-generate-with-secrets-token-hex-32

# Superadmin password — never stored in DB, read at every login
SUPERADMIN_PASSWORD=change-me-min-12-chars-1Upper1digit

# SQLite database path (relative to project root)
DATABASE_PATH=instance/erp.db

# ── Optional ───────────────────────────────────────────────────────────────
# Log directory (default: logs/)
# LOG_DIR=logs

# Set true to enable Werkzeug debug mode — NEVER in production
# FLASK_DEBUG=false

# Set true to activate SESSION_COOKIE_SECURE and HSTS header (requires HTTPS)
# HTTPS_ENABLED=false

# Resend API key for email functionality (optional)
# RESEND_API_KEY=re_...
EOF
```

- [ ] **Step 5.2: Verify the file was created correctly**

```bash
cat /opt/small_erp/.env.example
```

Expected: file with all variables, comments, no real secrets.

- [ ] **Step 5.3: Confirm .env.example is NOT in .gitignore**

```bash
grep "env.example" /opt/small_erp/.gitignore
```

Expected: no output (`.env.example` should be tracked; `.env` is already gitignored).

- [ ] **Step 5.4: Commit**

```bash
git add .env.example
git commit -m "ops: add .env.example referenced in README setup instructions"
```

---

## Task 6: Ops — Remove inline styles from templates

**Context:** `app/templates/activities/detail.html` uses `style="padding-left:1.5rem;"` inline. The CSP `style-src 'self'` blocks inline styles in general, though Flask-WTF/Jinja2's HTML attribute styles are not blocked by `style-src` (only `<style>` tags and `javascript:` pseudo-URLs are). Still, removing them improves consistency and maintainability.

**Files:**
- Modify: `app/templates/activities/detail.html`
- Modify: `app/static/css/style.css` — add `.breakdown-row--indented` utility class

- [ ] **Step 6.1: Add utility class to CSS**

In `app/static/css/style.css`, add after the existing `.breakdown-row` rules:

```css
.breakdown-row--indented {
  padding-left: 1.5rem;
}
```

- [ ] **Step 6.2: Replace inline styles in detail.html**

Find the two occurrences of `style="padding-left:1.5rem;"` in `app/templates/activities/detail.html` and replace with `class="breakdown-row breakdown-row--indented"`.

For example, change:
```html
<div class="breakdown-row" style="padding-left:1.5rem;">
```
to:
```html
<div class="breakdown-row breakdown-row--indented">
```

(Applies to both the Internal Consultants and External Consultants rows.)

- [ ] **Step 6.3: Run full test suite**

```bash
cd /opt/small_erp && python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6.4: Commit**

```bash
git add app/templates/activities/detail.html app/static/css/style.css
git commit -m "style: replace inline padding with CSS utility class in activity detail template"
```

---

## Task 7: Final verification

- [ ] **Step 7.1: Run complete test suite with coverage**

```bash
cd /opt/small_erp && python -m pytest --cov=app --cov-report=term-missing -q
```

Expected: 392+ tests pass, no failures.

- [ ] **Step 7.2: Start server and do a quick smoke test**

```bash
cd /opt/small_erp && python run.py &
sleep 2
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/login
```

Expected: `200`

```bash
kill %1
```

- [ ] **Step 7.3: Verify no Google Fonts requests remain in CSS**

```bash
grep -n "googleapis\|gstatic" /opt/small_erp/app/static/css/style.css
```

Expected: no output.

- [ ] **Step 7.4: Verify all four sub-routes now have authorization guards**

```bash
grep -n "is_superadmin" /opt/small_erp/app/activities.py
```

Expected: lines in `edit_cost`, `delete_cost`, `edit_participant`, `delete_participant`, `add_cost`, `add_participant`.

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Task 1 covers the 4 IDOR routes (edit_cost, delete_cost, edit_participant, delete_participant)
- ✅ Task 2 covers CSP/Google Fonts violation
- ✅ Task 3 covers `_can_modify_activity` parameter and edit_cost logging
- ✅ Task 4 covers duplicate dict keys in `calc_dashboard_stats`
- ✅ Task 5 covers missing `.env.example`
- ✅ Task 6 covers inline styles
- ✅ Task 7 is final verification

**Placeholder scan:** No TBDs, TODOs, or "implement later" present. All code snippets are complete.

**Type consistency:** No type conflicts across tasks. All route changes are isolated guard additions; function signature change in Task 3 has all 3 call sites updated.

**What was NOT included** (deliberately out of scope):
- `audit_service.log_action` double-commit: current pattern is safe (business commits first, then audit). Changing it requires restructuring all 20+ callers and is a larger refactor that deserves its own plan.
- User full_name edit UI: feature addition, out of scope for bug/quality pass.
- `total_due` semantics: intentional product decision (shows timesheet cost only, not fixed+proportional), not a bug.
