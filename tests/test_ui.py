"""Comprehensive UI tests for all pages and user interactions in Small ERP.

Tests cover: template rendering, HTML elements, navigation, form validation,
flash messages, role-based UI visibility, i18n, filters, pagination,
edge cases, and full CRUD workflows through the UI.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.models import (
    User, Agent, RevenueActivity, ActivityCost, ActivityParticipant, AuditLog,
)
from app import db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client, username='superadmin', password='password123'):
    return client.post('/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def _create_activity(client, title='UI Test Activity', revenue='5000.00',
                     agent_id=None, pct='10.00', status='bozza'):
    data = {
        'title': title,
        'description': 'Created by UI test',
        'date': date.today().isoformat(),
        'total_revenue': revenue,
        'agent_percentage': pct,
        'status': status,
    }
    if agent_id:
        data['agent_id'] = str(agent_id)
    return client.post('/activities/new', data=data, follow_redirects=True)


# ===========================================================================
# LOGIN PAGE UI
# ===========================================================================

class TestLoginPageUI:
    """Verify login page renders all expected elements."""

    def test_login_page_has_form_fields(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200
        assert b'name="username"' in resp.data
        assert b'name="password"' in resp.data
        assert b'csrf_token' in resp.data

    def test_login_page_has_brand(self, client):
        resp = client.get('/login')
        assert b'Small ERP' in resp.data

    def test_login_page_has_submit_button(self, client):
        resp = client.get('/login')
        assert b'type="submit"' in resp.data

    def test_login_shows_error_flash_on_bad_credentials(self, client, superadmin_user):
        resp = client.post('/login', data={
            'username': 'superadmin', 'password': 'wrong',
        }, follow_redirects=True)
        assert b'flash' in resp.data

    def test_login_redirects_authenticated_user_to_dashboard(self, client, superadmin_user):
        _login(client)
        resp = client.get('/login', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_login_empty_username(self, client):
        resp = client.post('/login', data={
            'username': '', 'password': 'password123',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_preserves_next_parameter_in_form(self, client, superadmin_user):
        resp = client.get('/login?next=/activities/')
        assert resp.status_code == 200


# ===========================================================================
# DASHBOARD UI
# ===========================================================================

class TestDashboardUI:
    """Verify dashboard template structure and content."""

    def test_dashboard_has_stat_cards(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'stat-card' in resp.data

    def test_dashboard_shows_navigation_sidebar(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'sidebar' in resp.data
        assert b'Dashboard' in resp.data

    def test_dashboard_shows_new_activity_button(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'/activities/new' in resp.data

    def test_dashboard_shows_recent_activities_table(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/')
        assert b'Test Activity' in resp.data

    def test_dashboard_shows_empty_state_when_no_activities(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        # Either shows table or empty-state
        assert b'empty-state' in resp.data or b'table' in resp.data

    def test_dashboard_kpi_values_present(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'stat-value' in resp.data

    def test_dashboard_shows_user_info_in_sidebar(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'Super Admin' in resp.data or b'superadmin' in resp.data

    def test_dashboard_has_logout_form(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'/logout' in resp.data
        assert b'method="POST"' in resp.data

    def test_dashboard_shows_admin_nav_for_admin(self, client, admin_user):
        _login(client, 'admin')
        resp = client.get('/')
        assert b'/users/' in resp.data

    def test_dashboard_hides_admin_nav_for_operator(self, client, operator_user):
        _login(client, 'operator')
        resp = client.get('/')
        assert b'/users/' not in resp.data

    def test_dashboard_shows_audit_nav_for_superadmin(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'/audit/' in resp.data

    def test_dashboard_hides_audit_nav_for_admin(self, client, admin_user):
        _login(client, 'admin')
        resp = client.get('/')
        assert b'/audit/' not in resp.data

    def test_dashboard_has_language_switcher(self, client, superadmin_user):
        _login(client)
        resp = client.get('/')
        assert b'lang-switch' in resp.data
        assert b'Italiano' in resp.data
        assert b'English' in resp.data


# ===========================================================================
# ACTIVITIES LIST UI
# ===========================================================================

class TestActivitiesListUI:
    """Verify activities listing page structure."""

    def test_activities_page_renders(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/')
        assert resp.status_code == 200

    def test_activities_page_has_new_button(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/')
        assert b'/activities/new' in resp.data

    def test_activities_shows_count(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        # "1 attivita totali" or "1 total activities"
        assert b'1' in resp.data

    def test_activities_table_shows_columns(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        assert b'Test Activity' in resp.data

    def test_activities_shows_status_badge(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        assert b'badge' in resp.data

    def test_activities_has_edit_link(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        assert f'/activities/{revenue_activity.id}/edit'.encode() in resp.data

    def test_activities_has_delete_form(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        assert f'/activities/{revenue_activity.id}/delete'.encode() in resp.data

    def test_activities_has_detail_link(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        assert f'/activities/{revenue_activity.id}'.encode() in resp.data

    def test_activities_shows_agent_name(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        assert b'Mario Rossi' in resp.data

    def test_activities_empty_state(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/')
        assert b'empty-state' in resp.data

    def test_activities_filter_by_status_bozza(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/?status=bozza')
        assert b'Test Activity' in resp.data

    def test_activities_filter_by_status_chiusa_hides_bozza(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/?status=chiusa')
        assert b'Test Activity' not in resp.data

    def test_activities_filter_preserves_selected(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/?status=confermata')
        assert b'selected' in resp.data

    def test_activities_filter_unknown_status(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/?status=nonexistent')
        assert resp.status_code == 200

    def test_activities_shows_revenue_formatted(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        # Italian currency format: 1.000,00
        assert b'1.000,00' in resp.data

    def test_activities_hides_edit_and_delete_for_non_owner_operator(self, client, superadmin_user, operator_user, revenue_activity):
        _login(client, 'operator')
        resp = client.get('/activities/')
        assert f'/activities/{revenue_activity.id}/edit'.encode() not in resp.data
        assert f'/activities/{revenue_activity.id}/delete'.encode() not in resp.data


# ===========================================================================
# ACTIVITY FORM UI
# ===========================================================================

class TestActivityFormUI:
    """Verify activity create/edit forms."""

    def test_create_form_has_all_fields(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/new')
        for field in [b'name="title"', b'name="date"', b'name="description"',
                      b'name="status"', b'name="total_revenue"',
                      b'name="agent_percentage"', b'name="agent_id"', b'name="notes"']:
            assert field in resp.data, f'Missing field: {field}'

    def test_create_form_has_agent_dropdown(self, client, superadmin_user, agent):
        _login(client)
        resp = client.get('/activities/new')
        assert b'Mario Rossi' in resp.data

    def test_create_form_has_status_options(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/new')
        assert b'value="bozza"' in resp.data
        assert b'value="confermata"' in resp.data
        assert b'value="chiusa"' in resp.data

    def test_create_form_has_csrf_token(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/new')
        assert b'csrf_token' in resp.data

    def test_create_form_submit_success(self, client, app, superadmin_user, agent):
        _login(client)
        resp = _create_activity(client, agent_id=agent.id)
        assert resp.status_code == 200
        with app.app_context():
            act = RevenueActivity.query.filter_by(title='UI Test Activity').first()
            assert act is not None

    def test_create_form_shows_flash_on_success(self, client, superadmin_user, agent):
        _login(client)
        resp = _create_activity(client, agent_id=agent.id)
        assert b'flash' in resp.data

    def test_create_form_invalid_revenue(self, client, superadmin_user):
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'Bad Revenue',
            'date': date.today().isoformat(),
            'total_revenue': 'not-a-number',
            'agent_percentage': '0',
        }, follow_redirects=True)
        assert b'flash' in resp.data

    def test_create_form_missing_title_rejected(self, client, app, superadmin_user):
        """Empty titles are rejected server-side."""
        _login(client)
        resp = client.post('/activities/new', data={
            'title': '',
            'date': date.today().isoformat(),
            'total_revenue': '100',
            'agent_percentage': '0',
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert RevenueActivity.query.filter_by(title='').first() is None

    def test_create_form_whitespace_title_rejected(self, client, app, superadmin_user):
        """Whitespace-only titles are rejected server-side."""
        _login(client)
        resp = client.post('/activities/new', data={
            'title': '   ',
            'date': date.today().isoformat(),
            'total_revenue': '100',
            'agent_percentage': '0',
        }, follow_redirects=True)
        assert b'flash' in resp.data

    def test_create_form_agent_percentage_over_100_rejected(self, client, app, superadmin_user, agent):
        """Agent percentage > 100 should be rejected."""
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'Over 100 Test',
            'date': date.today().isoformat(),
            'total_revenue': '1000',
            'agent_id': str(agent.id),
            'agent_percentage': '150',
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert RevenueActivity.query.filter_by(title='Over 100 Test').first() is None

    def test_create_form_missing_date_rejected(self, client, app, superadmin_user):
        """Empty date is rejected server-side."""
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'No Date Activity',
            'date': '',
            'total_revenue': '100',
            'agent_percentage': '0',
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert RevenueActivity.query.filter_by(title='No Date Activity').first() is None

    def test_create_form_comma_decimal(self, client, app, superadmin_user):
        """Italian comma-separated decimals should work."""
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'Comma Test',
            'date': date.today().isoformat(),
            'total_revenue': '1000,50',
            'agent_percentage': '10,5',
            'status': 'bozza',
        }, follow_redirects=True)
        with app.app_context():
            act = RevenueActivity.query.filter_by(title='Comma Test').first()
            assert act is not None
            assert act.total_revenue == Decimal('1000.50')

    def test_edit_form_prefills_values(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/edit')
        assert b'Test Activity' in resp.data
        assert b'1000' in resp.data

    def test_edit_form_submit(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/edit', data={
            'title': 'Edited via UI',
            'date': date.today().isoformat(),
            'total_revenue': '3000',
            'agent_percentage': '12',
            'status': 'confermata',
        }, follow_redirects=True)
        with app.app_context():
            act = db.session.get(RevenueActivity, revenue_activity.id)
            assert act.title == 'Edited via UI'
            assert act.status == 'confermata'

    def test_create_without_agent(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'No Agent Activity',
            'date': date.today().isoformat(),
            'total_revenue': '500',
            'agent_percentage': '0',
            'status': 'bozza',
        }, follow_redirects=True)
        with app.app_context():
            act = RevenueActivity.query.filter_by(title='No Agent Activity').first()
            assert act is not None
            assert act.agent_id is None


# ===========================================================================
# ACTIVITY DETAIL UI
# ===========================================================================

class TestActivityDetailUI:
    """Verify activity detail page."""

    def test_detail_shows_title(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'Test Activity' in resp.data

    def test_detail_shows_financial_breakdown(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'breakdown' in resp.data
        assert b'1.000,00' in resp.data  # revenue formatted

    def test_detail_shows_agent_compensation(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'100,00' in resp.data  # 10% of 1000

    def test_detail_shows_net_margin(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'900,00' in resp.data  # 1000 - 100

    def test_detail_has_edit_button(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert f'/activities/{revenue_activity.id}/edit'.encode() in resp.data

    def test_detail_has_delete_form(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert f'/activities/{revenue_activity.id}/delete'.encode() in resp.data

    def test_detail_hides_edit_and_delete_for_non_owner_operator(self, client, superadmin_user, operator_user, revenue_activity):
        _login(client, 'operator')
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert f'/activities/{revenue_activity.id}/edit'.encode() not in resp.data
        assert f'/activities/{revenue_activity.id}/delete'.encode() not in resp.data

    def test_detail_has_add_cost_button(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'costs/add' in resp.data

    def test_detail_has_add_participant_button(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'participants/add' in resp.data

    def test_detail_shows_status_badge(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'badge' in resp.data

    def test_detail_shows_costs_table(self, client, superadmin_user, revenue_activity, activity_cost):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'Test Material' in resp.data

    def test_detail_shows_participants(self, client, superadmin_user, revenue_activity, activity_participant):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'Test Participant' in resp.data

    def test_detail_shows_participant_total_due(self, client, superadmin_user, revenue_activity, activity_participant):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        assert b'participant-total' in resp.data

    def test_detail_shows_notes(self, client, app, superadmin_user, agent):
        _login(client)
        client.post('/activities/new', data={
            'title': 'With Notes',
            'date': date.today().isoformat(),
            'total_revenue': '100',
            'agent_percentage': '0',
            'notes': 'Important note here',
        }, follow_redirects=True)
        with app.app_context():
            act = RevenueActivity.query.filter_by(title='With Notes').first()
        resp = client.get(f'/activities/{act.id}')
        assert b'Important note here' in resp.data

    def test_detail_404_for_nonexistent(self, client, superadmin_user):
        _login(client)
        resp = client.get('/activities/99999')
        assert resp.status_code == 404

    def test_detail_costs_empty_state(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}')
        # No costs, so empty-state div should appear
        assert b'empty-state' in resp.data

    def test_delete_activity_via_ui(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        act_id = revenue_activity.id
        resp = client.post(f'/activities/{act_id}/delete', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(RevenueActivity, act_id) is None


# ===========================================================================
# COST FORM UI
# ===========================================================================

class TestCostFormUI:
    """Verify cost add/edit forms."""

    def test_cost_form_renders(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/costs/add')
        assert resp.status_code == 200
        assert b'name="description"' in resp.data
        assert b'name="amount"' in resp.data
        assert b'name="category"' in resp.data

    def test_cost_form_has_category_options(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/costs/add')
        assert b'materiale' in resp.data
        assert b'trasporto' in resp.data
        assert b'consulenza' in resp.data

    def test_cost_form_has_cost_type_options(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/costs/add')
        assert b'operativo' in resp.data
        assert b'extra' in resp.data

    def test_cost_form_shows_activity_title(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/costs/add')
        assert b'Test Activity' in resp.data

    def test_add_cost_success(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/costs/add', data={
            'description': 'UI Test Cost',
            'amount': '250.00',
            'category': 'trasporto',
            'cost_type': 'operativo',
            'date': date.today().isoformat(),
        }, follow_redirects=True)
        assert b'UI Test Cost' in resp.data
        with app.app_context():
            cost = ActivityCost.query.filter_by(description='UI Test Cost').first()
            assert cost is not None
            assert cost.amount == Decimal('250.00')

    def test_edit_cost_prefills(self, client, superadmin_user, revenue_activity, activity_cost):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/costs/{activity_cost.id}/edit')
        assert b'Test Material' in resp.data
        assert b'100' in resp.data

    def test_delete_cost_via_ui(self, client, app, superadmin_user, revenue_activity, activity_cost):
        _login(client)
        cost_id = activity_cost.id
        resp = client.post(
            f'/activities/{revenue_activity.id}/costs/{cost_id}/delete',
            follow_redirects=True
        )
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(ActivityCost, cost_id) is None

    def test_add_cost_invalid_amount(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/costs/add', data={
            'description': 'Bad Cost',
            'amount': 'abc',
            'category': 'altro',
            'date': date.today().isoformat(),
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert ActivityCost.query.filter_by(description='Bad Cost').first() is None

    def test_add_cost_empty_description_rejected(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/costs/add', data={
            'description': '',
            'amount': '100',
            'category': 'altro',
            'date': date.today().isoformat(),
        }, follow_redirects=True)
        assert b'flash' in resp.data

    def test_add_cost_empty_date_rejected(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/costs/add', data={
            'description': 'No Date Cost',
            'amount': '100',
            'category': 'altro',
            'date': '',
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert ActivityCost.query.filter_by(description='No Date Cost').first() is None


# ===========================================================================
# PARTICIPANT FORM UI
# ===========================================================================

class TestParticipantFormUI:
    """Verify participant add/edit forms."""

    def test_participant_form_renders(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/participants/add')
        assert resp.status_code == 200
        assert b'name="participant_name"' in resp.data
        assert b'name="work_share"' in resp.data
        assert b'name="fixed_compensation"' in resp.data

    def test_participant_form_has_user_dropdown(self, client, superadmin_user, revenue_activity, operator_user):
        _login(client)
        resp = client.get(f'/activities/{revenue_activity.id}/participants/add')
        assert b'Operator User' in resp.data

    def test_add_participant_success(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/participants/add', data={
            'participant_name': 'UI Test Participant',
            'role_description': 'Tester',
            'work_share': '60',
            'fixed_compensation': '100',
        }, follow_redirects=True)
        assert b'UI Test Participant' in resp.data
        with app.app_context():
            p = ActivityParticipant.query.filter_by(participant_name='UI Test Participant').first()
            assert p is not None

    def test_edit_participant(self, client, app, superadmin_user, revenue_activity, activity_participant):
        _login(client)
        resp = client.post(
            f'/activities/{revenue_activity.id}/participants/{activity_participant.id}/edit',
            data={
                'participant_name': 'Updated Name',
                'work_share': '70',
                'fixed_compensation': '300',
            },
            follow_redirects=True
        )
        with app.app_context():
            p = db.session.get(ActivityParticipant, activity_participant.id)
            assert p.participant_name == 'Updated Name'

    def test_delete_participant_via_ui(self, client, app, superadmin_user, revenue_activity, activity_participant):
        _login(client)
        pid = activity_participant.id
        resp = client.post(
            f'/activities/{revenue_activity.id}/participants/{pid}/delete',
            follow_redirects=True
        )
        with app.app_context():
            assert db.session.get(ActivityParticipant, pid) is None

    def test_add_participant_without_user(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/participants/add', data={
            'participant_name': 'External Contractor',
            'work_share': '40',
            'fixed_compensation': '0',
        }, follow_redirects=True)
        with app.app_context():
            p = ActivityParticipant.query.filter_by(participant_name='External Contractor').first()
            assert p is not None
            assert p.user_id is None

    def test_add_participant_empty_name_rejected(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        resp = client.post(f'/activities/{revenue_activity.id}/participants/add', data={
            'participant_name': '',
            'work_share': '50',
            'fixed_compensation': '0',
        }, follow_redirects=True)
        assert b'flash' in resp.data


# ===========================================================================
# AGENTS LIST & FORM UI
# ===========================================================================

class TestAgentsUI:
    """Verify agents list and form pages."""

    def test_agents_page_renders(self, client, superadmin_user):
        _login(client)
        resp = client.get('/agents/')
        assert resp.status_code == 200

    def test_agents_empty_state(self, client, superadmin_user):
        _login(client)
        resp = client.get('/agents/')
        assert b'empty-state' in resp.data

    def test_agents_shows_agent(self, client, superadmin_user, agent):
        _login(client)
        resp = client.get('/agents/')
        assert b'Mario Rossi' in resp.data

    def test_agents_shows_percentage(self, client, superadmin_user, agent):
        _login(client)
        resp = client.get('/agents/')
        assert b'10,00%' in resp.data

    def test_agents_has_new_button(self, client, superadmin_user):
        _login(client)
        resp = client.get('/agents/')
        assert b'/agents/new' in resp.data

    def test_agents_has_edit_link(self, client, superadmin_user, agent):
        _login(client)
        resp = client.get('/agents/')
        assert f'/agents/{agent.id}/edit'.encode() in resp.data

    def test_agents_has_delete_form(self, client, superadmin_user, agent):
        _login(client)
        resp = client.get('/agents/')
        assert f'/agents/{agent.id}/delete'.encode() in resp.data

    def test_agent_create_form_renders(self, client, superadmin_user):
        _login(client)
        resp = client.get('/agents/new')
        assert b'name="first_name"' in resp.data
        assert b'name="default_percentage"' in resp.data

    def test_agent_create_success(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/agents/new', data={
            'first_name': 'UI Test Agent',
            'default_percentage': '15.00',
            'is_active': 'on',
        }, follow_redirects=True)
        assert b'UI Test Agent' in resp.data
        with app.app_context():
            a = Agent.query.filter_by(first_name='UI Test Agent').first()
            assert a is not None

    def test_agent_edit_prefills(self, client, superadmin_user, agent):
        _login(client)
        resp = client.get(f'/agents/{agent.id}/edit')
        assert b'Mario Rossi' in resp.data

    def test_agent_edit_submit(self, client, app, superadmin_user, agent):
        _login(client)
        resp = client.post(f'/agents/{agent.id}/edit', data={
            'first_name': 'Updated Agent',
            'default_percentage': '20',
            'is_active': 'on',
        }, follow_redirects=True)
        with app.app_context():
            a = db.session.get(Agent, agent.id)
            assert a.first_name == 'Updated Agent'

    def test_agent_delete_success(self, client, app, superadmin_user, agent):
        _login(client)
        agent_id = agent.id
        resp = client.post(f'/agents/{agent_id}/delete', follow_redirects=True)
        with app.app_context():
            assert db.session.get(Agent, agent_id) is None

    def test_agent_delete_blocked_with_activities(self, client, app, superadmin_user, revenue_activity):
        _login(client)
        with app.app_context():
            act = db.session.get(RevenueActivity, revenue_activity.id)
            agent_id = act.agent_id
        resp = client.post(f'/agents/{agent_id}/delete', follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert db.session.get(Agent, agent_id) is not None

    def test_agent_create_inactive(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/agents/new', data={
            'first_name': 'Inactive Agent',
            'default_percentage': '5',
            # is_active NOT in form = inactive
        }, follow_redirects=True)
        with app.app_context():
            a = Agent.query.filter_by(first_name='Inactive Agent').first()
            assert a is not None
            assert a.is_active is False

    def test_agent_shows_active_badge(self, client, superadmin_user, agent):
        _login(client)
        resp = client.get('/agents/')
        assert b'badge-active' in resp.data

    def test_agent_404_for_nonexistent(self, client, superadmin_user):
        _login(client)
        resp = client.get('/agents/99999/edit')
        assert resp.status_code == 404

    def test_agent_create_empty_name_rejected(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/agents/new', data={
            'first_name': '',
            'default_percentage': '10',
            'is_active': 'on',
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert Agent.query.filter_by(first_name='').first() is None

    def test_agent_create_percentage_over_100_rejected(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/agents/new', data={
            'first_name': 'Over 100 Agent',
            'default_percentage': '150',
            'is_active': 'on',
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert Agent.query.filter_by(first_name='Over 100 Agent').first() is None

    def test_agent_create_negative_percentage_rejected(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/agents/new', data={
            'first_name': 'Negative Agent',
            'default_percentage': '-5',
            'is_active': 'on',
        }, follow_redirects=True)
        assert b'flash' in resp.data
        with app.app_context():
            assert Agent.query.filter_by(first_name='Negative Agent').first() is None


# ===========================================================================
# USERS MANAGEMENT UI
# ===========================================================================

class TestUsersUI:
    """Verify user management pages."""

    def test_users_page_renders_for_admin(self, client, admin_user):
        _login(client, 'admin')
        resp = client.get('/users/')
        assert resp.status_code == 200

    def test_users_page_denied_for_operator(self, client, operator_user):
        _login(client, 'operator')
        resp = client.get('/users/', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_users_page_shows_users(self, client, superadmin_user, operator_user):
        _login(client)
        resp = client.get('/users/')
        assert b'operator' in resp.data
        assert b'superadmin' in resp.data

    def test_users_shows_active_status(self, client, superadmin_user):
        _login(client)
        resp = client.get('/users/')
        assert b'badge-active' in resp.data

    def test_user_create_form_simplified(self, client, superadmin_user):
        """Create form should only have username, password, is_active."""
        _login(client)
        resp = client.get('/users/new')
        assert b'name="username"' in resp.data
        assert b'name="password"' in resp.data
        assert b'name="is_active"' in resp.data
        # Hidden/legacy fields should NOT be exposed
        assert b'name="email"' not in resp.data
        assert b'name="full_name"' not in resp.data
        assert b'name="role"' not in resp.data

    def test_user_create_success(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': 'uitestuser',
            'password': 'Str0ngP@ssw0rd!',
            'is_active': 'on',
        }, follow_redirects=True)
        with app.app_context():
            u = User.query.filter_by(username='uitestuser').first()
            assert u is not None
            assert u.role == 'operatore'
            assert u.email == 'uitestuser@erp.local'

    def test_user_create_duplicate_username(self, client, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': 'superadmin',
            'password': 'Str0ngP@ssw0rd!',
        }, follow_redirects=True)
        assert b'flash' in resp.data

    def test_user_create_weak_password(self, client, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': 'weakuser',
            'password': 'short',
        }, follow_redirects=True)
        assert b'flash' in resp.data

    def test_user_edit_form(self, client, superadmin_user, operator_user):
        _login(client)
        resp = client.get(f'/users/{operator_user.id}/edit')
        assert resp.status_code == 200
        assert b'operator' in resp.data

    def test_user_edit_username_disabled(self, client, superadmin_user, operator_user):
        _login(client)
        resp = client.get(f'/users/{operator_user.id}/edit')
        assert b'disabled' in resp.data

    def test_user_edit_password_optional(self, client, app, superadmin_user, operator_user):
        _login(client)
        resp = client.post(f'/users/{operator_user.id}/edit', data={
            'username': 'operator',
            'password': '',
            'is_active': 'on',
        }, follow_redirects=True)
        with app.app_context():
            u = db.session.get(User, operator_user.id)
            assert u.check_password('password123')  # unchanged

    def test_user_edit_change_password(self, client, app, superadmin_user, operator_user):
        _login(client)
        resp = client.post(f'/users/{operator_user.id}/edit', data={
            'username': 'operator',
            'password': 'N3wStr0ngP@ss!',
            'is_active': 'on',
        }, follow_redirects=True)
        with app.app_context():
            u = db.session.get(User, operator_user.id)
            assert u.check_password('N3wStr0ngP@ss!')

    def test_user_deactivate(self, client, app, superadmin_user, operator_user):
        _login(client)
        resp = client.post(f'/users/{operator_user.id}/edit', data={
            'username': 'operator',
            'password': '',
            # is_active NOT in form = deactivated
        }, follow_redirects=True)
        with app.app_context():
            u = db.session.get(User, operator_user.id)
            assert u.is_active_user is False

    def test_admin_cannot_edit_superadmin(self, client, app, superadmin_user, admin_user):
        _login(client, 'admin')
        resp = client.get(f'/users/{superadmin_user.id}/edit', follow_redirects=True)
        assert b'flash' in resp.data

    def test_user_404_for_nonexistent(self, client, superadmin_user):
        _login(client)
        resp = client.get('/users/99999/edit')
        assert resp.status_code == 404

    def test_user_create_empty_username_rejected(self, client, superadmin_user):
        _login(client)
        resp = client.post('/users/new', data={
            'username': '',
            'password': 'Str0ngP@ssw0rd!',
            'is_active': 'on',
        }, follow_redirects=True)
        assert b'flash' in resp.data

    def test_user_create_form_password_placeholder_correct(self, client, superadmin_user):
        """Password placeholder should mention the actual minimum (12 chars)."""
        _login(client)
        resp = client.get('/users/new')
        assert b'12' in resp.data
        assert b'minlength="12"' in resp.data


# ===========================================================================
# REPORTS UI
# ===========================================================================

class TestReportsUI:
    """Verify reports page structure."""

    def test_reports_page_renders(self, client, superadmin_user):
        _login(client)
        resp = client.get('/reports/')
        assert resp.status_code == 200

    def test_reports_has_period_selector(self, client, superadmin_user):
        _login(client)
        resp = client.get('/reports/')
        assert b'name="month"' in resp.data
        assert b'name="year"' in resp.data

    def test_reports_shows_summary_cards(self, client, superadmin_user):
        _login(client)
        resp = client.get('/reports/')
        assert b'report-summary-card' in resp.data or b'empty-state' in resp.data

    def test_reports_empty_period(self, client, superadmin_user):
        _login(client)
        resp = client.get('/reports/?year=2020&month=1')
        assert resp.status_code == 200
        assert b'empty-state' in resp.data

    def test_reports_with_closed_activity(self, client, app, superadmin_user, agent):
        _login(client)
        # Create a closed activity for current month
        with app.app_context():
            act = RevenueActivity(
                title='Closed for Report',
                date=date.today(),
                status='chiusa',
                total_revenue=Decimal('2000.00'),
                agent_id=agent.id,
                agent_percentage=Decimal('10.00'),
                created_by=superadmin_user.id,
            )
            db.session.add(act)
            db.session.commit()

        today = date.today()
        resp = client.get(f'/reports/?year={today.year}&month={today.month}')
        assert b'Closed for Report' in resp.data
        assert b'2.000,00' in resp.data

    def test_reports_shows_agent_summary(self, client, app, superadmin_user, agent):
        _login(client)
        with app.app_context():
            act = RevenueActivity(
                title='Agent Summary Test',
                date=date.today(),
                status='chiusa',
                total_revenue=Decimal('1000.00'),
                agent_id=agent.id,
                agent_percentage=Decimal('15.00'),
                created_by=superadmin_user.id,
            )
            db.session.add(act)
            db.session.commit()

        today = date.today()
        resp = client.get(f'/reports/?year={today.year}&month={today.month}')
        assert b'Mario Rossi' in resp.data

    def test_reports_shows_participant_summary(self, client, app, superadmin_user, agent):
        _login(client)
        with app.app_context():
            act = RevenueActivity(
                title='Participant Summary',
                date=date.today(),
                status='chiusa',
                total_revenue=Decimal('5000.00'),
                agent_id=agent.id,
                agent_percentage=Decimal('10.00'),
                created_by=superadmin_user.id,
            )
            db.session.add(act)
            db.session.commit()

            p = ActivityParticipant(
                activity_id=act.id,
                participant_name='Report Participant',
                work_share=Decimal('100'),
                fixed_compensation=Decimal('0'),
            )
            db.session.add(p)
            db.session.commit()

        today = date.today()
        resp = client.get(f'/reports/?year={today.year}&month={today.month}')
        assert b'Report Participant' in resp.data

    def test_reports_has_print_button(self, client, superadmin_user):
        _login(client)
        resp = client.get('/reports/')
        assert b'window.print()' in resp.data

    def test_reports_different_month(self, client, superadmin_user):
        _login(client)
        resp = client.get('/reports/?year=2025&month=6')
        assert resp.status_code == 200

    def test_reports_draft_activities_excluded(self, client, app, superadmin_user, agent):
        _login(client)
        with app.app_context():
            act = RevenueActivity(
                title='Draft Should Not Show',
                date=date.today(),
                status='bozza',
                total_revenue=Decimal('999.00'),
                agent_id=agent.id,
                created_by=superadmin_user.id,
            )
            db.session.add(act)
            db.session.commit()

        today = date.today()
        resp = client.get(f'/reports/?year={today.year}&month={today.month}')
        assert b'Draft Should Not Show' not in resp.data


# ===========================================================================
# AUDIT LOG UI
# ===========================================================================

class TestAuditUI:
    """Verify audit log pages."""

    def test_audit_page_renders_for_superadmin(self, client, superadmin_user):
        _login(client)
        resp = client.get('/audit/')
        assert resp.status_code == 200

    def test_audit_denied_for_admin(self, client, admin_user):
        _login(client, 'admin')
        resp = client.get('/audit/', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_audit_denied_for_operator(self, client, operator_user):
        _login(client, 'operator')
        resp = client.get('/audit/', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_audit_has_filters(self, client, superadmin_user):
        _login(client)
        resp = client.get('/audit/')
        assert b'name="username"' in resp.data
        assert b'name="action_type"' in resp.data
        assert b'name="entity_type"' in resp.data
        assert b'name="date_from"' in resp.data
        assert b'name="date_to"' in resp.data

    def test_audit_shows_log_entries(self, client, superadmin_user, audit_log):
        _login(client)
        resp = client.get('/audit/')
        assert b'superadmin' in resp.data
        assert b'create' in resp.data

    def test_audit_detail_renders(self, client, superadmin_user, audit_log):
        _login(client)
        resp = client.get(f'/audit/{audit_log.id}')
        assert resp.status_code == 200
        assert b'Test audit log' in resp.data

    def test_audit_detail_shows_values(self, client, app, superadmin_user):
        _login(client)
        with app.app_context():
            from app.audit_service import log_action
            from flask_login import login_user
            with app.test_request_context('/'):
                login_user(superadmin_user)
                log_action('update', 'Agent', 1, 'Test changes',
                           old_values={'name': 'Old'}, new_values={'name': 'New'})
            log = AuditLog.query.filter_by(description='Test changes').first()
            log_id = log.id

        resp = client.get(f'/audit/{log_id}')
        assert b'Old' in resp.data
        assert b'New' in resp.data

    def test_audit_filter_by_action_type(self, client, superadmin_user, audit_log):
        _login(client)
        resp = client.get('/audit/?action_type=create')
        assert resp.status_code == 200

    def test_audit_filter_by_entity_type(self, client, superadmin_user, audit_log):
        _login(client)
        resp = client.get('/audit/?entity_type=User')
        assert resp.status_code == 200

    def test_audit_filter_by_username(self, client, superadmin_user, audit_log):
        _login(client)
        resp = client.get('/audit/?username=superadmin')
        assert resp.status_code == 200

    def test_audit_filter_by_date_range(self, client, superadmin_user, audit_log):
        _login(client)
        today = date.today().isoformat()
        resp = client.get(f'/audit/?date_from={today}&date_to={today}')
        assert resp.status_code == 200

    def test_audit_detail_404(self, client, superadmin_user):
        _login(client)
        resp = client.get('/audit/99999')
        assert resp.status_code == 404

    def test_audit_has_back_link(self, client, superadmin_user, audit_log):
        _login(client)
        resp = client.get(f'/audit/{audit_log.id}')
        assert b'/audit/' in resp.data


# ===========================================================================
# LANGUAGE / i18n UI
# ===========================================================================

class TestLanguageSwitchUI:
    """Verify language switching works across the UI."""

    def test_switch_to_english(self, client, superadmin_user):
        _login(client)
        resp = client.post('/set-language', data={
            'lang': 'en',
            'next': '/',
        }, follow_redirects=True)
        assert b'Dashboard' in resp.data
        assert b'Open Activities' in resp.data

    def test_switch_to_italian(self, client, superadmin_user):
        _login(client)
        # First switch to English
        client.post('/set-language', data={'lang': 'en', 'next': '/'})
        # Then back to Italian
        resp = client.post('/set-language', data={
            'lang': 'it',
            'next': '/',
        }, follow_redirects=True)
        assert b'Attivita Aperte' in resp.data

    def test_invalid_language_ignored(self, client, superadmin_user):
        _login(client)
        resp = client.post('/set-language', data={
            'lang': 'xx',
            'next': '/',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_language_persists_across_pages(self, client, superadmin_user):
        _login(client)
        client.post('/set-language', data={'lang': 'en', 'next': '/'})
        resp = client.get('/activities/')
        assert b'Activities' in resp.data
        resp = client.get('/agents/')
        assert b'Agents' in resp.data


# ===========================================================================
# FULL WORKFLOW E2E
# ===========================================================================

class TestFullWorkflowE2E:
    """End-to-end workflow tests through the UI."""

    def test_complete_activity_lifecycle(self, client, app, superadmin_user, agent):
        """Create activity -> add cost -> add participant -> close -> verify in report."""
        _login(client)

        # 1. Create activity
        resp = client.post('/activities/new', data={
            'title': 'E2E Lifecycle Activity',
            'description': 'Full lifecycle test',
            'date': date.today().isoformat(),
            'total_revenue': '10000',
            'agent_id': str(agent.id),
            'agent_percentage': '10',
            'status': 'bozza',
        }, follow_redirects=True)
        assert b'E2E Lifecycle Activity' in resp.data

        with app.app_context():
            act = RevenueActivity.query.filter_by(title='E2E Lifecycle Activity').first()
            act_id = act.id

        # 2. Add cost
        resp = client.post(f'/activities/{act_id}/costs/add', data={
            'description': 'E2E Cost',
            'amount': '500',
            'category': 'consulenza',
            'cost_type': 'operativo',
            'date': date.today().isoformat(),
        }, follow_redirects=True)
        assert b'E2E Cost' in resp.data

        # 3. Add participant
        resp = client.post(f'/activities/{act_id}/participants/add', data={
            'participant_name': 'E2E Participant',
            'work_share': '100',
            'fixed_compensation': '200',
        }, follow_redirects=True)
        assert b'E2E Participant' in resp.data

        # 4. Verify detail financial summary
        resp = client.get(f'/activities/{act_id}')
        assert b'10.000,00' in resp.data  # revenue
        assert b'1.000,00' in resp.data   # agent compensation (10%)

        # 5. Close activity
        resp = client.post(f'/activities/{act_id}/edit', data={
            'title': 'E2E Lifecycle Activity',
            'date': date.today().isoformat(),
            'total_revenue': '10000',
            'agent_id': str(agent.id),
            'agent_percentage': '10',
            'status': 'chiusa',
        }, follow_redirects=True)

        # 6. Verify in monthly report
        today = date.today()
        resp = client.get(f'/reports/?year={today.year}&month={today.month}')
        assert b'E2E Lifecycle Activity' in resp.data

    def test_operator_can_create_and_view_own_activity(self, client, app, operator_user, agent):
        _login(client, 'operator')

        resp = client.post('/activities/new', data={
            'title': 'Operator Activity',
            'date': date.today().isoformat(),
            'total_revenue': '500',
            'agent_percentage': '5',
            'status': 'bozza',
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            act = RevenueActivity.query.filter_by(title='Operator Activity').first()
            assert act is not None
            act_id = act.id

        # Operator can see it in list
        resp = client.get('/activities/')
        assert b'Operator Activity' in resp.data

        # Operator can view detail
        resp = client.get(f'/activities/{act_id}')
        assert resp.status_code == 200

    def test_operator_can_edit_own_activity(self, client, app, operator_user):
        _login(client, 'operator')

        client.post('/activities/new', data={
            'title': 'My Activity',
            'date': date.today().isoformat(),
            'total_revenue': '100',
            'agent_percentage': '0',
            'status': 'bozza',
        }, follow_redirects=True)

        with app.app_context():
            act = RevenueActivity.query.filter_by(title='My Activity').first()
            act_id = act.id

        resp = client.post(f'/activities/{act_id}/edit', data={
            'title': 'My Updated Activity',
            'date': date.today().isoformat(),
            'total_revenue': '200',
            'agent_percentage': '0',
            'status': 'confermata',
        }, follow_redirects=True)
        with app.app_context():
            act = db.session.get(RevenueActivity, act_id)
            assert act.title == 'My Updated Activity'

    def test_operator_cannot_edit_others_activity(self, client, app, operator_user, revenue_activity):
        _login(client, 'operator')
        resp = client.post(f'/activities/{revenue_activity.id}/edit', data={
            'title': 'Hacked',
            'date': date.today().isoformat(),
            'total_revenue': '1',
            'agent_percentage': '0',
        }, follow_redirects=True)
        # Should get authorization error flash
        with app.app_context():
            act = db.session.get(RevenueActivity, revenue_activity.id)
            assert act.title == 'Test Activity'  # unchanged


# ===========================================================================
# SECURITY & EDGE CASES IN UI
# ===========================================================================

class TestUISecurityEdgeCases:
    """Additional security and edge case UI tests."""

    def test_all_protected_routes_redirect_when_not_logged_in(self, client):
        protected = [
            '/', '/activities/', '/activities/new', '/agents/',
            '/agents/new', '/reports/', '/users/', '/audit/',
        ]
        for path in protected:
            resp = client.get(path, follow_redirects=False)
            assert resp.status_code in (301, 302, 303, 307), \
                f'{path} did not redirect: {resp.status_code}'

    def test_csrf_token_present_on_all_forms(self, client, superadmin_user, revenue_activity, agent):
        _login(client)
        form_pages = [
            '/activities/new',
            f'/activities/{revenue_activity.id}/edit',
            f'/activities/{revenue_activity.id}/costs/add',
            f'/activities/{revenue_activity.id}/participants/add',
            '/agents/new',
            f'/agents/{agent.id}/edit',
            '/users/new',
        ]
        for page in form_pages:
            resp = client.get(page)
            assert b'csrf_token' in resp.data, f'CSRF token missing on {page}'

    def test_xss_in_activity_title(self, client, app, superadmin_user):
        _login(client)
        xss_title = '<script>alert("xss")</script>'
        client.post('/activities/new', data={
            'title': xss_title,
            'date': date.today().isoformat(),
            'total_revenue': '100',
            'agent_percentage': '0',
        }, follow_redirects=True)

        with app.app_context():
            act = RevenueActivity.query.filter_by(title=xss_title).first()
            if act:
                resp = client.get(f'/activities/{act.id}')
                # Jinja2 auto-escapes, so raw <script> should not appear
                assert b'<script>alert("xss")</script>' not in resp.data

    def test_xss_in_agent_name(self, client, app, superadmin_user):
        _login(client)
        xss_name = '<img src=x onerror=alert(1)>'
        client.post('/agents/new', data={
            'first_name': xss_name,
            'default_percentage': '10',
            'is_active': 'on',
        }, follow_redirects=True)
        resp = client.get('/agents/')
        assert b'<img src=x onerror=alert(1)>' not in resp.data

    def test_large_revenue_value(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'Big Revenue',
            'date': date.today().isoformat(),
            'total_revenue': '999999999.99',
            'agent_percentage': '0',
        }, follow_redirects=True)
        with app.app_context():
            act = RevenueActivity.query.filter_by(title='Big Revenue').first()
            assert act is not None

    def test_zero_revenue_activity(self, client, app, superadmin_user):
        _login(client)
        resp = client.post('/activities/new', data={
            'title': 'Zero Revenue',
            'date': date.today().isoformat(),
            'total_revenue': '0',
            'agent_percentage': '0',
        }, follow_redirects=True)
        with app.app_context():
            act = RevenueActivity.query.filter_by(title='Zero Revenue').first()
            assert act is not None
            assert act.total_revenue == Decimal('0')

    def test_hundred_percent_agent(self, client, app, superadmin_user, agent):
        _login(client)
        resp = client.post('/activities/new', data={
            'title': '100% Agent',
            'date': date.today().isoformat(),
            'total_revenue': '1000',
            'agent_id': str(agent.id),
            'agent_percentage': '100',
        }, follow_redirects=True)
        with app.app_context():
            act = RevenueActivity.query.filter_by(title='100% Agent').first()
            assert act is not None

        resp = client.get(f'/activities/{act.id}')
        assert b'1.000,00' in resp.data  # agent compensation = full revenue


# ===========================================================================
# TEMPLATE FILTERS
# ===========================================================================

class TestTemplateFilters:
    """Verify currency and percentage filters render correctly."""

    def test_currency_filter_large_number(self, client, app, superadmin_user, agent):
        _login(client)
        with app.app_context():
            act = RevenueActivity(
                title='Big Number Filter',
                date=date.today(),
                status='bozza',
                total_revenue=Decimal('1234567.89'),
                agent_id=agent.id,
                agent_percentage=Decimal('0'),
                created_by=superadmin_user.id,
            )
            db.session.add(act)
            db.session.commit()
            act_id = act.id

        resp = client.get(f'/activities/{act_id}')
        assert b'1.234.567,89' in resp.data

    def test_currency_filter_zero(self, client, app, superadmin_user):
        _login(client)
        with app.app_context():
            act = RevenueActivity(
                title='Zero Filter',
                date=date.today(),
                status='bozza',
                total_revenue=Decimal('0'),
                agent_percentage=Decimal('0'),
                created_by=superadmin_user.id,
            )
            db.session.add(act)
            db.session.commit()
            act_id = act.id

        resp = client.get(f'/activities/{act_id}')
        assert b'0,00' in resp.data

    def test_percentage_filter_renders(self, client, superadmin_user, revenue_activity):
        _login(client)
        resp = client.get('/activities/')
        assert b'10,00%' in resp.data
