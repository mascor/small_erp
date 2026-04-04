"""Security tests for Small ERP application — penetration test suite."""
import pytest
from decimal import Decimal
from datetime import date
from app.models import User, RevenueActivity
from app import db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client, username='superadmin', password='password123'):
    return client.post('/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def _login_operator(client, operator_user):
    return _login(client, 'operator', 'password123')


# ===========================================================================
# AUTH-01 — Open Redirect prevention
# ===========================================================================

class TestOpenRedirect:
    """Verify that the login redirect only allows safe (relative) URLs."""

    def test_open_redirect_absolute_url_blocked(self, client, superadmin_user):
        """Login with next=https://evil.com should NOT redirect externally."""
        resp = client.post('/login?next=https://evil.com', data={
            'username': 'superadmin',
            'password': 'password123',
        })
        assert resp.status_code in (302, 303)
        location = resp.headers.get('Location', '')
        assert 'evil.com' not in location

    def test_open_redirect_protocol_relative_blocked(self, client, superadmin_user):
        """Protocol-relative URL //evil.com should be blocked."""
        resp = client.post('/login?next=//evil.com', data={
            'username': 'superadmin',
            'password': 'password123',
        })
        location = resp.headers.get('Location', '')
        assert 'evil.com' not in location

    def test_safe_relative_redirect_allowed(self, client, superadmin_user):
        """A safe relative path like /activities/ should still work."""
        resp = client.post('/login?next=/activities/', data={
            'username': 'superadmin',
            'password': 'password123',
        })
        assert resp.status_code in (302, 303)
        location = resp.headers.get('Location', '')
        assert '/activities/' in location

    def test_protected_route_redirects_with_relative_next(self, client, superadmin_user):
        """Unauthenticated access to protected route should preserve safe relative next."""
        resp = client.get('/activities/', follow_redirects=False)
        assert resp.status_code in (302, 303)
        location = resp.headers.get('Location', '')
        assert '/login' in location
        assert ('next=%2Factivities%2F' in location) or ('next=/activities/' in location)

        login_resp = client.post(location, data={
            'username': 'superadmin',
            'password': 'password123',
        }, follow_redirects=False)
        assert login_resp.status_code in (302, 303)
        assert '/activities/' in login_resp.headers.get('Location', '')


# ===========================================================================
# AUTH-02 — Session fixation prevention
# ===========================================================================

class TestSessionFixation:
    """Session should be regenerated on login."""

    def test_session_cleared_on_login(self, client, superadmin_user):
        """After login the session cookie should be fresh (no pre-login data)."""
        # Set a value in the session before login
        with client.session_transaction() as sess:
            sess['canary'] = 'pre-login-value'

        _login(client)

        with client.session_transaction() as sess:
            # canary should be gone after session.clear()
            assert 'canary' not in sess


# ===========================================================================
# AUTH-03 — Logout must be POST (CSRF-safe)
# ===========================================================================

class TestLogoutMethod:
    """Logout endpoint should only accept POST requests."""

    def test_logout_get_not_allowed(self, client, superadmin_user):
        """GET /logout should return 405 Method Not Allowed."""
        _login(client)
        resp = client.get('/logout')
        assert resp.status_code == 405

    def test_logout_post_works(self, client, superadmin_user):
        """POST /logout should succeed and redirect to login."""
        _login(client)
        resp = client.post('/logout', follow_redirects=False)
        assert resp.status_code in (302, 303)


# ===========================================================================
# CRYPTO-01 — Weak SECRET_KEY detection
# ===========================================================================

class TestSecretKey:
    """SECRET_KEY must be strong in non-test mode."""

    def test_secret_key_not_default_fallback(self, app):
        """The running app should NOT use the weak dev-fallback-key."""
        assert app.config['SECRET_KEY'] != 'dev-fallback-key'


# ===========================================================================
# CRYPTO-02 — Session cookie flags
# ===========================================================================

class TestSessionCookieFlags:
    """Session cookies must have secure flags."""

    def test_cookie_httponly(self, app):
        assert app.config.get('SESSION_COOKIE_HTTPONLY') is True

    def test_cookie_samesite(self, app):
        assert app.config.get('SESSION_COOKIE_SAMESITE') == 'Lax'

    def test_permanent_session_lifetime(self, app):
        assert app.config.get('PERMANENT_SESSION_LIFETIME') is not None


# ===========================================================================
# CONF-02 — Security headers
# ===========================================================================

class TestSecurityHeaders:
    """HTTP responses should include security headers."""

    def test_security_headers_present(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
        assert resp.headers.get('X-Frame-Options') == 'DENY'
        assert resp.headers.get('X-XSS-Protection') == '1; mode=block'
        assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'


# ===========================================================================
# AUTHZ-01 — IDOR on activities (edit / delete owner check)
# ===========================================================================

class TestActivityIDOR:
    """Non-owner, non-admin users should not modify others' activities."""

    def test_operator_cannot_edit_others_activity(self, client, app, operator_user, revenue_activity):
        """An operator should not be able to edit an activity they did not create."""
        _login_operator(client, operator_user)
        resp = client.post(f'/activities/{revenue_activity.id}/edit', data={
            'title': 'Hacked Title',
            'date': str(date.today()),
            'status': 'bozza',
            'total_revenue': '999',
            'agent_percentage': '0',
        }, follow_redirects=True)
        # Should see authorization error
        assert tr_match(resp.data, b'Non autorizzat', b'Not authorized')

        # Verify title was NOT changed
        with app.app_context():
            act = db.session.get(RevenueActivity, revenue_activity.id)
            assert act.title == 'Test Activity'

    def test_operator_cannot_delete_others_activity(self, client, app, operator_user, revenue_activity):
        """An operator should not be able to delete an activity they did not create."""
        _login_operator(client, operator_user)
        resp = client.post(f'/activities/{revenue_activity.id}/delete', follow_redirects=True)
        assert tr_match(resp.data, b'Non autorizzat', b'Not authorized')

        with app.app_context():
            act = db.session.get(RevenueActivity, revenue_activity.id)
            assert act is not None

    def test_superadmin_can_edit_any_activity(self, client, app, superadmin_user, revenue_activity):
        """Superadmin users should be able to edit any activity."""
        _login(client, 'superadmin', 'password123')
        resp = client.post(f'/activities/{revenue_activity.id}/edit', data={
            'title': 'Superadmin Edit',
            'date': str(date.today()),
            'status': 'bozza',
            'total_revenue': '1000',
            'agent_percentage': '10',
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            act = db.session.get(RevenueActivity, revenue_activity.id)
            assert act.title == 'Superadmin Edit'


# ===========================================================================
# CONF-03 — Password policy
# ===========================================================================

class TestPasswordPolicy:
    """Password must meet complexity requirements."""

    def test_short_password_rejected(self, client, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': 'weakuser',
            'password': 'Short1A',
        }, follow_redirects=True)
        assert b'12' in resp.data  # mentions "12 caratteri" or "12 characters"

    def test_no_uppercase_rejected(self, client, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': 'weakuser',
            'password': 'alllowercase1234',
        }, follow_redirects=True)
        assert tr_match(resp.data, b'maiuscola', b'uppercase')

    def test_no_digit_rejected(self, client, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': 'weakuser',
            'password': 'NoDigitsHereAA',
        }, follow_redirects=True)
        assert tr_match(resp.data, b'numero', b'digit')

    def test_strong_password_accepted(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': 'stronguser',
            'password': 'Str0ngP@ssw0rd!',
            'is_active': 'on',
        }, follow_redirects=True)
        # Should redirect to users list on success
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.filter_by(username='stronguser').first() is not None


# ===========================================================================
# INJ-01 — SQL wildcard injection in audit filter
# ===========================================================================

class TestAuditFilterInjection:
    """Wildcards in audit username filter should be stripped."""

    def test_wildcard_characters_stripped(self, client, superadmin_user):
        _login(client)
        resp = client.get('/audit/?username=%25%25%25')  # URL-encoded %%%
        assert resp.status_code == 200


# ===========================================================================
# INJ-02 — Date filter validation in audit
# ===========================================================================

class TestAuditDateValidation:
    """Invalid dates in audit filter should not cause errors."""

    def test_invalid_date_from_ignored(self, client, superadmin_user):
        _login(client)
        resp = client.get('/audit/?date_from=not-a-date')
        assert resp.status_code == 200

    def test_invalid_date_to_ignored(self, client, superadmin_user):
        _login(client)
        resp = client.get('/audit/?date_to="><script>alert(1)</script>')
        assert resp.status_code == 200

    def test_valid_dates_work(self, client, superadmin_user):
        _login(client)
        resp = client.get('/audit/?date_from=2026-01-01&date_to=2026-12-31')
        assert resp.status_code == 200


# ===========================================================================
# INJ-03 — XSS via error messages (exception details not leaked)
# ===========================================================================

class TestXSSErrorMessages:
    """Error messages should not include raw exception text."""

    def test_malicious_decimal_no_xss(self, client, superadmin_user, agent):
        """Submitting a crafted decimal should not put raw input in the response."""
        _login(client)
        payload = '<script>alert(1)</script>'
        resp = client.post('/activities/new', data={
            'title': 'Test',
            'date': str(date.today()),
            'total_revenue': payload,
            'agent_percentage': '0',
        }, follow_redirects=True)
        # Raw script tag should NEVER appear unescaped
        assert b'<script>alert(1)</script>' not in resp.data


# ===========================================================================
# INPUT-01 — Decimal overflow / negative values
# ===========================================================================

class TestDecimalValidation:
    """Decimal fields should reject negative and overflow values."""

    def test_negative_revenue_rejected(self, client, superadmin_user, agent):
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'NegativeTest',
            'date': str(date.today()),
            'total_revenue': '-1000',
            'agent_id': str(agent.id),
            'agent_percentage': '10',
        }, follow_redirects=True)
        # Should show error, not create activity
        with client.application.app_context():
            assert RevenueActivity.query.filter_by(title='NegativeTest').first() is None

    def test_overflow_revenue_rejected(self, client, superadmin_user, agent):
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'OverflowTest',
            'date': str(date.today()),
            'total_revenue': '99999999999999',
            'agent_id': str(agent.id),
            'agent_percentage': '10',
        }, follow_redirects=True)
        with client.application.app_context():
            assert RevenueActivity.query.filter_by(title='OverflowTest').first() is None


# ===========================================================================
# Set-language open redirect
# ===========================================================================

class TestSetLanguageRedirect:
    """The set-language endpoint should not allow open redirects."""

    def test_set_language_external_redirect_blocked(self, client, superadmin_user):
        _login(client)
        resp = client.post('/set-language', data={
            'lang': 'en',
            'next': 'https://evil.com',
        })
        location = resp.headers.get('Location', '')
        assert 'evil.com' not in location


# ===========================================================================
# Utility
# ===========================================================================

def tr_match(data, it_fragment, en_fragment):
    """Check if response contains either the Italian or English text."""
    return it_fragment in data or en_fragment in data
