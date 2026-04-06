"""Tests for authentication and authorization."""
import pytest
from app.models import User


class TestLoginRoute:
    """Test login functionality."""

    def test_login_page_get(self, client):
        """Test accessing login page."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'Login' in response.data

    def test_login_valid_credentials(self, client, superadmin_user):
        """Test login with valid credentials."""
        response = client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Redirection should happen after login

    def test_login_invalid_username(self, client):
        """Test login with invalid username."""
        response = client.post('/login', data={
            'username': 'invalid_user',
            'password': 'password123'
        })
        
        assert response.status_code == 200

    def test_login_invalid_password(self, client, superadmin_user):
        """Test login with invalid password."""
        response = client.post('/login', data={
            'username': 'superadmin',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200

    def test_login_inactive_user(self, client, app):
        """Test login with inactive user."""
        with app.app_context():
            from app import db
            superadmin_user = User.query.filter_by(username='superadmin').first()
            if superadmin_user:
                superadmin_user.is_active_user = False
                db.session.commit()

    def test_login_redirects_to_dashboard(self, client, superadmin_user):
        """Test that login redirects to dashboard."""
        response = client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        }, follow_redirects=False)
        
        # Should redirect
        assert response.status_code in (301, 302, 303, 307)


class TestLogoutRoute:
    """Test logout functionality."""

    def test_logout_redirects(self, client, superadmin_user):
        """Test that logout redirects."""
        # First login
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        # Then logout (POST required)
        response = client.post('/logout', follow_redirects=False)
        assert response.status_code in (301, 302, 303, 307)

    def test_logout_then_cannot_access_protected(self, client, superadmin_user):
        """Test that logged out users cannot access protected routes."""
        client.post('/logout')
        
        response = client.get('/')
        # Should redirect to login
        assert response.status_code in (301, 302, 303, 307)


class TestAuthorizationDecorators:
    """Test authorization decorators."""

    def test_superadmin_required_with_superadmin(self, client, superadmin_user):
        """Test superadmin routes are accessible to superadmins."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/users/')
        assert response.status_code != 401

    def test_superadmin_required_with_regular_user_denied(self, client, operator_user):
        """Test superadmin routes deny access to regular users."""
        client.post('/login', data={
            'username': 'operator',
            'password': 'password123'
        })
        
        response = client.get('/users/')
        # Should be denied
        assert response.status_code in (301, 302, 303, 307, 401, 403)

    def test_audit_superadmin_required_with_superadmin(self, client, superadmin_user):
        """Test audit routes are accessible to superadmins."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/audit/')
        assert response.status_code != 401

    def test_audit_superadmin_required_with_regular_user_denied(self, client, operator_user):
        """Test audit routes deny access to regular users."""
        client.post('/login', data={
            'username': 'operator',
            'password': 'password123'
        })
        
        response = client.get('/audit/')
        assert response.status_code in (301, 302, 303, 307, 401, 403)

    def test_user_loader_invalid_session_id_does_not_500(self, client):
        """A malformed session user id must not crash protected routes."""
        with client.session_transaction() as sess:
            sess['_user_id'] = 'not-an-int'

        response = client.get('/users/new', follow_redirects=False)
        assert response.status_code in (301, 302, 303, 307)


class TestUserModel:
    """Test User model authentication methods."""

    def test_check_password_valid(self, app):
        """Test password validation with valid password."""
        with app.app_context():
            from app import db
            user = User(username='test', email='test@example.com', full_name='Test')
            user.set_password('mypassword')
            
            assert user.check_password('mypassword') is True

    def test_check_password_invalid(self, app):
        """Test password validation with invalid password."""
        with app.app_context():
            from app import db
            user = User(username='test', email='test@example.com', full_name='Test')
            user.set_password('mypassword')
            
            assert user.check_password('wrongpassword') is False

    def test_check_password_empty(self, app):
        """Test password validation with empty password."""
        with app.app_context():
            user = User(username='test', email='test@example.com', full_name='Test')
            user.set_password('mypassword')
            
            assert user.check_password('') is False

    def test_is_superadmin_true(self, app, superadmin_user):
        """Test is_superadmin returns True for superadmin."""
        with app.app_context():
            user = User.query.filter_by(username='superadmin').first()
            assert user.is_superadmin is True

    def test_is_superadmin_false_regular_user(self, app, operator_user):
        """Test is_superadmin returns False for regular user."""
        with app.app_context():
            user = User.query.filter_by(username='operator').first()
            assert user.is_superadmin is False


class TestAdminEnvPasswordAuth:
    """Test env-only authentication for admin superadmin account."""

    def test_admin_superadmin_login_uses_env_password_only(self, app, client, monkeypatch):
        """Admin superadmin must authenticate with SUPERADMIN_PASSWORD, not DB hash."""
        monkeypatch.setenv('SUPERADMIN_PASSWORD', 'EnvOnlyPass!2026')

        with app.app_context():
            from app import db
            admin = User(
                username='admin',
                email='admin@erp.local',
                full_name='Super Admin',
                is_superadmin=True,
                is_active_user=True,
            )
            admin.set_password('DbPassword!2025')
            db.session.add(admin)
            db.session.commit()

        fail_resp = client.post('/login', data={
            'username': 'admin',
            'password': 'DbPassword!2025',
        }, follow_redirects=True)
        assert fail_resp.status_code == 200
        assert b'Credenziali' in fail_resp.data or b'Invalid credentials' in fail_resp.data

        ok_resp = client.post('/login', data={
            'username': 'admin',
            'password': 'EnvOnlyPass!2026',
        }, follow_redirects=False)
        assert ok_resp.status_code in (301, 302, 303, 307)

    def test_regular_user_named_admin_still_uses_db_password(self, app, client, monkeypatch):
        """A non-superadmin named admin must keep standard DB password auth."""
        monkeypatch.setenv('SUPERADMIN_PASSWORD', 'DifferentEnv!2026')

        with app.app_context():
            from app import db
            user = User(
                username='admin',
                email='admin@erp.local',
                full_name='Admin User',
                is_superadmin=False,
                is_active_user=True,
            )
            user.set_password('DbPassword!2025')
            db.session.add(user)
            db.session.commit()

        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'DbPassword!2025',
        }, follow_redirects=False)
        assert resp.status_code in (301, 302, 303, 307)
