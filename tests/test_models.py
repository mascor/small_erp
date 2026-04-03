"""Tests for app.models module."""
import pytest
from decimal import Decimal
from datetime import datetime, date
from app.models import User, Agent, RevenueActivity, ActivityCost, ActivityParticipant, AuditLog


class TestUserModel:
    """Test User model and its methods."""

    def test_user_creation(self, app):
        """Test creating a new user."""
        with app.app_context():
            from app import db
            user = User(
                username='testuser',
                email='test@example.com',
                full_name='Test User',
                role='operatore'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.full_name == 'Test User'

    def test_set_password_and_check(self, app):
        """Test password hashing and validation."""
        with app.app_context():
            from app import db
            user = User(
                username='testuser',
                email='test@example.com',
                full_name='Test User'
            )
            user.set_password('mypassword')
            db.session.add(user)
            db.session.commit()
            
            assert user.check_password('mypassword') is True
            assert user.check_password('wrongpassword') is False

    def test_is_superadmin_property(self, app, superadmin_user):
        """Test is_superadmin property."""
        with app.app_context():
            assert superadmin_user.is_superadmin is True

    def test_is_admin_property_superadmin(self, app, superadmin_user):
        """Test is_admin property for superadmin."""
        with app.app_context():
            assert superadmin_user.is_admin is True

    def test_is_admin_property_admin(self, app, admin_user):
        """Test is_admin property for admin."""
        with app.app_context():
            assert admin_user.is_admin is True

    def test_is_admin_property_operator(self, app, operator_user):
        """Test is_admin property for operator."""
        with app.app_context():
            assert operator_user.is_admin is False

    def test_is_active_property(self, app, superadmin_user):
        """Test is_active property for Flask-Login compatibility."""
        with app.app_context():
            assert superadmin_user.is_active is True
            superadmin_user.is_active_user = False
            assert superadmin_user.is_active is False

    def test_user_repr(self, app, superadmin_user):
        """Test user string representation."""
        with app.app_context():
            assert repr(superadmin_user) == '<User superadmin>'


class TestAgentModel:
    """Test Agent model."""

    def test_agent_creation(self, app):
        """Test creating a new agent."""
        with app.app_context():
            from app import db
            agent = Agent(
                first_name='Mario Rossi',
                default_percentage=Decimal('15.50'),
                is_active=True
            )
            db.session.add(agent)
            db.session.commit()
            
            assert agent.id is not None
            assert agent.first_name == 'Mario Rossi'
            assert agent.default_percentage == Decimal('15.50')
            assert agent.is_active is True

    def test_agent_full_name_property(self, app, agent):
        """Test agent full_name property."""
        with app.app_context():
            assert agent.full_name == 'Mario Rossi'

    def test_agent_repr(self, app, agent):
        """Test agent string representation."""
        with app.app_context():
            assert repr(agent) == '<Agent Mario Rossi>'


class TestRevenueActivityModel:
    """Test RevenueActivity model."""

    def test_activity_creation(self, app, superadmin_user, agent):
        """Test creating a revenue activity."""
        with app.app_context():
            from app import db
            activity = RevenueActivity(
                title='Test Activity',
                description='Test Description',
                date=date.today(),
                status='bozza',
                total_revenue=Decimal('5000.00'),
                agent_id=agent.id,
                agent_percentage=Decimal('10.00'),
                created_by=superadmin_user.id
            )
            db.session.add(activity)
            db.session.commit()
            
            assert activity.id is not None
            assert activity.title == 'Test Activity'
            assert activity.status == 'bozza'
            assert activity.total_revenue == Decimal('5000.00')

    def test_activity_status_label(self, app, revenue_activity):
        """Test activity status label property."""
        with app.app_context():
            assert revenue_activity.status_label == 'Bozza'
            revenue_activity.status = 'confermata'
            assert revenue_activity.status_label == 'Confermata'
            revenue_activity.status = 'chiusa'
            assert revenue_activity.status_label == 'Chiusa'

    def test_activity_other_status_label(self, app, revenue_activity):
        """Test activity status label for unknown status."""
        with app.app_context():
            revenue_activity.status = 'unknown'
            assert revenue_activity.status_label == 'unknown'

    def test_activity_cascade_delete_costs(self, app, revenue_activity, activity_cost):
        """Test that deleting activity cascades to costs."""
        with app.app_context():
            from app import db
            activity_id = revenue_activity.id
            cost_id = activity_cost.id
            
            # Delete activity
            db.session.delete(revenue_activity)
            db.session.commit()
            
            # Cost should be deleted too
            cost = ActivityCost.query.get(cost_id)
            assert cost is None

    def test_activity_cascade_delete_participants(self, app, revenue_activity, activity_participant):
        """Test that deleting activity cascades to participants."""
        with app.app_context():
            from app import db
            participant_id = activity_participant.id
            
            db.session.delete(revenue_activity)
            db.session.commit()
            
            participant = ActivityParticipant.query.get(participant_id)
            assert participant is None

    def test_activity_repr(self, app, revenue_activity):
        """Test activity string representation."""
        with app.app_context():
            assert repr(revenue_activity) == '<RevenueActivity Test Activity>'


class TestActivityCostModel:
    """Test ActivityCost model."""

    def test_cost_creation(self, app, revenue_activity):
        """Test creating an activity cost."""
        with app.app_context():
            from app import db
            cost = ActivityCost(
                activity_id=revenue_activity.id,
                category='trasporto',
                description='Fuel and transport',
                amount=Decimal('250.75'),
                date=date.today(),
                cost_type='operativo'
            )
            db.session.add(cost)
            db.session.commit()
            
            assert cost.id is not None
            assert cost.category == 'trasporto'
            assert cost.amount == Decimal('250.75')
            assert cost.cost_type == 'operativo'

    def test_cost_extra_type(self, app, revenue_activity):
        """Test creating an extra cost."""
        with app.app_context():
            from app import db
            cost = ActivityCost(
                activity_id=revenue_activity.id,
                category='altro',
                description='Extra expense',
                amount=Decimal('50.00'),
                cost_type='extra'
            )
            db.session.add(cost)
            db.session.commit()
            
            assert cost.cost_type == 'extra'

    def test_cost_repr(self, app, activity_cost):
        """Test cost string representation."""
        with app.app_context():
            assert repr(activity_cost) == '<ActivityCost Test Material 100.00>'


class TestActivityParticipantModel:
    """Test ActivityParticipant model."""

    def test_participant_creation(self, app, revenue_activity, operator_user):
        """Test creating an activity participant."""
        with app.app_context():
            from app import db
            participant = ActivityParticipant(
                activity_id=revenue_activity.id,
                participant_name='John Developer',
                user_id=operator_user.id,
                role_description='Senior Developer',
                work_share=Decimal('75.00'),
                fixed_compensation=Decimal('500.00')
            )
            db.session.add(participant)
            db.session.commit()
            
            assert participant.id is not None
            assert participant.participant_name == 'John Developer'
            assert participant.work_share == Decimal('75.00')
            assert participant.fixed_compensation == Decimal('500.00')

    def test_participant_without_user(self, app, revenue_activity):
        """Test creating participant without linked user."""
        with app.app_context():
            from app import db
            participant = ActivityParticipant(
                activity_id=revenue_activity.id,
                participant_name='External Contractor',
                work_share=Decimal('50.00'),
                fixed_compensation=Decimal('300.00')
            )
            db.session.add(participant)
            db.session.commit()
            
            assert participant.user_id is None

    def test_participant_repr(self, app, activity_participant):
        """Test participant string representation."""
        with app.app_context():
            assert repr(activity_participant) == '<ActivityParticipant Test Participant>'


class TestAuditLogModel:
    """Test AuditLog model."""

    def test_audit_log_creation(self, app, superadmin_user):
        """Test creating an audit log entry."""
        with app.app_context():
            from app import db
            log = AuditLog(
                user_id=superadmin_user.id,
                username=superadmin_user.username,
                timestamp=datetime.utcnow(),
                action_type='create',
                entity_type='Agent',
                entity_id=1,
                description='Created new agent'
            )
            db.session.add(log)
            db.session.commit()
            
            assert log.id is not None
            assert log.action_type == 'create'
            assert log.entity_type == 'Agent'
            assert log.username == 'superadmin'

    def test_audit_log_with_values(self, app, superadmin_user):
        """Test audit log with old and new values."""
        with app.app_context():
            from app import db
            log = AuditLog(
                user_id=superadmin_user.id,
                username=superadmin_user.username,
                timestamp=datetime.utcnow(),
                action_type='update',
                entity_type='Agent',
                entity_id=1,
                description='Agent updated',
                old_values='{"percentage": "10.00"}',
                new_values='{"percentage": "15.00"}'
            )
            db.session.add(log)
            db.session.commit()
            
            assert log.old_values == '{"percentage": "10.00"}'
            assert log.new_values == '{"percentage": "15.00"}'
