import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import AuditLog
from functools import wraps

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')

PER_PAGE = 25


def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_superadmin:
            flash('Accesso riservato al superadmin.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@audit_bp.route('/')
@login_required
@superadmin_required
def index():
    page = request.args.get('page', 1, type=int)
    username = request.args.get('username', '').strip()
    action_type = request.args.get('action_type', '').strip()
    entity_type = request.args.get('entity_type', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    query = AuditLog.query

    if username:
        query = query.filter(AuditLog.username.ilike(f'%{username}%'))
    if action_type:
        query = query.filter_by(action_type=action_type)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if date_from:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to:
        query = query.filter(AuditLog.timestamp <= date_to + ' 23:59:59')

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )

    action_types = ['login', 'logout', 'create', 'update', 'delete',
                    'status_change', 'user_create', 'user_update']
    entity_types = ['User', 'Agent', 'RevenueActivity', 'ActivityCost', 'ActivityParticipant']

    return render_template('audit/index.html',
                           logs=pagination.items,
                           pagination=pagination,
                           action_types=action_types,
                           entity_types=entity_types,
                           filters={
                               'username': username,
                               'action_type': action_type,
                               'entity_type': entity_type,
                               'date_from': date_from,
                               'date_to': date_to,
                           })


@audit_bp.route('/<int:id>')
@login_required
@superadmin_required
def detail(id):
    from . import db
    log = db.get_or_404(AuditLog, id)

    old_values = json.loads(log.old_values) if log.old_values else None
    new_values = json.loads(log.new_values) if log.new_values else None

    return render_template('audit/detail.html', log=log,
                           old_values=old_values, new_values=new_values)
