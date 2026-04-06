import pytest

import init_db
from app import db
from app.models import User


@pytest.mark.unit
@pytest.mark.auth
def test_init_creates_admin_without_storing_env_password(app, monkeypatch):
    """init_db must create admin and avoid storing the env password hash in DB."""
    monkeypatch.setattr(init_db, 'create_app', lambda: app)
    monkeypatch.setenv('SUPERADMIN_PASSWORD', 'EnvPassword!2026')

    init_db.init()

    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.is_superadmin is True
        assert admin.check_password('EnvPassword!2026') is False


@pytest.mark.unit
@pytest.mark.auth
def test_init_replaces_existing_admin_password_hash(app, monkeypatch):
    """init_db must replace any existing admin hash with a non-env placeholder."""
    monkeypatch.setattr(init_db, 'create_app', lambda: app)
    monkeypatch.setenv('SUPERADMIN_PASSWORD', 'FreshPassword!2026')

    with app.app_context():
        admin = User(
            username='admin',
            email='admin@erp.local',
            full_name='Super Admin',
            is_superadmin=True,
            is_active_user=True,
        )
        admin.set_password('OldPassword!2025')
        db.session.add(admin)
        db.session.commit()

    init_db.init()

    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.check_password('FreshPassword!2026') is False
        assert admin.check_password('OldPassword!2025') is False