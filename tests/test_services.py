"""Tests for app.services module - Business logic and calculations."""
import pytest
from decimal import Decimal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from app.services import (
    to_decimal,
    calc_agent_compensation,
    calc_activity_totals,
    calc_monthly_report,
    calc_dashboard_stats
)
from app.models import RevenueActivity


class TestDecimalConversion:
    """Test decimal conversion utilities."""

    def test_to_decimal_from_string(self):
        """Test converting string to decimal."""
        result = to_decimal('100.50')
        assert result == Decimal('100.50')
        assert isinstance(result, Decimal)

    def test_to_decimal_from_int(self):
        """Test converting integer to decimal."""
        result = to_decimal(100)
        assert result == Decimal('100')

    def test_to_decimal_from_float(self):
        """Test converting float to decimal."""
        result = to_decimal(100.5)
        assert result == Decimal('100.5')

    def test_to_decimal_from_decimal(self):
        """Test converting decimal to decimal."""
        input_val = Decimal('100.50')
        result = to_decimal(input_val)
        assert result == Decimal('100.50')

    def test_to_decimal_none_returns_zero(self):
        """Test that None returns zero."""
        result = to_decimal(None)
        assert result == Decimal('0')

    def test_to_decimal_empty_string(self):
        """Test converting empty string."""
        from decimal import InvalidOperation
        with pytest.raises(InvalidOperation):
            to_decimal('')


class TestAgentCompensation:
    """Test agent compensation calculation."""

    def test_simple_compensation_calculation(self):
        """Test basic compensation calculation."""
        result = calc_agent_compensation(Decimal('1000.00'), Decimal('10.00'))
        assert result == Decimal('100.00')

    def test_compensation_with_string_inputs(self):
        """Test compensation with string inputs."""
        result = calc_agent_compensation('1000.00', '10.00')
        assert result == Decimal('100.00')

    def test_compensation_with_zero_percentage(self):
        """Test compensation with zero percentage."""
        result = calc_agent_compensation(Decimal('1000.00'), Decimal('0.00'))
        assert result == Decimal('0.00')

    def test_compensation_with_zero_revenue(self):
        """Test compensation with zero revenue."""
        result = calc_agent_compensation(Decimal('0.00'), Decimal('10.00'))
        assert result == Decimal('0.00')

    def test_compensation_rounding_half_up(self):
        """Test that rounding uses ROUND_HALF_UP."""
        # 1000 * 10.33 / 100 = 103.30
        result = calc_agent_compensation(Decimal('1000.00'), Decimal('10.33'))
        assert result == Decimal('103.30')

    def test_compensation_with_complex_percentage(self):
        """Test compensation with complex percentage."""
        # 5000 * 12.5 / 100 = 625.00
        result = calc_agent_compensation(Decimal('5000.00'), Decimal('12.50'))
        assert result == Decimal('625.00')

    def test_compensation_two_decimal_places(self):
        """Test that result always has exactly 2 decimal places."""
        result = calc_agent_compensation(Decimal('1000.00'), Decimal('10.00'))
        assert result.as_tuple().exponent == -2


class TestActivityTotalsCalculation:
    """Test activity financial calculations."""

    def test_activity_totals_basic(self, app, revenue_activity):
        """Test basic activity totals calculation."""
        with app.app_context():
            result = calc_activity_totals(revenue_activity)
            
            assert result['revenue'] == Decimal('1000.00')
            assert result['agent_percentage'] == Decimal('10.00')
            assert result['agent_compensation'] == Decimal('100.00')
            assert result['total_operative_costs'] == Decimal('0')
            assert result['total_extra_costs'] == Decimal('0')
            assert result['total_costs'] == Decimal('0')
            assert result['net_margin'] == Decimal('900.00')
            assert result['total_fixed_compensations'] == Decimal('0')
            assert result['distributable_residual'] == Decimal('900.00')

    def test_activity_totals_with_costs(self, app, revenue_activity, activity_cost):
        """Test activity totals with operational costs."""
        with app.app_context():
            from app import db
            result = calc_activity_totals(revenue_activity)
            
            assert result['total_operative_costs'] == Decimal('100.00')
            assert result['total_costs'] == Decimal('100.00')
            assert result['net_margin'] == Decimal('800.00')
            assert result['distributable_residual'] == Decimal('800.00')

    def test_activity_totals_with_extra_costs(self, app, revenue_activity):
        """Test activity totals with extra costs."""
        with app.app_context():
            from app import db
            from app.models import ActivityCost
            
            extra_cost = ActivityCost(
                activity_id=revenue_activity.id,
                category='altro',
                description='Extra expense',
                amount=Decimal('50.00'),
                cost_type='extra'
            )
            db.session.add(extra_cost)
            db.session.commit()
            
            result = calc_activity_totals(revenue_activity)
            assert result['total_extra_costs'] == Decimal('50.00')
            assert result['total_costs'] == Decimal('50.00')

    def test_activity_totals_with_multiple_costs(self, app, revenue_activity):
        """Test activity totals with multiple costs of different types."""
        with app.app_context():
            from app import db
            from app.models import ActivityCost
            
            cost1 = ActivityCost(
                activity_id=revenue_activity.id,
                category='materiale',
                description='Material',
                amount=Decimal('100.00'),
                cost_type='operativo'
            )
            cost2 = ActivityCost(
                activity_id=revenue_activity.id,
                category='trasporto',
                description='Transport',
                amount=Decimal('50.00'),
                cost_type='operativo'
            )
            cost3 = ActivityCost(
                activity_id=revenue_activity.id,
                category='altro',
                description='Extra',
                amount=Decimal('25.00'),
                cost_type='extra'
            )
            db.session.add_all([cost1, cost2, cost3])
            db.session.commit()
            
            result = calc_activity_totals(revenue_activity)
            assert result['total_operative_costs'] == Decimal('150.00')
            assert result['total_extra_costs'] == Decimal('25.00')
            assert result['total_costs'] == Decimal('175.00')

    def test_activity_totals_with_participant_fixed_compensation(self, app, revenue_activity, activity_participant):
        """Test activity totals with participant fixed compensation."""
        with app.app_context():
            result = calc_activity_totals(revenue_activity)
            
            assert result['total_fixed_compensations'] == Decimal('200.00')
            assert result['distributable_residual'] == Decimal('700.00')

    def test_activity_totals_participant_breakdown(self, app, revenue_activity, activity_participant):
        """Test participant breakdown in activity totals."""
        with app.app_context():
            result = calc_activity_totals(revenue_activity)
            
            assert len(result['participants']) == 1
            participant_detail = result['participants'][0]
            assert participant_detail['name'] == 'Test Participant'
            assert participant_detail['fixed_compensation'] == Decimal('200.00')
            assert participant_detail['work_share'] == Decimal('50.00')

    def test_activity_totals_multiple_participants_distribution(self, app, revenue_activity):
        """Test distribution among multiple participants."""
        with app.app_context():
            from app import db
            from app.models import ActivityParticipant
            
            p1 = ActivityParticipant(
                activity_id=revenue_activity.id,
                participant_name='Participant 1',
                work_share=Decimal('60.00'),
                fixed_compensation=Decimal('100.00')
            )
            p2 = ActivityParticipant(
                activity_id=revenue_activity.id,
                participant_name='Participant 2',
                work_share=Decimal('40.00'),
                fixed_compensation=Decimal('50.00')
            )
            db.session.add_all([p1, p2])
            db.session.commit()
            
            result = calc_activity_totals(revenue_activity)
            
            # Net margin = 1000 - 100 (agent) - 0 (costs) = 900
            # Fixed comp total = 150, distributable = 750
            # P1 gets: 100 + (750 * 60/100) = 550
            # P2 gets: 50 + (750 * 40/100) = 350
            
            assert len(result['participants']) == 2
            assert result['participants'][0]['total_due'] == Decimal('550.00')
            assert result['participants'][1]['total_due'] == Decimal('350.00')

    def test_activity_totals_no_work_share_distribution(self, app, revenue_activity):
        """Test when total work share is zero."""
        with app.app_context():
            from app import db
            from app.models import ActivityParticipant
            
            participant = ActivityParticipant(
                activity_id=revenue_activity.id,
                participant_name='Participant',
                work_share=Decimal('0.00'),
                fixed_compensation=Decimal('200.00')
            )
            db.session.add(participant)
            db.session.commit()
            
            result = calc_activity_totals(revenue_activity)
            
            p_detail = result['participants'][0]
            assert p_detail['proportional_share'] == Decimal('0.00')
            assert p_detail['total_due'] == Decimal('200.00')


class TestMonthlyReportCalculation:
    """Test monthly report generation."""

    def test_monthly_report_empty(self, app):
        """Test monthly report with no activities."""
        with app.app_context():
            today = date.today()
            result = calc_monthly_report(today.year, today.month)
            
            assert result['year'] == today.year
            assert result['month'] == today.month
            assert result['total_revenue'] == Decimal('0')
            assert result['total_costs'] == Decimal('0')
            assert result['net_margin'] == Decimal('0')
            assert len(result['activities']) == 0

    def test_monthly_report_only_closed_activities(self, app, superadmin_user, agent):
        """Test that only closed activities are included."""
        with app.app_context():
            from app import db
            
            today = date.today()
            
            # Create a draft activity
            draft = RevenueActivity(
                title='Draft Activity',
                date=today,
                status='bozza',
                total_revenue=Decimal('1000.00'),
                agent_id=agent.id,
                agent_percentage=Decimal('10.00'),
                created_by=superadmin_user.id
            )
            
            # Create a closed activity
            closed = RevenueActivity(
                title='Closed Activity',
                date=today,
                status='chiusa',
                total_revenue=Decimal('2000.00'),
                agent_id=agent.id,
                agent_percentage=Decimal('10.00'),
                created_by=superadmin_user.id
            )
            
            db.session.add_all([draft, closed])
            db.session.commit()
            
            result = calc_monthly_report(today.year, today.month)
            
            assert len(result['activities']) == 1
            assert result['total_revenue'] == Decimal('2000.00')

    def test_monthly_report_aggregates_correctly(self, app, superadmin_user, agent):
        """Test that monthly report aggregates activities correctly."""
        with app.app_context():
            from app import db
            
            today = date.today()
            
            for i in range(3):
                activity = RevenueActivity(
                    title=f'Activity {i+1}',
                    date=today,
                    status='chiusa',
                    total_revenue=Decimal('1000.00'),
                    agent_id=agent.id,
                    agent_percentage=Decimal('10.00'),
                    created_by=superadmin_user.id
                )
                db.session.add(activity)
            
            db.session.commit()
            
            result = calc_monthly_report(today.year, today.month)
            
            assert len(result['activities']) == 3
            assert result['total_revenue'] == Decimal('3000.00')
            assert result['total_agent_compensations'] == Decimal('300.00')

    def test_monthly_report_filters_by_month(self, app, superadmin_user, agent):
        """Test that report filters by month correctly."""
        with app.app_context():
            from app import db
            
            today = date.today()
            last_month = today - relativedelta(months=1)
            
            # Activity in current month
            current_activity = RevenueActivity(
                title='Current Activity',
                date=today,
                status='chiusa',
                total_revenue=Decimal('1000.00'),
                agent_id=agent.id,
                created_by=superadmin_user.id
            )
            
            # Activity in last month
            last_activity = RevenueActivity(
                title='Last Month Activity',
                date=last_month,
                status='chiusa',
                total_revenue=Decimal('2000.00'),
                agent_id=agent.id,
                created_by=superadmin_user.id
            )
            
            db.session.add_all([current_activity, last_activity])
            db.session.commit()
            
            result = calc_monthly_report(today.year, today.month)
            
            assert len(result['activities']) == 1
            assert result['total_revenue'] == Decimal('1000.00')


class TestDashboardStats:
    """Test dashboard statistics calculation."""

    def test_dashboard_stats_basic(self, app):
        """Test basic dashboard stats."""
        with app.app_context():
            result = calc_dashboard_stats()
            
            assert 'open_activities_count' in result
            assert 'month_revenue' in result
            assert 'month_costs' in result
            assert 'month_net_margin' in result
            assert 'recent_activities' in result
            assert 'top_agents' in result

    def test_dashboard_stats_open_activities(self, app, superadmin_user, agent):
        """Test counting open activities."""
        with app.app_context():
            from app import db
            
            today = date.today()
            
            # Create draft activity (open)
            draft = RevenueActivity(
                title='Draft Activity',
                date=today,
                status='bozza',
                total_revenue=Decimal('1000.00'),
                agent_id=agent.id,
                created_by=superadmin_user.id
            )
            
            # Create closed activity
            closed = RevenueActivity(
                title='Closed Activity',
                date=today,
                status='chiusa',
                total_revenue=Decimal('2000.00'),
                agent_id=agent.id,
                created_by=superadmin_user.id
            )
            
            db.session.add_all([draft, closed])
            db.session.commit()
            
            result = calc_dashboard_stats()
            assert result['open_activities_count'] >= 1

    def test_dashboard_stats_recent_activities(self, app, superadmin_user, agent):
        """Test recent activities list."""
        with app.app_context():
            from app import db
            
            today = date.today()
            
            for i in range(7):
                activity = RevenueActivity(
                    title=f'Activity {i+1}',
                    date=today,
                    status='bozza',
                    total_revenue=Decimal('1000.00'),
                    agent_id=agent.id,
                    created_by=superadmin_user.id
                )
                db.session.add(activity)
            
            db.session.commit()
            
            result = calc_dashboard_stats()
            assert len(result['recent_activities']) <= 5
