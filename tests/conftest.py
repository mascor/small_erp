"""Pytest configuration and shared fixtures."""
import pytest
import os
import tempfile
from datetime import datetime, date
from decimal import Decimal

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import User, Agent, RevenueActivity, ActivityCost, ActivityParticipant, AuditLog


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create temp database
    db_fd, db_path = tempfile.mkstemp()

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-only-insecure-key-not-for-production',
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def app_context(app):
    """Application context."""
    with app.app_context():
        yield app


@pytest.fixture
def db_session(app):
    """Database session."""
    with app.app_context():
        yield db
        db.session.rollback()


@pytest.fixture
def get_user(app):
    """Helper fixture to get user by username."""
    def _get_user(username):
        with app.app_context():
            return User.query.filter_by(username=username).first()
    return _get_user


@pytest.fixture
def get_agent(app):
    """Helper fixture to get agent by ID."""
    def _get_agent(agent_id):
        with app.app_context():
            return Agent.query.get(agent_id)
    return _get_agent


@pytest.fixture
def get_activity(app):
    """Helper fixture to get activity by ID."""
    def _get_activity(activity_id):
        with app.app_context():
            return RevenueActivity.query.get(activity_id)
    return _get_activity


@pytest.fixture
def superadmin_user(app):
    """Create a superadmin user."""
    with app.app_context():
        user = User(
            username='superadmin',
            email='superadmin@test.com',
            full_name='Super Admin',
            role='superadmin'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    with app.app_context():
        return User.query.get(user_id)


@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    with app.app_context():
        user = User(
            username='admin',
            email='admin@test.com',
            full_name='Admin User',
            role='admin'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    with app.app_context():
        return User.query.get(user_id)


@pytest.fixture
def operator_user(app):
    """Create a regular operator user."""
    with app.app_context():
        user = User(
            username='operator',
            email='operator@test.com',
            full_name='Operator User',
            role='operatore'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    with app.app_context():
        return User.query.get(user_id)


@pytest.fixture
def agent(app):
    """Create a test agent."""
    with app.app_context():
        agent_obj = Agent(
            first_name='Mario',
            last_name='Rossi',
            default_percentage=Decimal('10.00'),
            is_active=True,
            notes='Test agent'
        )
        db.session.add(agent_obj)
        db.session.commit()
        agent_id = agent_obj.id
    
    with app.app_context():
        return Agent.query.get(agent_id)


@pytest.fixture
def revenue_activity(app, superadmin_user, agent):
    """Create a test revenue activity."""
    with app.app_context():
        activity = RevenueActivity(
            title='Test Activity',
            description='Test Description',
            date=date.today(),
            status='bozza',
            total_revenue=Decimal('1000.00'),
            agent_id=agent.id,
            agent_percentage=Decimal('10.00'),
            created_by=superadmin_user.id
        )
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id
    
    with app.app_context():
        return RevenueActivity.query.get(activity_id)


@pytest.fixture
def activity_cost(app, revenue_activity):
    """Create a test activity cost."""
    with app.app_context():
        cost = ActivityCost(
            activity_id=revenue_activity.id,
            category='materiale',
            description='Test Material',
            amount=Decimal('100.00'),
            date=date.today(),
            cost_type='operativo'
        )
        db.session.add(cost)
        db.session.commit()
        cost_id = cost.id
    
    with app.app_context():
        return ActivityCost.query.get(cost_id)


@pytest.fixture
def activity_participant(app, revenue_activity, operator_user):
    """Create a test activity participant."""
    with app.app_context():
        participant = ActivityParticipant(
            activity_id=revenue_activity.id,
            participant_name='Test Participant',
            user_id=operator_user.id,
            role_description='Developer',
            work_share=Decimal('50.00'),
            fixed_compensation=Decimal('200.00')
        )
        db.session.add(participant)
        db.session.commit()
        participant_id = participant.id
    
    with app.app_context():
        return ActivityParticipant.query.get(participant_id)


@pytest.fixture
def audit_log(app, superadmin_user):
    """Create a test audit log."""
    with app.app_context():
        log = AuditLog(
            user_id=superadmin_user.id,
            username=superadmin_user.username,
            timestamp=datetime.utcnow(),
            action_type='create',
            entity_type='User',
            entity_id=1,
            description='Test audit log',
            old_values=None,
            new_values='{"username": "testuser", "role": "operatore"}'
        )
        db.session.add(log)
        db.session.commit()
        log_id = log.id
    
    with app.app_context():
        return AuditLog.query.get(log_id)
