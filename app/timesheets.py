"""Blueprint for personal timesheet views."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import extract
from . import db
from .models import TimesheetEntry, RevenueActivity, User
from .services import delete_timesheet_entry, TimesheetValidationError
from .audit_service import log_action
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
    filter_day = request.args.get('day', '', type=str)
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

    if filter_day:
        try:
            day_int = int(filter_day)
            if 1 <= day_int <= 31:
                query = query.filter(extract('day', TimesheetEntry.work_date) == day_int)
        except ValueError:
            pass

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
        filter_day=filter_day,
        filter_user_id=filter_user_id or '',
        years=years,
    )


@timesheets_bp.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_timesheets():
    """Delete one or more timesheet entries and redirect back to my_timesheets."""
    entry_ids = request.form.getlist('entry_ids', type=int)

    # Build redirect URL preserving active filters
    redirect_args = {}
    for param in ('month', 'year', 'day', 'activity_id', 'user_id'):
        val = request.form.get(f'filter_{param}', '')
        if val:
            redirect_args[param] = val

    if not entry_ids:
        flash(tr('Nessun timesheet selezionato.', 'No timesheets selected.'), 'error')
        return redirect(url_for('timesheets.my_timesheets', **redirect_args))

    deleted = 0
    skipped = 0
    for entry_id in entry_ids:
        entry = db.session.get(TimesheetEntry, entry_id)
        if entry is None:
            continue
        if not current_user.is_superadmin and entry.user_id != current_user.id:
            skipped += 1
            continue
        activity = db.session.get(RevenueActivity, entry.activity_id)
        if not current_user.is_superadmin and (activity is None or activity.status != 'confermata'):
            skipped += 1
            continue
        log_action('delete', 'TimesheetEntry', entry_id,
                   f'Eliminato timesheet ID {entry_id} per attività "{activity.title if activity else entry.activity_id}"',
                   old_values={
                       'user_id': entry.user_id,
                       'activity_id': entry.activity_id,
                       'work_date': str(entry.work_date),
                       'hours': str(entry.hours),
                       'description': entry.description,
                   })
        try:
            delete_timesheet_entry(entry_id, current_user)
            deleted += 1
        except TimesheetValidationError as e:
            flash(str(e), 'error')

    if deleted:
        msg_it = f'{deleted} timesheet eliminat{"o" if deleted == 1 else "i"}.'
        msg_en = f'{deleted} timesheet{"" if deleted == 1 else "s"} deleted.'
        flash(tr(msg_it, msg_en), 'success')
    if skipped:
        flash(tr(f'{skipped} voci non eliminate (permessi insufficienti).',
                 f'{skipped} entries skipped (insufficient permissions).'), 'warning')

    return redirect(url_for('timesheets.my_timesheets', **redirect_args))
