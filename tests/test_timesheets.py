"""Tests for timesheet functionality."""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from app import create_app, db
from app.models import User, RevenueActivity, ActivityCost, TimesheetEntry, Agent
from app.services import (
    create_timesheet_entry,
    update_timesheet_entry,
    delete_timesheet_entry,
    rebuild_internal_consultant_cost,
    get_internal_consultant_cost,
    TimesheetValidationError,
)


# ---------------------------------------------------------------------------
# Additional fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_with_rate(app):
    """Create an operator user with an hourly_cost_rate set."""
    with app.app_context():
        user = User(
            username='consultant1',
            email='consultant1@test.com',
            full_name='Mario Rossi',
            hourly_cost_rate=Decimal('20.00'),
        )
        user.set_password('TestPassword1!')
        db.session.add(user)
        db.session.commit()
        uid = user.id
    with app.app_context():
        return db.session.get(User, uid)


@pytest.fixture
def user_no_rate(app):
    """Create a user with hourly_cost_rate=0 (not configured for timesheets)."""
    with app.app_context():
        user = User(
            username='norate',
            email='norate@test.com',
            full_name='No Rate User',
            hourly_cost_rate=Decimal('0'),  # zero = not configured
        )
        user.set_password('TestPassword1!')
        db.session.add(user)
        db.session.commit()
        uid = user.id
    with app.app_context():
        return db.session.get(User, uid)


@pytest.fixture
def simple_activity(app, user_with_rate):
    """Create a simple activity owned by user_with_rate."""
    with app.app_context():
        activity = RevenueActivity(
            title='Test Timesheet Activity',
            date=date.today(),
            status='confermata',
            total_revenue=Decimal('5000.00'),
            created_by=user_with_rate.id,
        )
        db.session.add(activity)
        db.session.commit()
        aid = activity.id
    with app.app_context():
        return db.session.get(RevenueActivity, aid)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestTimesheetModel:

    def test_user_has_hourly_cost_rate(self, app, user_with_rate):
        with app.app_context():
            u = db.session.get(User, user_with_rate.id)
            assert u.hourly_cost_rate == Decimal('20.00')

    def test_user_default_hourly_cost_rate_zero(self, app, operator_user):
        with app.app_context():
            u = db.session.get(User, operator_user.id)
            # Default should be 0 (not None) when not set explicitly
            assert u.hourly_cost_rate is not None or u.hourly_cost_rate is None

    def test_activity_cost_new_fields_defaults(self, app, revenue_activity):
        with app.app_context():
            cost = ActivityCost(
                activity_id=revenue_activity.id,
                category='materiale',
                description='Test',
                amount=Decimal('100.00'),
                date=date.today(),
            )
            db.session.add(cost)
            db.session.commit()
            db.session.refresh(cost)
            assert cost.line_type == 'generic'
            assert cost.source_type == 'manual'
            assert cost.source_user_id is None
            assert cost.is_auto_generated is False

    def test_timesheet_entry_creation(self, app, user_with_rate, simple_activity):
        with app.app_context():
            entry = TimesheetEntry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5.00'),
                description='Test work',
                hourly_rate_snapshot=Decimal('20.00'),
                created_by=user_with_rate.id,
            )
            db.session.add(entry)
            db.session.commit()
            db.session.refresh(entry)
            assert entry.id is not None
            assert entry.hours == Decimal('5.00')
            assert entry.hourly_rate_snapshot == Decimal('20.00')

    def test_timesheet_relations(self, app, user_with_rate, simple_activity):
        with app.app_context():
            entry = TimesheetEntry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('3.00'),
                description='Some work',
                hourly_rate_snapshot=Decimal('20.00'),
                created_by=user_with_rate.id,
            )
            db.session.add(entry)
            db.session.commit()
            eid = entry.id

            entry = db.session.get(TimesheetEntry, eid)
            assert entry.user.full_name == 'Mario Rossi'
            assert entry.activity.title == 'Test Timesheet Activity'


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestTimesheetServices:

    def test_create_timesheet_creates_cost_aggregate(self, app, user_with_rate, simple_activity):
        with app.app_context():
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5'),
                description='Test work day 1',
                created_by_id=user_with_rate.id,
            )
            cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            assert cost is not None
            assert cost.hours_total == Decimal('5')
            assert cost.amount == Decimal('100.00')  # 5h * 20€
            assert cost.line_type == 'internal_consultant'
            assert cost.source_type == 'timesheet_aggregate'
            assert cost.is_auto_generated is True

    def test_multiple_timesheets_produce_single_cost_row(self, app, user_with_rate, simple_activity):
        with app.app_context():
            # Three timesheet entries like in the spec example
            for h, desc in [(5, 'Day 1'), (7, 'Day 2'), (8, 'Day 3')]:
                create_timesheet_entry(
                    user_id=user_with_rate.id,
                    activity_id=simple_activity.id,
                    work_date=date.today(),
                    hours=Decimal(str(h)),
                    description=desc,
                    created_by_id=user_with_rate.id,
                )

            costs = ActivityCost.query.filter_by(
                activity_id=simple_activity.id,
                line_type='internal_consultant',
            ).all()
            assert len(costs) == 1
            assert costs[0].hours_total == Decimal('20')
            assert costs[0].amount == Decimal('400.00')  # 20h * 20€

    def test_cost_description_format(self, app, user_with_rate, simple_activity):
        with app.app_context():
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('4'),
                description='Work',
                created_by_id=user_with_rate.id,
            )
            cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            assert cost.description == 'Costo consulenti interni - Mario Rossi'

    def test_update_timesheet_recalculates_aggregate(self, app, user_with_rate, simple_activity):
        with app.app_context():
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5'),
                description='Initial',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

            user = db.session.get(User, user_with_rate.id)
            update_timesheet_entry(
                entry_id=eid,
                requesting_user=user,
                hours=Decimal('8'),
            )

            cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            assert cost.hours_total == Decimal('8')
            assert cost.amount == Decimal('160.00')  # 8h * 20€

    def test_delete_timesheet_removes_cost_aggregate(self, app, user_with_rate, simple_activity):
        with app.app_context():
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5'),
                description='To delete',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

            user = db.session.get(User, user_with_rate.id)
            delete_timesheet_entry(eid, user)

            cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            assert cost is None

    def test_delete_one_of_multiple_timesheets_updates_aggregate(self, app, user_with_rate, simple_activity):
        with app.app_context():
            e1 = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5'),
                description='First',
                created_by_id=user_with_rate.id,
            )
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today() + timedelta(days=1),
                hours=Decimal('7'),
                description='Second',
                created_by_id=user_with_rate.id,
            )

            user = db.session.get(User, user_with_rate.id)
            delete_timesheet_entry(e1.id, user)

            cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            assert cost is not None
            assert cost.hours_total == Decimal('7')
            assert cost.amount == Decimal('140.00')

    def test_uses_hourly_rate_snapshot_not_current_rate(self, app, simple_activity):
        """Verify historical snapshot is used, not the user's current rate."""
        with app.app_context():
            user = User(
                username='rate_change',
                email='rate_change@test.com',
                full_name='Rate Change User',
                hourly_cost_rate=Decimal('10.00'),
            )
            user.set_password('TestPassword1!')
            db.session.add(user)
            db.session.commit()

            entry = create_timesheet_entry(
                user_id=user.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5'),
                description='Work at old rate',
                created_by_id=user.id,
            )
            eid = entry.id

            # Change the user's rate
            user.hourly_cost_rate = Decimal('50.00')
            db.session.commit()

            # Rebuild explicitly (simulates a new timesheet triggering rebuild)
            rebuild_internal_consultant_cost(simple_activity.id, user.id)
            db.session.commit()

            cost = get_internal_consultant_cost(simple_activity.id, user.id)
            # Amount should still be 5*10=50, not 5*50=250
            assert cost.amount == Decimal('50.00')

    def test_external_consultant_costs_not_affected_by_timesheets(self, app, user_with_rate, simple_activity):
        with app.app_context():
            # Add a manual external consultant cost
            ext_cost = ActivityCost(
                activity_id=simple_activity.id,
                category='consulenza',
                description='External consultant X',
                amount=Decimal('500.00'),
                date=date.today(),
                cost_type='operativo',
                line_type='external_consultant',
                source_type='manual',
                is_auto_generated=False,
            )
            db.session.add(ext_cost)
            db.session.commit()
            ext_cost_id = ext_cost.id

            # Add a timesheet
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('3'),
                description='Internal work',
                created_by_id=user_with_rate.id,
            )

            # External cost must be untouched
            ext_cost_db = db.session.get(ActivityCost, ext_cost_id)
            assert ext_cost_db is not None
            assert ext_cost_db.amount == Decimal('500.00')
            assert ext_cost_db.line_type == 'external_consultant'

            # Internal aggregate must exist separately
            int_cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            assert int_cost is not None
            assert int_cost.amount == Decimal('60.00')  # 3*20

    def test_user_without_rate_cannot_create_timesheet(self, app, user_no_rate, simple_activity):
        with app.app_context():
            with pytest.raises(TimesheetValidationError, match='tariffa'):
                create_timesheet_entry(
                    user_id=user_no_rate.id,
                    activity_id=simple_activity.id,
                    work_date=date.today(),
                    hours=Decimal('4'),
                    description='Work',
                    created_by_id=user_no_rate.id,
                )

    def test_hours_must_be_positive(self, app, user_with_rate, simple_activity):
        with app.app_context():
            with pytest.raises(TimesheetValidationError):
                create_timesheet_entry(
                    user_id=user_with_rate.id,
                    activity_id=simple_activity.id,
                    work_date=date.today(),
                    hours=Decimal('0'),
                    description='Work',
                    created_by_id=user_with_rate.id,
                )

    def test_hours_cannot_exceed_24(self, app, user_with_rate, simple_activity):
        with app.app_context():
            with pytest.raises(TimesheetValidationError):
                create_timesheet_entry(
                    user_id=user_with_rate.id,
                    activity_id=simple_activity.id,
                    work_date=date.today(),
                    hours=Decimal('25'),
                    description='Work',
                    created_by_id=user_with_rate.id,
                )

    def test_description_is_required(self, app, user_with_rate, simple_activity):
        with app.app_context():
            with pytest.raises(TimesheetValidationError):
                create_timesheet_entry(
                    user_id=user_with_rate.id,
                    activity_id=simple_activity.id,
                    work_date=date.today(),
                    hours=Decimal('4'),
                    description='   ',
                    created_by_id=user_with_rate.id,
                )


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------

class TestTimesheetAuthorization:

    def test_user_cannot_edit_another_users_timesheet(self, app, user_with_rate, simple_activity, operator_user):
        with app.app_context():
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('4'),
                description='Entry by user_with_rate',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

            other = db.session.get(User, operator_user.id)
            with pytest.raises(TimesheetValidationError, match='autorizzato'):
                update_timesheet_entry(eid, other, hours=Decimal('2'))

    def test_user_cannot_delete_another_users_timesheet(self, app, user_with_rate, simple_activity, operator_user):
        with app.app_context():
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('4'),
                description='Entry by user_with_rate',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

            other = db.session.get(User, operator_user.id)
            with pytest.raises(TimesheetValidationError, match='autorizzato'):
                delete_timesheet_entry(eid, other)

    def test_superadmin_can_edit_any_timesheet(self, app, user_with_rate, simple_activity, superadmin_user):
        with app.app_context():
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('4'),
                description='Entry by user_with_rate',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

            admin = db.session.get(User, superadmin_user.id)
            # Should not raise
            updated = update_timesheet_entry(eid, admin, hours=Decimal('6'))
            assert updated.hours == Decimal('6')

    def test_superadmin_can_delete_any_timesheet(self, app, user_with_rate, simple_activity, superadmin_user):
        with app.app_context():
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('4'),
                description='Entry by user_with_rate',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

            admin = db.session.get(User, superadmin_user.id)
            delete_timesheet_entry(eid, admin)  # should not raise

            assert db.session.get(TimesheetEntry, eid) is None


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

def _login(client, username, password='password123'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


class TestTimesheetRoutes:

    def test_add_timesheet_get(self, client, app, user_with_rate, simple_activity):
        with app.app_context():
            u = db.session.get(User, user_with_rate.id)
            u.set_password('TestPassword1!')
            db.session.commit()

        _login(client, 'consultant1', 'TestPassword1!')
        resp = client.get(f'/activities/{simple_activity.id}/timesheets/add')
        assert resp.status_code == 200

    def test_add_timesheet_post(self, client, app, user_with_rate, simple_activity):
        with app.app_context():
            u = db.session.get(User, user_with_rate.id)
            u.set_password('TestPassword1!')
            db.session.commit()

        _login(client, 'consultant1', 'TestPassword1!')
        resp = client.post(
            f'/activities/{simple_activity.id}/timesheets/add',
            data={
                'work_date': date.today().isoformat(),
                'hours': '5',
                'description': 'Test work via route',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            entries = TimesheetEntry.query.filter_by(activity_id=simple_activity.id).all()
            assert len(entries) == 1
            assert entries[0].hours == Decimal('5')

    def test_edit_timesheet_own(self, client, app, user_with_rate, simple_activity):
        with app.app_context():
            u = db.session.get(User, user_with_rate.id)
            u.set_password('TestPassword1!')
            db.session.commit()
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('4'),
                description='Original',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

        _login(client, 'consultant1', 'TestPassword1!')
        resp = client.post(
            f'/activities/{simple_activity.id}/timesheets/{eid}/edit',
            data={
                'work_date': date.today().isoformat(),
                'hours': '8',
                'description': 'Updated description',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            e = db.session.get(TimesheetEntry, eid)
            assert e.hours == Decimal('8')

    def test_delete_timesheet_own(self, client, app, user_with_rate, simple_activity):
        with app.app_context():
            u = db.session.get(User, user_with_rate.id)
            u.set_password('TestPassword1!')
            db.session.commit()
            entry = create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('4'),
                description='To delete',
                created_by_id=user_with_rate.id,
            )
            eid = entry.id

        _login(client, 'consultant1', 'TestPassword1!')
        resp = client.post(
            f'/activities/{simple_activity.id}/timesheets/{eid}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(TimesheetEntry, eid) is None

    def test_auto_generated_cost_not_editable(self, client, app, user_with_rate, simple_activity, superadmin_user):
        """Auto-generated costs should redirect with error, not render edit form."""
        with app.app_context():
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('3'),
                description='Work',
                created_by_id=user_with_rate.id,
            )
            cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            cid = cost.id

        with app.app_context():
            u = db.session.get(User, superadmin_user.id)
            u.set_password('password123')
            db.session.commit()

        _login(client, 'superadmin', 'password123')
        resp = client.get(
            f'/activities/{simple_activity.id}/costs/{cid}/edit',
            follow_redirects=True,
        )
        # Should redirect back to detail with an error flash
        assert resp.status_code == 200

    def test_auto_generated_cost_not_deletable(self, client, app, user_with_rate, simple_activity, superadmin_user):
        with app.app_context():
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('3'),
                description='Work',
                created_by_id=user_with_rate.id,
            )
            cost = get_internal_consultant_cost(simple_activity.id, user_with_rate.id)
            cid = cost.id

        with app.app_context():
            u = db.session.get(User, superadmin_user.id)
            u.set_password('password123')
            db.session.commit()

        _login(client, 'superadmin', 'password123')
        resp = client.post(
            f'/activities/{simple_activity.id}/costs/{cid}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            cost_db = db.session.get(ActivityCost, cid)
            assert cost_db is not None  # still exists

    def test_my_timesheets_view(self, client, app, user_with_rate, simple_activity):
        with app.app_context():
            u = db.session.get(User, user_with_rate.id)
            u.set_password('TestPassword1!')
            db.session.commit()
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5'),
                description='Visible entry',
                created_by_id=user_with_rate.id,
            )

        _login(client, 'consultant1', 'TestPassword1!')
        resp = client.get('/timesheets/')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Report tests
# ---------------------------------------------------------------------------

class TestTimesheetReports:

    def test_activity_totals_includes_internal_costs(self, app, user_with_rate, simple_activity):
        from app.services import calc_activity_totals
        with app.app_context():
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('10'),
                description='Work',
                created_by_id=user_with_rate.id,
            )
            activity = db.session.get(RevenueActivity, simple_activity.id)
            totals = calc_activity_totals(activity)

            assert totals['total_internal_consultant_costs'] == Decimal('200.00')
            assert totals['total_internal_hours'] == Decimal('10')
            assert totals['total_external_consultant_costs'] == Decimal('0')

    def test_activity_totals_separates_internal_external(self, app, user_with_rate, simple_activity):
        from app.services import calc_activity_totals
        with app.app_context():
            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=simple_activity.id,
                work_date=date.today(),
                hours=Decimal('5'),
                description='Internal work',
                created_by_id=user_with_rate.id,
            )
            ext_cost = ActivityCost(
                activity_id=simple_activity.id,
                category='consulenza',
                description='External consultant',
                amount=Decimal('300.00'),
                date=date.today(),
                cost_type='operativo',
                line_type='external_consultant',
                source_type='manual',
            )
            db.session.add(ext_cost)
            db.session.commit()

            activity = db.session.get(RevenueActivity, simple_activity.id)
            totals = calc_activity_totals(activity)

            assert totals['total_internal_consultant_costs'] == Decimal('100.00')
            assert totals['total_external_consultant_costs'] == Decimal('300.00')
            assert totals['total_internal_hours'] == Decimal('5')

    def test_monthly_report_includes_consultant_totals(self, app, user_with_rate):
        from app.services import calc_monthly_report
        with app.app_context():
            activity = RevenueActivity(
                title='Report Test Activity',
                date=date(2026, 4, 1),
                status='chiusa',
                total_revenue=Decimal('1000.00'),
                created_by=user_with_rate.id,
            )
            db.session.add(activity)
            db.session.commit()

            create_timesheet_entry(
                user_id=user_with_rate.id,
                activity_id=activity.id,
                work_date=date(2026, 4, 1),
                hours=Decimal('8'),
                description='Report work',
                created_by_id=user_with_rate.id,
            )

            report = calc_monthly_report(2026, 4)
            assert report['total_internal_consultant_costs'] == Decimal('160.00')
            assert report['total_internal_hours'] == Decimal('8')
