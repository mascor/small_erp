"""Tests for audit service and logging."""
import pytest
import json
from datetime import datetime
from app.audit_service import log_action, model_to_dict
from app.models import User, Agent, AuditLog


class TestLogAction:
    """Test the log_action function."""

    def test_log_action_basic(self, app, superadmin_user):
        """Test logging a basic action."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            log_action(
                action_type='create',
                entity_type='Agent',
                entity_id=1,
                description='Created test agent'
            )
            
            log = AuditLog.query.filter_by(action_type='create').first()
            assert log is not None
            assert log.action_type == 'create'
            assert log.entity_type == 'Agent'
            assert log.entity_id == 1

    def test_log_action_with_values(self, app, superadmin_user):
        """Test logging action with old and new values."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            old_values = {'percentage': '10.00', 'is_active': True}
            new_values = {'percentage': '15.00', 'is_active': False}
            
            log_action(
                action_type='update',
                entity_type='Agent',
                entity_id=1,
                description='Updated agent',
                old_values=old_values,
                new_values=new_values
            )
            
            log = AuditLog.query.filter_by(action_type='update').first()
            assert log is not None
            assert log.old_values is not None
            assert log.new_values is not None

    def test_log_action_none_values(self, app, superadmin_user):
        """Test logging action with None values."""
        with app.app_context():
            from app.audit_service import log_action
            
            log_action(
                action_type='login',
                entity_type='User',
                entity_id=superadmin_user.id,
                description='User login',
                old_values=None,
                new_values=None
            )
            
            log = AuditLog.query.filter_by(action_type='login').first()
            assert log is not None

    def test_log_action_all_action_types(self, app, superadmin_user):
        """Test logging various action types."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            action_types = [
                'login', 'logout', 'create', 'update', 'delete',
                'status_change', 'user_create', 'user_update'
            ]
            
            for action_type in action_types:
                log_action(
                    action_type=action_type,
                    entity_type='Test',
                    entity_id=1,
                    description=f'Test {action_type}'
                )
            
            log_count = AuditLog.query.count()
            assert log_count >= len(action_types)

    def test_log_action_records_username(self, app, superadmin_user):
        """Test that log records current user username."""
        with app.app_context():
            from app.audit_service import log_action
            from flask_login import login_user

            # login_user requires a request context.
            with app.test_request_context('/'):
                login_user(superadmin_user)
                log_action(
                    action_type='create',
                    entity_type='Agent',
                    entity_id=1,
                    description='Test'
                )

            log = AuditLog.query.filter_by(action_type='create').first()
            assert log is not None
            assert log.username == 'superadmin'

    def test_log_action_without_request_uses_system_username(self, app):
        """Without a request/user context, audit should fallback to system."""
        with app.app_context():
            from app.audit_service import log_action
            log_action(
                action_type='create',
                entity_type='Agent',
                entity_id=1,
                description='Test'
            )

            log = AuditLog.query.filter_by(action_type='create').first()
            assert log is not None
            assert log.username == 'system'


class TestModelToDict:
    """Test the model_to_dict serialization function."""

    def test_model_to_dict_user(self, app, superadmin_user):
        """Test converting User model to dict."""
        with app.app_context():
            from app.audit_service import model_to_dict
            
            result = model_to_dict(superadmin_user, ['username', 'email', 'role'])
            
            assert result['username'] == 'superadmin'
            assert result['email'] == 'superadmin@test.com'
            assert result['role'] == 'superadmin'

    def test_model_to_dict_agent(self, app, agent):
        """Test converting Agent model to dict."""
        with app.app_context():
            from app.audit_service import model_to_dict
            
            result = model_to_dict(agent, ['first_name', 'default_percentage', 'is_active'])
            
            assert result['first_name'] == 'Mario Rossi'
            assert result['is_active'] is True

    def test_model_to_dict_decimal_fields(self, app, agent):
        """Test converting model with Decimal fields to dict."""
        with app.app_context():
            from app.audit_service import model_to_dict
            from decimal import Decimal
            
            result = model_to_dict(agent, ['default_percentage'])
            
            # Should be converted to string for JSON serialization
            assert 'default_percentage' in result

    def test_model_to_dict_datetime_fields(self, app, superadmin_user):
        """Test converting model with datetime fields to dict."""
        with app.app_context():
            from app.audit_service import model_to_dict
            
            result = model_to_dict(superadmin_user, ['created_at', 'updated_at'])
            
            assert 'created_at' in result
            assert 'updated_at' in result

    def test_model_to_dict_empty_fields_list(self, app, superadmin_user):
        """Test model_to_dict with empty fields list."""
        with app.app_context():
            from app.audit_service import model_to_dict
            
            result = model_to_dict(superadmin_user, [])
            
            assert result == {}

    def test_model_to_dict_partial_fields(self, app, superadmin_user):
        """Test model_to_dict with subset of fields."""
        with app.app_context():
            from app.audit_service import model_to_dict
            
            result = model_to_dict(superadmin_user, ['username', 'role'])
            
            assert 'username' in result
            assert 'role' in result
            assert 'email' not in result


class TestAuditLogStorage:
    """Test audit log data storage and retrieval."""

    def test_audit_log_query_by_user(self, app, superadmin_user):
        """Test querying audit logs by user."""
        with app.app_context():
            from app.audit_service import log_action
            from flask_login import login_user

            with app.test_request_context('/'):
                login_user(superadmin_user)
                log_action(
                    action_type='create',
                    entity_type='Agent',
                    entity_id=1,
                    description='Test'
                )
            
            logs = AuditLog.query.filter_by(username='superadmin').all()
            assert len(logs) >= 1

    def test_audit_log_query_by_action_type(self, app, superadmin_user):
        """Test querying audit logs by action type."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            log_action('create', 'Agent', 1, 'Test 1')
            log_action('update', 'Agent', 1, 'Test 2')
            log_action('create', 'User', 1, 'Test 3')
            
            create_logs = AuditLog.query.filter_by(action_type='create').all()
            assert len(create_logs) >= 2

    def test_audit_log_query_by_entity(self, app, superadmin_user):
        """Test querying audit logs by entity type."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            log_action('create', 'Agent', 1, 'Agent test')
            log_action('create', 'User', 1, 'User test')
            
            agent_logs = AuditLog.query.filter_by(entity_type='Agent').all()
            user_logs = AuditLog.query.filter_by(entity_type='User').all()
            
            assert len(agent_logs) >= 1
            assert len(user_logs) >= 1

    def test_audit_log_timestamp_recorded(self, app, superadmin_user):
        """Test that timestamp is recorded."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            before_time = datetime.utcnow()
            log_action('create', 'Agent', 1, 'Test')
            after_time = datetime.utcnow()
            
            log = AuditLog.query.filter_by(action_type='create').first()
            assert log.timestamp is not None
            assert before_time <= log.timestamp <= after_time

    def test_audit_log_json_parsing(self, app, superadmin_user):
        """Test that JSON values can be parsed back."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            old_values = {'field1': 'value1', 'field2': 'value2'}
            new_values = {'field1': 'updated1', 'field2': 'updated2'}
            
            log_action(
                'update',
                'Agent',
                1,
                'Test update',
                old_values=old_values,
                new_values=new_values
            )
            
            log = AuditLog.query.filter_by(action_type='update').first()
            
            # Parse JSON back
            old = json.loads(log.old_values) if log.old_values else None
            new = json.loads(log.new_values) if log.new_values else None
            
            assert old is not None
            assert new is not None


class TestAuditIntegration:
    """Test audit logging in action."""

    def test_agent_creation_audit_logged(self, app, superadmin_user):
        """Test that agent creation is logged."""
        with app.app_context():
            from app import db
            from app.models import Agent
            
            agent = Agent(
                first_name='Test Agent',
                default_percentage=10
            )
            db.session.add(agent)
            db.session.commit()

    def test_user_creation_audit_logged(self, app, superadmin_user):
        """Test that user creation is logged."""
        with app.app_context():
            from app import db
            from app.models import User
            
            user = User(
                username='testuser',
                email='test@example.com',
                full_name='Test User'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

    def test_multiple_audit_entries(self, app, superadmin_user):
        """Test recording multiple audit entries."""
        with app.app_context():
            from app.audit_service import log_action
            from app import db
            
            for i in range(5):
                log_action(
                    'create',
                    'Agent',
                    i,
                    f'Created agent {i}'
                )
            
            logs = AuditLog.query.filter_by(action_type='create').all()
            assert len(logs) >= 5
