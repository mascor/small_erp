"""Centralized business logic for financial calculations."""
from decimal import Decimal, ROUND_HALF_UP
from . import db
from .models import ActivityCost, ActivityParticipant, RevenueActivity


TWO_PLACES = Decimal('0.01')


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
    revenue = to_decimal(activity.total_revenue)
    agent_pct = to_decimal(activity.agent_percentage)

    agent_comp = calc_agent_compensation(revenue, agent_pct)

    costs = activity.costs.all()
    total_operative = sum(to_decimal(c.amount) for c in costs if c.cost_type == 'operativo')
    total_extra = sum(to_decimal(c.amount) for c in costs if c.cost_type == 'extra')
    total_costs = total_operative + total_extra

    participants = activity.participants.all()
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

    return {
        'revenue': revenue,
        'agent_percentage': agent_pct,
        'agent_compensation': agent_comp,
        'total_operative_costs': total_operative,
        'total_extra_costs': total_extra,
        'total_costs': total_costs,
        'net_margin': net_margin,
        'total_fixed_compensations': total_fixed_comp,
        'distributable_residual': distributable,
        'total_shares': total_shares,
        'participants': participant_details,
    }


def calc_monthly_report(year, month):
    """Calculate aggregated monthly report."""
    from sqlalchemy import extract

    activities = RevenueActivity.query.filter(
        extract('year', RevenueActivity.date) == year,
        extract('month', RevenueActivity.date) == month,
    ).order_by(RevenueActivity.date.desc()).all()

    total_revenue = Decimal('0')
    total_costs = Decimal('0')
    total_extra = Decimal('0')
    total_agent_comp = Decimal('0')

    activity_details = []
    participant_totals = {}
    agent_totals = {}

    for act in activities:
        totals = calc_activity_totals(act)

        total_revenue += totals['revenue']
        total_costs += totals['total_costs']
        total_extra += totals['total_extra_costs']
        total_agent_comp += totals['agent_compensation']

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
        'net_margin': net_margin,
        'activities': activity_details,
        'agent_summary': agent_summary,
        'participant_summary': participant_summary,
    }


def calc_dashboard_stats():
    """Calculate dashboard statistics."""
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

    return {
        'open_activities': open_activities,
        'month_revenue': month_revenue,
        'month_costs': month_costs,
        'month_margin': month_margin,
        'recent_activities': recent_activities,
        'top_agents': top_agents,
        'current_month': current_month,
        'current_year': current_year,
    }
