"""Centralized business logic for financial calculations."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date as _date
from . import db
from .models import ActivityCost, ActivityParticipant, RevenueActivity, TimesheetEntry, User
from .logging_config import get_logger

logger = get_logger(__name__)


TWO_PLACES = Decimal('0.01')
MAX_HOURS_PER_ENTRY = Decimal('24')
MAX_DECIMAL = Decimal('999999999.99')


def to_decimal(value):
    if value is None:
        return Decimal('0')
    return Decimal(str(value))


def calc_agent_compensation(total_revenue, agent_percentage):
    revenue = to_decimal(total_revenue)
    pct = to_decimal(agent_percentage)
    return (revenue * pct / Decimal('100')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calc_activity_totals(activity):
    """Calculate all financial totals for an activity."""
    try:
        revenue = to_decimal(activity.total_revenue)
        agent_pct = to_decimal(activity.agent_percentage)

        agent_comp = calc_agent_compensation(revenue, agent_pct)

        costs = ActivityCost.query.filter_by(activity_id=activity.id).all()
        total_operative = sum(to_decimal(c.amount) for c in costs if c.cost_type == 'operativo')
        total_extra = sum(to_decimal(c.amount) for c in costs if c.cost_type == 'extra')
        total_costs = total_operative + total_extra

        # Breakdown by line_type
        total_internal_consultant = sum(
            to_decimal(c.amount) for c in costs if c.line_type == 'internal_consultant'
        )
        total_external_consultant = sum(
            to_decimal(c.amount) for c in costs if c.line_type == 'external_consultant'
        )
        total_generic_costs = sum(
            to_decimal(c.amount) for c in costs if c.line_type == 'generic'
        )

        # Timesheet hours summary
        ts_entries = TimesheetEntry.query.filter_by(activity_id=activity.id).all()
        total_internal_hours = sum(to_decimal(t.hours) for t in ts_entries)

        participants = ActivityParticipant.query.filter_by(activity_id=activity.id).all()
        total_fixed_comp = sum(to_decimal(p.fixed_compensation) for p in participants)

        net_margin = revenue - agent_comp - total_costs
        distributable = net_margin - total_fixed_comp

        total_shares = sum(to_decimal(p.work_share) for p in participants)

        participant_details = []
        for p in participants:
            fixed = to_decimal(p.fixed_compensation)
            share = to_decimal(p.work_share)

            if total_shares > 0 and distributable > 0:
                proportional = (distributable * share / total_shares).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            else:
                proportional = Decimal('0')

            total_due = fixed + proportional
            participant_details.append({
                'id': p.id,
                'name': p.participant_name,
                'role': p.role_description,
                'work_share': share,
                'fixed_compensation': fixed,
                'proportional_share': proportional,
                'total_due': total_due,
            })

        logger.debug(
            f'Activity totals calculated: activity_id={activity.id}, revenue={revenue}, '
            f'total_costs={total_costs}, net_margin={net_margin}'
        )
        return {
            'revenue': revenue,
            'agent_percentage': agent_pct,
            'agent_compensation': agent_comp,
            'total_operative_costs': total_operative,
            'total_extra_costs': total_extra,
            'total_costs': total_costs,
            'total_internal_consultant_costs': total_internal_consultant,
            'total_external_consultant_costs': total_external_consultant,
            'total_generic_costs': total_generic_costs,
            'total_internal_hours': total_internal_hours,
            'net_margin': net_margin,
            'total_fixed_compensations': total_fixed_comp,
            'distributable_residual': distributable,
            'total_shares': total_shares,
            'participants': participant_details,
        }
    except Exception as e:
        logger.error(f'Error calculating activity totals for activity_id={activity.id}: {str(e)}', exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Timesheet service functions
# ---------------------------------------------------------------------------

class TimesheetValidationError(ValueError):
    pass


def _validate_timesheet_input(user, activity_id, work_date, hours, description, hourly_rate_snapshot=None):
    """Validate inputs for creating/updating a timesheet entry."""
    if activity_id is None:
        raise TimesheetValidationError('Attività obbligatoria')

    activity = db.session.get(RevenueActivity, activity_id)
    if activity is None:
        raise TimesheetValidationError('Attività non trovata')

    if work_date is None:
        raise TimesheetValidationError('Data obbligatoria')

    hours_d = to_decimal(hours)
    if hours_d <= Decimal('0'):
        raise TimesheetValidationError('Le ore devono essere maggiori di 0')
    if hours_d > MAX_HOURS_PER_ENTRY:
        raise TimesheetValidationError('Le ore non possono superare 24 per voce')
    VALID_HOURS = {Decimal('0.5'), Decimal('1'), Decimal('1.5')}
    if hours_d not in VALID_HOURS:
        raise TimesheetValidationError('Le ore devono essere 0.5, 1 oppure 1.5')

    if not description or not description.strip():
        raise TimesheetValidationError('Descrizione obbligatoria')

    if hourly_rate_snapshot is not None:
        rate = to_decimal(hourly_rate_snapshot)
        if rate < Decimal('0'):
            raise TimesheetValidationError('La tariffa oraria non può essere negativa')

    # Rate from user if not explicitly provided
    rate = hourly_rate_snapshot if hourly_rate_snapshot is not None else (
        user.hourly_cost_rate if user.hourly_cost_rate is not None else None
    )
    if rate is None or to_decimal(rate) < Decimal('0'):
        raise TimesheetValidationError(
            f'L\'utente {user.full_name} non ha una tariffa oraria configurata'
        )

    return activity, hours_d


def create_timesheet_entry(user_id, activity_id, work_date, hours, description, created_by_id):
    """Create a timesheet entry and rebuild the internal cost aggregate."""
    user = db.session.get(User, user_id)
    if user is None:
        raise TimesheetValidationError('Utente non trovato')

    if user.hourly_cost_rate is None or to_decimal(user.hourly_cost_rate) <= Decimal('0'):
        raise TimesheetValidationError(
            f'L\'utente {user.full_name} non ha una tariffa oraria configurata'
        )

    activity, hours_d = _validate_timesheet_input(
        user, activity_id, work_date, hours, description
    )

    rate_snapshot = to_decimal(user.hourly_cost_rate)

    entry = TimesheetEntry(
        user_id=user_id,
        activity_id=activity_id,
        work_date=work_date,
        hours=hours_d,
        description=description.strip(),
        hourly_rate_snapshot=rate_snapshot,
        created_by=created_by_id,
    )
    db.session.add(entry)
    db.session.flush()  # get entry.id before commit

    rebuild_internal_consultant_cost(activity_id, user_id)
    db.session.commit()

    logger.info(
        f'TimesheetEntry created: id={entry.id}, user_id={user_id}, '
        f'activity_id={activity_id}, hours={hours_d}, rate={rate_snapshot}'
    )
    return entry


def update_timesheet_entry(entry_id, requesting_user, hours=None, work_date=None,
                           description=None, activity_id=None):
    """Update a timesheet entry and rebuild affected cost aggregates."""
    entry = db.session.get(TimesheetEntry, entry_id)
    if entry is None:
        raise TimesheetValidationError('Voce timesheet non trovata')

    if not requesting_user.is_superadmin and entry.user_id != requesting_user.id:
        raise TimesheetValidationError('Non autorizzato a modificare questa voce')

    old_activity_id = entry.activity_id
    old_user_id = entry.user_id

    if hours is not None:
        hours_d = to_decimal(hours)
        if hours_d <= Decimal('0'):
            raise TimesheetValidationError('Le ore devono essere maggiori di 0')
        if hours_d > MAX_HOURS_PER_ENTRY:
            raise TimesheetValidationError('Le ore non possono superare 24 per voce')
        VALID_HOURS = {Decimal('0.5'), Decimal('1'), Decimal('1.5')}
        if hours_d not in VALID_HOURS:
            raise TimesheetValidationError('Le ore devono essere 0.5, 1 oppure 1.5')
        entry.hours = hours_d

    if work_date is not None:
        entry.work_date = work_date

    if description is not None:
        if not description.strip():
            raise TimesheetValidationError('Descrizione obbligatoria')
        entry.description = description.strip()

    if activity_id is not None and activity_id != old_activity_id:
        activity = db.session.get(RevenueActivity, activity_id)
        if activity is None:
            raise TimesheetValidationError('Attività non trovata')
        entry.activity_id = activity_id

    db.session.flush()

    # Rebuild cost aggregate for the new pair (and old pair if changed)
    rebuild_internal_consultant_cost(entry.activity_id, entry.user_id)
    if old_activity_id != entry.activity_id or old_user_id != entry.user_id:
        rebuild_internal_consultant_cost(old_activity_id, old_user_id)

    db.session.commit()
    logger.info(f'TimesheetEntry updated: id={entry_id}')
    return entry


def delete_timesheet_entry(entry_id, requesting_user):
    """Delete a timesheet entry and rebuild the cost aggregate."""
    entry = db.session.get(TimesheetEntry, entry_id)
    if entry is None:
        raise TimesheetValidationError('Voce timesheet non trovata')

    if not requesting_user.is_superadmin and entry.user_id != requesting_user.id:
        raise TimesheetValidationError('Non autorizzato a eliminare questa voce')

    activity_id = entry.activity_id
    user_id = entry.user_id

    db.session.delete(entry)
    db.session.flush()

    rebuild_internal_consultant_cost(activity_id, user_id)
    db.session.commit()
    logger.info(f'TimesheetEntry deleted: id={entry_id}, activity_id={activity_id}, user_id={user_id}')


def rebuild_internal_consultant_cost(activity_id, user_id):
    """Recompute (or remove) the single aggregated ActivityCost for a given
    activity + internal consultant pair.

    This is always a full rebuild from the source timesheets — never delta.
    Call this inside an open session; the caller is responsible for commit.
    """
    entries = TimesheetEntry.query.filter_by(
        activity_id=activity_id,
        user_id=user_id,
    ).all()

    existing_cost = ActivityCost.query.filter_by(
        activity_id=activity_id,
        source_user_id=user_id,
        line_type='internal_consultant',
        source_type='timesheet_aggregate',
    ).first()

    if not entries:
        # No timesheets left → remove the aggregate row if present
        if existing_cost is not None:
            db.session.delete(existing_cost)
            logger.debug(
                f'Removed internal_consultant cost aggregate: '
                f'activity_id={activity_id}, user_id={user_id}'
            )
        return

    # Aggregate: sum hours, sum (hours * rate_snapshot)
    total_hours = sum(to_decimal(e.hours) for e in entries)
    total_amount = sum(
        (to_decimal(e.hours) * to_decimal(e.hourly_rate_snapshot)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        for e in entries
    )

    user = db.session.get(User, user_id)
    user_name = user.full_name if user else f'Utente {user_id}'
    description = f'Costo consulenti interni - {user_name}'

    if existing_cost is None:
        cost = ActivityCost(
            activity_id=activity_id,
            category='consulenza',
            description=description,
            amount=total_amount,
            date=_date.today(),
            cost_type='operativo',
            line_type='internal_consultant',
            source_type='timesheet_aggregate',
            source_user_id=user_id,
            hours_total=total_hours,
            unit_rate=to_decimal(user.hourly_cost_rate) if user and user.hourly_cost_rate else None,
            is_auto_generated=True,
        )
        db.session.add(cost)
        logger.debug(
            f'Created internal_consultant cost aggregate: '
            f'activity_id={activity_id}, user_id={user_id}, '
            f'hours={total_hours}, amount={total_amount}'
        )
    else:
        existing_cost.description = description
        existing_cost.amount = total_amount
        existing_cost.hours_total = total_hours
        existing_cost.unit_rate = to_decimal(user.hourly_cost_rate) if user and user.hourly_cost_rate else None
        logger.debug(
            f'Updated internal_consultant cost aggregate: '
            f'activity_id={activity_id}, user_id={user_id}, '
            f'hours={total_hours}, amount={total_amount}'
        )


def get_internal_consultant_cost(activity_id, user_id):
    """Return the aggregated ActivityCost for a given activity+user pair, or None."""
    return ActivityCost.query.filter_by(
        activity_id=activity_id,
        source_user_id=user_id,
        line_type='internal_consultant',
        source_type='timesheet_aggregate',
    ).first()


# ---------------------------------------------------------------------------
# Monthly report
# ---------------------------------------------------------------------------

def calc_monthly_report(year, month):
    """Calculate aggregated monthly report."""
    from sqlalchemy import extract

    activities = RevenueActivity.query.filter(
        extract('year', RevenueActivity.date) == year,
        extract('month', RevenueActivity.date) == month,
        RevenueActivity.status == 'chiusa',
    ).order_by(RevenueActivity.date.desc()).all()

    total_revenue = Decimal('0')
    total_costs = Decimal('0')
    total_extra = Decimal('0')
    total_agent_comp = Decimal('0')
    total_internal_consultant = Decimal('0')
    total_external_consultant = Decimal('0')
    total_internal_hours = Decimal('0')

    activity_details = []
    participant_totals = {}
    agent_totals = {}

    for act in activities:
        totals = calc_activity_totals(act)

        total_revenue += totals['revenue']
        total_costs += totals['total_costs']
        total_extra += totals['total_extra_costs']
        total_agent_comp += totals['agent_compensation']
        total_internal_consultant += totals['total_internal_consultant_costs']
        total_external_consultant += totals['total_external_consultant_costs']
        total_internal_hours += totals['total_internal_hours']

        if act.agent:
            agent_name = act.agent.full_name
            agent_totals[agent_name] = agent_totals.get(agent_name, Decimal('0')) + totals['agent_compensation']

        for pd in totals['participants']:
            name = pd['name']
            participant_totals[name] = participant_totals.get(name, Decimal('0')) + pd['total_due']

        activity_details.append({
            'activity': act,
            'totals': totals,
        })

    net_margin = total_revenue - total_agent_comp - total_costs

    agent_summary = [{'name': k, 'total': v} for k, v in sorted(agent_totals.items())]
    participant_summary = [{'name': k, 'total': v} for k, v in sorted(participant_totals.items())]

    return {
        'year': year,
        'month': month,
        'total_revenue': total_revenue,
        'total_costs': total_costs,
        'total_extra_costs': total_extra,
        'total_agent_compensations': total_agent_comp,
        'total_internal_consultant_costs': total_internal_consultant,
        'total_external_consultant_costs': total_external_consultant,
        'total_internal_hours': total_internal_hours,
        'net_margin': net_margin,
        'activities': activity_details,
        'agent_summary': agent_summary,
        'participant_summary': participant_summary,
    }


def calc_dashboard_stats():
    """Calculate dashboard statistics."""
    try:
        from datetime import date
        from sqlalchemy import extract, func

        today = date.today()
        current_month = today.month
        current_year = today.year

        open_activities = RevenueActivity.query.filter(
            RevenueActivity.status.in_(['bozza', 'confermata'])
        ).count()

        month_activities = RevenueActivity.query.filter(
            extract('year', RevenueActivity.date) == current_year,
            extract('month', RevenueActivity.date) == current_month,
        ).all()

        month_revenue = Decimal('0')
        month_costs = Decimal('0')
        agent_commissions = {}

        for act in month_activities:
            totals = calc_activity_totals(act)
            month_revenue += totals['revenue']
            month_costs += totals['total_costs']
            if act.agent:
                name = act.agent.full_name
                agent_commissions[name] = agent_commissions.get(name, Decimal('0')) + totals['agent_compensation']

        month_margin = month_revenue - month_costs - sum(agent_commissions.values())

        recent_activities = RevenueActivity.query.order_by(
            RevenueActivity.created_at.desc()
        ).limit(5).all()

        top_agents = sorted(agent_commissions.items(), key=lambda x: x[1], reverse=True)[:5]
        top_agents = [{'name': k, 'total': v} for k, v in top_agents]

        logger.debug(
            f'Dashboard stats calculated: open_activities={open_activities}, '
            f'month_revenue={month_revenue}, month_margin={month_margin}'
        )
        return {
            'open_activities': open_activities,
            'open_activities_count': open_activities,
            'month_revenue': month_revenue,
            'month_costs': month_costs,
            'month_margin': month_margin,
            'month_net_margin': month_margin,
            'recent_activities': recent_activities,
            'top_agents': top_agents,
            'current_month': current_month,
            'current_year': current_year,
        }
    except Exception as e:
        logger.error(f'Error calculating dashboard stats: {str(e)}', exc_info=True)
        raise
