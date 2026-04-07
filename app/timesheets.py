"""Blueprint for personal timesheet views."""
from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import extract
from . import db
from .models import TimesheetEntry, RevenueActivity, User
from .logging_config import get_logger
from .i18n import tr

logger = get_logger(__name__)

timesheets_bp = Blueprint('timesheets', __name__, url_prefix='/timesheets')


@timesheets_bp.route('/')
@login_required
def my_timesheets():
    """Personal timesheet list with filters."""
    today = date.today()

    # Filters
    filter_month = request.args.get('month', today.month, type=int)
    filter_year = request.args.get('year', today.year, type=int)
    filter_activity_id = request.args.get('activity_id', '', type=str)

    # Superadmin can filter by user too
    filter_user_id = None
    if current_user.is_superadmin:
        filter_user_id = request.args.get('user_id', '', type=str)

    query = TimesheetEntry.query

    if current_user.is_superadmin and filter_user_id:
        try:
            query = query.filter_by(user_id=int(filter_user_id))
        except ValueError:
            pass
    elif not current_user.is_superadmin:
        query = query.filter_by(user_id=current_user.id)

    if filter_month and filter_year:
        query = query.filter(
            extract('year', TimesheetEntry.work_date) == filter_year,
            extract('month', TimesheetEntry.work_date) == filter_month,
        )

    if filter_activity_id:
        try:
            query = query.filter_by(activity_id=int(filter_activity_id))
        except ValueError:
            pass

    entries = query.order_by(TimesheetEntry.work_date.desc()).all()

    # Activity list for filter dropdown
    if current_user.is_superadmin:
        activities = RevenueActivity.query.order_by(RevenueActivity.title).all()
        users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    else:
        activities = RevenueActivity.query.order_by(RevenueActivity.title).all()
        users = []

    # Year options for filter
    years = list(range(today.year - 3, today.year + 2))

    from decimal import Decimal
    total_hours = sum(Decimal(str(e.hours)) for e in entries)
    total_cost = sum(Decimal(str(e.hours)) * Decimal(str(e.hourly_rate_snapshot)) for e in entries)

    return render_template(
        'timesheets/my_timesheets.html',
        entries=entries,
        activities=activities,
        users=users,
        total_hours=total_hours,
        total_cost=total_cost,
        filter_month=filter_month,
        filter_year=filter_year,
        filter_activity_id=filter_activity_id,
        filter_user_id=filter_user_id or '',
        years=years,
    )
