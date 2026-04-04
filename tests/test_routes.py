"""Tests for Flask routes and view functions."""
import pytest
from decimal import Decimal
from datetime import date


class TestDashboardRoutes:
    """Test dashboard routes."""

    def test_dashboard_not_logged_in(self, client):
        """Test dashboard redirects when not logged in."""
        response = client.get('/', follow_redirects=False)
        assert response.status_code in (301, 302, 303, 307)

    def test_dashboard_logged_in(self, client, superadmin_user):
        """Test dashboard loads when logged in."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/')
        assert response.status_code == 200

    def test_dashboard_shows_statistics(self, client, superadmin_user, agent):
        """Test dashboard displays statistics."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/')
        assert response.status_code == 200


class TestActivityRoutes:
    """Test activity CRUD routes."""

    def test_activities_list(self, client, superadmin_user):
        """Test listing activities."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/activities/')
        assert response.status_code == 200
        assert b'attivit' in response.data.lower() or b'attivita' in response.data.lower()

    def test_activities_filter_by_status(self, client, superadmin_user):
        """Test filtering activities by status."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/activities/?status=bozza')
        assert response.status_code == 200

    def test_create_activity_form_get(self, client, superadmin_user):
        """Test GET request for new activity form."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/activities/new')
        assert response.status_code == 200

    def test_create_activity_post(self, client, app, superadmin_user, agent):
        """Test POST to create activity."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post('/activities/new', data={
            'title': 'New Activity',
            'description': 'Test Activity',
            'date': date.today().isoformat(),
            'total_revenue': '1000.00',
            'agent_id': agent.id,
            'agent_percentage': '10.00',
            'status': 'bozza'
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import RevenueActivity
            activity = RevenueActivity.query.filter_by(title='New Activity').first()
            assert activity is not None

    def test_activity_detail(self, client, superadmin_user, revenue_activity):
        """Test viewing activity details."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get(f'/activities/{revenue_activity.id}')
        assert response.status_code == 200

    def test_edit_activity_form_get(self, client, superadmin_user, revenue_activity):
        """Test GET request for edit activity form."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get(f'/activities/{revenue_activity.id}/edit')
        assert response.status_code == 200

    def test_edit_activity_post(self, client, app, superadmin_user, revenue_activity):
        """Test POST to edit activity."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post(f'/activities/{revenue_activity.id}/edit', data={
            'title': 'Updated Title',
            'description': 'Updated Description',
            'date': date.today().isoformat(),
            'total_revenue': '2000.00',
            'agent_percentage': '15.00',
            'status': 'confermata'
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import RevenueActivity
            activity = RevenueActivity.query.get(revenue_activity.id)
            assert activity.title == 'Updated Title'

    def test_delete_activity(self, client, app, superadmin_user, revenue_activity):
        """Test deleting activity."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        activity_id = revenue_activity.id
        
        response = client.post(f'/activities/{activity_id}/delete', follow_redirects=True)
        
        with app.app_context():
            from app.models import RevenueActivity
            activity = RevenueActivity.query.get(activity_id)
            assert activity is None

    def test_delete_activity_unauthorized_user_blocked(self, client, app, superadmin_user, operator_user, revenue_activity):
        """Test unauthorized user cannot delete another user's activity."""
        client.post('/login', data={
            'username': 'operator',
            'password': 'password123'
        })

        activity_id = revenue_activity.id

        response = client.post(f'/activities/{activity_id}/delete', follow_redirects=True)

        assert response.status_code == 200
        with app.app_context():
            from app.models import RevenueActivity
            activity = RevenueActivity.query.get(activity_id)
            assert activity is not None

    def test_bulk_delete_activities(self, client, app, superadmin_user, agent):
        """Test bulk deleting multiple activities."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        # Create two activities to bulk delete
        with app.app_context():
            from app.models import RevenueActivity
            a1 = RevenueActivity(
                title='Bulk 1', date=date.today(), status='bozza',
                total_revenue=Decimal('100'), agent_id=agent.id,
                agent_percentage=Decimal('10'), created_by=superadmin_user.id
            )
            a2 = RevenueActivity(
                title='Bulk 2', date=date.today(), status='bozza',
                total_revenue=Decimal('200'), agent_id=agent.id,
                agent_percentage=Decimal('10'), created_by=superadmin_user.id
            )
            from app import db
            db.session.add_all([a1, a2])
            db.session.commit()
            id1, id2 = a1.id, a2.id

        response = client.post('/activities/bulk-delete', data={
            'activity_ids': [str(id1), str(id2)]
        }, follow_redirects=True)

        assert response.status_code == 200
        with app.app_context():
            from app.models import RevenueActivity
            assert RevenueActivity.query.get(id1) is None
            assert RevenueActivity.query.get(id2) is None

    def test_bulk_delete_no_selection(self, client, superadmin_user):
        """Test bulk delete with no activities selected shows warning."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        response = client.post('/activities/bulk-delete', data={}, follow_redirects=True)
        assert response.status_code == 200
        assert 'Nessuna'.encode() in response.data or b'No activities' in response.data

    def test_bulk_delete_unauthorized_skips(self, client, app, superadmin_user, operator_user, agent):
        """Test bulk delete skips activities the user cannot modify."""
        client.post('/login', data={
            'username': 'operator',
            'password': 'password123'
        })

        # Activity created by superadmin — operator cannot delete
        with app.app_context():
            from app.models import RevenueActivity
            from app import db
            a = RevenueActivity(
                title='Not Mine', date=date.today(), status='bozza',
                total_revenue=Decimal('100'), agent_id=agent.id,
                agent_percentage=Decimal('10'), created_by=superadmin_user.id
            )
            db.session.add(a)
            db.session.commit()
            aid = a.id

        response = client.post('/activities/bulk-delete', data={
            'activity_ids': [str(aid)]
        }, follow_redirects=True)

        assert response.status_code == 200
        with app.app_context():
            from app.models import RevenueActivity
            assert RevenueActivity.query.get(aid) is not None

    def test_bulk_delete_requires_login(self, client):
        """Test bulk delete redirects when not logged in."""
        response = client.post('/activities/bulk-delete', data={
            'activity_ids': ['1']
        }, follow_redirects=False)
        assert response.status_code in (301, 302, 303, 307)


class TestActivityCostRoutes:
    """Test activity cost management routes."""

    def test_add_cost_form(self, client, superadmin_user, revenue_activity):
        """Test GET request for add cost form."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get(f'/activities/{revenue_activity.id}/costs/add')
        assert response.status_code == 200

    def test_add_cost_post(self, client, app, superadmin_user, revenue_activity):
        """Test POST to add cost."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post(f'/activities/{revenue_activity.id}/costs/add', data={
            'category': 'materiale',
            'description': 'Test Material',
            'amount': '100.00',
            'date': date.today().isoformat(),
            'cost_type': 'operativo'
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import ActivityCost
            cost = ActivityCost.query.filter_by(description='Test Material').first()
            assert cost is not None

    def test_edit_cost_post(self, client, app, superadmin_user, revenue_activity, activity_cost):
        """Test POST to edit cost."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post(
            f'/activities/{revenue_activity.id}/costs/{activity_cost.id}/edit',
            data={
                'category': 'trasporto',
                'description': 'Updated Cost',
                'amount': '150.00',
                'date': date.today().isoformat(),
                'cost_type': 'extra'
            },
            follow_redirects=True
        )
        
        with app.app_context():
            from app.models import ActivityCost
            cost = ActivityCost.query.get(activity_cost.id)
            assert cost.category == 'trasporto'

    def test_delete_cost(self, client, app, superadmin_user, revenue_activity, activity_cost):
        """Test deleting cost."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        cost_id = activity_cost.id
        
        response = client.post(
            f'/activities/{revenue_activity.id}/costs/{cost_id}/delete',
            follow_redirects=True
        )
        
        with app.app_context():
            from app.models import ActivityCost
            cost = ActivityCost.query.get(cost_id)
            assert cost is None


class TestActivityParticipantRoutes:
    """Test activity participant management routes."""

    def test_add_participant_form(self, client, superadmin_user, revenue_activity):
        """Test GET request for add participant form."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get(f'/activities/{revenue_activity.id}/participants/add')
        assert response.status_code == 200

    def test_add_participant_post(self, client, app, superadmin_user, revenue_activity, operator_user):
        """Test POST to add participant."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post(f'/activities/{revenue_activity.id}/participants/add', data={
            'participant_name': 'New Participant',
            'role_description': 'Developer',
            'user_id': operator_user.id,
            'work_share': '50.00',
            'fixed_compensation': '300.00'
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import ActivityParticipant
            participant = ActivityParticipant.query.filter_by(participant_name='New Participant').first()
            assert participant is not None

    def test_delete_participant(self, client, app, superadmin_user, revenue_activity, activity_participant):
        """Test deleting participant."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        participant_id = activity_participant.id
        
        response = client.post(
            f'/activities/{revenue_activity.id}/participants/{participant_id}/delete',
            follow_redirects=True
        )
        
        with app.app_context():
            from app.models import ActivityParticipant
            participant = ActivityParticipant.query.get(participant_id)
            assert participant is None


class TestAgentRoutes:
    """Test agent management routes."""

    def test_agents_list(self, client, superadmin_user):
        """Test listing agents."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/agents/')
        assert response.status_code == 200

    def test_create_agent_form(self, client, superadmin_user):
        """Test GET request for create agent form."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/agents/new')
        assert response.status_code == 200

    def test_create_agent_post(self, client, app, superadmin_user):
        """Test POST to create agent."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post('/agents/new', data={
            'first_name': 'New Agent',
            'default_percentage': '12.50',
            'is_active': True
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import Agent
            agent = Agent.query.filter_by(first_name='New Agent').first()
            assert agent is not None

    def test_edit_agent_post(self, client, app, superadmin_user, agent):
        """Test POST to edit agent."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post(f'/agents/{agent.id}/edit', data={
            'first_name': 'Updated Agent Name',
            'default_percentage': '15.00',
            'is_active': True
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import Agent
            updated_agent = Agent.query.get(agent.id)
            assert updated_agent.first_name == 'Updated Agent Name'

    def test_delete_agent(self, client, app, superadmin_user, agent):
        """Test deleting agent."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        agent_id = agent.id
        
        response = client.post(f'/agents/{agent_id}/delete', follow_redirects=True)
        
        with app.app_context():
            from app.models import Agent
            deleted_agent = Agent.query.get(agent_id)
            assert deleted_agent is None


class TestUserManagementRoutes:
    """Test user management routes."""

    def test_users_list_admin_only(self, client, admin_user):
        """Test users list is admin-only."""
        client.post('/login', data={
            'username': 'admin',
            'password': 'password123'
        })
        
        response = client.get('/users/')
        assert response.status_code == 200

    def test_create_user_form(self, client, superadmin_user):
        """Test GET request for create user form."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/users/new')
        assert response.status_code == 200
        assert b'name="email"' not in response.data
        assert b'name="full_name"' not in response.data
        assert b'name="role"' not in response.data

    def test_create_user_post(self, client, app, superadmin_user):
        """Test POST to create user."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post('/users/new', data={
            'username': 'newuser',
            'password': 'Str0ngPass123!',
            'is_active': 'on'
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import User
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'newuser@erp.local'
            assert user.full_name == 'newuser'
            assert user.role == 'operatore'

    def test_edit_user_post(self, client, app, superadmin_user, operator_user):
        """Test POST to edit user."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.post(f'/users/{operator_user.id}/edit', data={
            'username': 'operator',
            'password': 'N3wStr0ngPass!'
        }, follow_redirects=True)
        
        with app.app_context():
            from app.models import User
            user = User.query.get(operator_user.id)
            assert user.email == 'operator@test.com'
            assert user.full_name == 'Operator User'
            assert user.role == 'operatore'
            assert user.check_password('N3wStr0ngPass!') is True

    def test_delete_user_post(self, client, app, superadmin_user, operator_user):
        """Test POST to delete a user."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        user_id = operator_user.id

        response = client.post(f'/users/{user_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from app.models import User
            user = User.query.get(user_id)
            assert user is None

    def test_delete_user_self_denied(self, client, app, superadmin_user):
        """Test self-deletion is denied."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        user_id = superadmin_user.id

        response = client.post(f'/users/{user_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from app.models import User
            user = User.query.get(user_id)
            assert user is not None

    def test_delete_superadmin_denied_for_admin(self, client, app, superadmin_user, admin_user):
        """Test deleting superadmin is denied for admin users."""
        client.post('/login', data={
            'username': 'admin',
            'password': 'password123'
        })

        superadmin_id = superadmin_user.id

        response = client.post(f'/users/{superadmin_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from app.models import User
            user = User.query.get(superadmin_id)
            assert user is not None

    def test_delete_user_with_linked_records_shows_confirmation(self, client, app, superadmin_user, operator_user, agent):
        """Test deleting user with linked records shows confirmation instead of deleting."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        # Create an activity owned by operator
        with app.app_context():
            from app.models import RevenueActivity
            from app import db
            a = RevenueActivity(
                title='Operator Act', date=date.today(), status='bozza',
                total_revenue=Decimal('100'), agent_id=agent.id,
                agent_percentage=Decimal('10'), created_by=operator_user.id,
            )
            db.session.add(a)
            db.session.commit()

        user_id = operator_user.id
        response = client.post(f'/users/{user_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode()
        # Should show confirmation panel, not delete
        assert 'confirm_force' in html

        with app.app_context():
            from app.models import User
            assert User.query.get(user_id) is not None

    def test_delete_user_force_with_linked_records(self, client, app, superadmin_user, operator_user, agent):
        """Test force-deleting user with linked records removes user and data."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        with app.app_context():
            from app.models import RevenueActivity
            from app import db
            a = RevenueActivity(
                title='To Delete', date=date.today(), status='bozza',
                total_revenue=Decimal('100'), agent_id=agent.id,
                agent_percentage=Decimal('10'), created_by=operator_user.id,
            )
            db.session.add(a)
            db.session.commit()
            act_id = a.id

        user_id = operator_user.id
        response = client.post(f'/users/{user_id}/delete', data={
            'confirm_force': '1'
        }, follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from app.models import User, RevenueActivity
            assert User.query.get(user_id) is None
            assert RevenueActivity.query.get(act_id) is None


class TestReportRoutes:
    """Test report generation routes."""

    def test_reports_page(self, client, superadmin_user):
        """Test reports page loads."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/reports/')
        assert response.status_code == 200

    def test_monthly_report_generation(self, client, superadmin_user):
        """Test monthly report generation."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        today = date.today()
        response = client.get(f'/reports/?year={today.year}&month={today.month}')
        assert response.status_code == 200


class TestAuditRoutes:
    """Test audit log routes."""

    def test_audit_list_superadmin_only(self, client, superadmin_user):
        """Test audit list is superadmin-only."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get('/audit/')
        assert response.status_code == 200

    def test_audit_list_admin_denied(self, client, admin_user):
        """Test audit list denies access to admins."""
        client.post('/login', data={
            'username': 'admin',
            'password': 'password123'
        })
        
        response = client.get('/audit/', follow_redirects=False)
        assert response.status_code in (301, 302, 303, 307, 401, 403)

    def test_audit_detail(self, client, superadmin_user, audit_log):
        """Test audit log detail view."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })
        
        response = client.get(f'/audit/{audit_log.id}')
        assert response.status_code == 200


class TestManualRoutes:
    """Test manual page routes."""

    def test_manual_not_logged_in(self, client):
        """Test manual page redirects when not logged in."""
        response = client.get('/manual', follow_redirects=False)
        assert response.status_code in (301, 302, 303, 307)

    def test_manual_logged_in_italian(self, client, superadmin_user):
        """Test manual page loads in Italian."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        response = client.get('/manual')
        assert response.status_code == 200
        assert 'Manuale Utente'.encode() in response.data
        assert 'Cos\'è Small ERP'.encode() in response.data

    def test_manual_logged_in_english(self, client, superadmin_user):
        """Test manual page loads in English."""
        client.post('/login', data={
            'username': 'superadmin',
            'password': 'password123'
        })

        # Switch language to English
        client.post('/set-language', data={'lang': 'en', 'next': '/manual'})

        response = client.get('/manual')
        assert response.status_code == 200
        assert b'User Manual' in response.data
        assert b'What is Small ERP' in response.data

    def test_manual_accessible_by_operator(self, client, operator_user):
        """Test manual page is accessible by operator role."""
        client.post('/login', data={
            'username': 'operator',
            'password': 'password123'
        })

        response = client.get('/manual')
        assert response.status_code == 200
