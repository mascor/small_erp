from decimal import Decimal, InvalidOperation
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import db
from .models import RevenueActivity, Agent, ActivityCost, ActivityParticipant, User
from .services import calc_activity_totals
from .audit_service import log_action, model_to_dict
from .logging_config import get_logger
from .i18n import tr

logger = get_logger(__name__)

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')

ACTIVITY_FIELDS = ['title', 'description', 'date', 'status', 'total_revenue',
                    'agent_id', 'agent_percentage', 'notes']


VALID_STATUSES = {'bozza', 'confermata', 'chiusa'}
VALID_COST_CATEGORIES = {'materiale', 'trasporto', 'consulenza', 'marketing', 'spese_vive', 'altro'}
VALID_COST_TYPES = {'operativo', 'extra'}
MAX_DECIMAL = Decimal('999999999.99')


def _validate_decimal(value_str, field_name, allow_negative=False, max_value=None):
    """Parse and validate a decimal value from form input."""
    d = Decimal(value_str.replace(',', '.'))
    if not allow_negative and d < 0:
        raise ValueError(f'{field_name}: valore negativo non ammesso')
    upper = max_value if max_value is not None else MAX_DECIMAL
    if d > upper:
        raise ValueError(f'{field_name}: valore troppo grande')
    return d


def _require_non_empty(value, field_name):
    """Ensure a stripped string is not empty."""
    if not value or not value.strip():
        raise ValueError(f'{field_name}: campo obbligatorio')
    return value.strip()


def _can_modify_activity(activity):
    """Check if current user can modify the activity."""
    return current_user.is_admin or activity.created_by == current_user.id


@activities_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    agent_filter = request.args.get('agent_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('q', '').strip()

    query = RevenueActivity.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    if agent_filter:
        query = query.filter_by(agent_id=int(agent_filter))
    if date_from:
        query = query.filter(RevenueActivity.date >= date_from)
    if date_to:
        query = query.filter(RevenueActivity.date <= date_to)
    if search:
        query = query.filter(RevenueActivity.title.ilike(f'%{search}%'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(RevenueActivity.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    agents = Agent.query.filter_by(is_active=True).order_by(Agent.first_name).all()

    filters = {
        'status': status_filter,
        'agent_id': agent_filter,
        'date_from': date_from,
        'date_to': date_to,
        'q': search,
    }
    return render_template('activities/index.html',
                           activities=pagination.items,
                           pagination=pagination,
                           agents_list=agents,
                           filters=filters)


@activities_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    agents = Agent.query.filter_by(is_active=True).order_by(Agent.first_name).all()

    if request.method == 'POST':
        try:
            status = request.form.get('status', 'bozza')
            if status not in VALID_STATUSES:
                status = 'bozza'

            title = _require_non_empty(request.form.get('title', ''), tr('Titolo', 'Title'))
            date_str = _require_non_empty(request.form.get('date', ''), tr('Data', 'Date'))

            activity = RevenueActivity(
                title=title,
                description=request.form.get('description', '').strip(),
                date=date.fromisoformat(date_str),
                status=status,
                total_revenue=_validate_decimal(request.form['total_revenue'], tr('Ricavo totale', 'Total revenue')),
                agent_id=int(request.form['agent_id']) if request.form.get('agent_id') else None,
                agent_percentage=_validate_decimal(request.form.get('agent_percentage', '0'), tr('% agente', 'Agent %'), max_value=Decimal('100')),
                notes=request.form.get('notes', '').strip(),
                created_by=current_user.id,
            )
            db.session.add(activity)
            db.session.commit()

            logger.info(f'Activity created: {activity.title} (ID: {activity.id}) by user {current_user.username}')
            log_action('create', 'RevenueActivity', activity.id,
                       f'Creata attività: {activity.title}',
                       new_values=model_to_dict(activity, ACTIVITY_FIELDS))

            flash(tr('Attività creata con successo.', 'Activity created successfully.'), 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError, InvalidOperation) as e:
            logger.error(f'Error creating activity: {str(e)}', exc_info=True)
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('activities/form.html', activity=None, agents=agents)


@activities_bp.route('/<int:id>')
@login_required
def detail(id):
    activity = db.get_or_404(RevenueActivity, id)
    totals = calc_activity_totals(activity)
    return render_template('activities/detail.html', activity=activity, totals=totals)


@activities_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    activity = db.get_or_404(RevenueActivity, id)
    if not _can_modify_activity(activity):
        flash(tr('Non autorizzato a modificare questa attività.', 'Not authorized to modify this activity.'), 'error')
        return redirect(url_for('activities.index'))
    agents = Agent.query.filter_by(is_active=True).order_by(Agent.first_name).all()

    if request.method == 'POST':
        try:
            old_values = model_to_dict(activity, ACTIVITY_FIELDS)
            old_status = activity.status

            status = request.form.get('status', 'bozza')
            if status not in VALID_STATUSES:
                status = 'bozza'

            title = _require_non_empty(request.form.get('title', ''), tr('Titolo', 'Title'))
            date_str = _require_non_empty(request.form.get('date', ''), tr('Data', 'Date'))

            activity.title = title
            activity.description = request.form.get('description', '').strip()
            activity.date = date.fromisoformat(date_str)
            activity.status = status
            activity.total_revenue = _validate_decimal(request.form['total_revenue'], tr('Ricavo totale', 'Total revenue'))
            activity.agent_id = int(request.form['agent_id']) if request.form.get('agent_id') else None
            activity.agent_percentage = _validate_decimal(request.form.get('agent_percentage', '0'), tr('% agente', 'Agent %'), max_value=Decimal('100'))
            activity.notes = request.form.get('notes', '').strip()

            db.session.commit()

            action = 'status_change' if old_status != activity.status else 'update'
            logger.info(f'Activity updated: {activity.title} (ID: {activity.id}) - Action: {action} by user {current_user.username}')
            log_action(action, 'RevenueActivity', activity.id,
                       f'Modificata attività: {activity.title}',
                       old_values=old_values,
                       new_values=model_to_dict(activity, ACTIVITY_FIELDS))

            flash(tr('Attività aggiornata.', 'Activity updated.'), 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError, InvalidOperation) as e:
            logger.error(f'Error updating activity {id}: {str(e)}', exc_info=True)
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('activities/form.html', activity=activity, agents=agents)


@activities_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    activity = db.get_or_404(RevenueActivity, id)
    if not _can_modify_activity(activity):
        flash(tr('Non autorizzato a eliminare questa attività.', 'Not authorized to delete this activity.'), 'error')
        return redirect(url_for('activities.index'))
    title = activity.title

    logger.info(f'Activity deleted: {title} (ID: {id}) by user {current_user.username}')
    log_action('delete', 'RevenueActivity', activity.id,
               f'Eliminata attività: {title}',
               old_values=model_to_dict(activity, ACTIVITY_FIELDS))

    db.session.delete(activity)
    db.session.commit()
    flash(tr(f'Attività "{title}" eliminata.', f'Activity "{title}" deleted.'), 'success')
    return redirect(url_for('activities.index'))


@activities_bp.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    ids = request.form.getlist('activity_ids')
    if not ids:
        flash(tr('Nessuna attività selezionata.', 'No activities selected.'), 'warning')
        return redirect(url_for('activities.index'))

    deleted = 0
    for aid in ids:
        try:
            activity = db.session.get(RevenueActivity, int(aid))
        except (ValueError, TypeError):
            continue
        if activity is None:
            continue
        if not _can_modify_activity(activity):
            continue
        logger.info(f'Activity bulk-deleted: {activity.title} (ID: {activity.id}) by user {current_user.username}')
        log_action('delete', 'RevenueActivity', activity.id,
                   f'Eliminata attività (bulk): {activity.title}',
                   old_values=model_to_dict(activity, ACTIVITY_FIELDS))
        db.session.delete(activity)
        deleted += 1

    db.session.commit()
    flash(tr(f'{deleted} attività eliminate.', f'{deleted} activities deleted.'), 'success')
    return redirect(url_for('activities.index'))


# --- Costs sub-routes ---

COST_FIELDS = ['category', 'description', 'amount', 'date', 'cost_type', 'notes']


@activities_bp.route('/<int:id>/costs/add', methods=['GET', 'POST'])
@login_required
def add_cost(id):
    activity = db.get_or_404(RevenueActivity, id)

    if request.method == 'POST':
        try:
            cost_desc = _require_non_empty(request.form.get('description', ''), tr('Descrizione', 'Description'))
            cost_date_str = _require_non_empty(request.form.get('date', ''), tr('Data', 'Date'))

            cost = ActivityCost(
                activity_id=activity.id,
                category=request.form['category'] if request.form['category'] in VALID_COST_CATEGORIES else 'altro',
                description=cost_desc,
                amount=_validate_decimal(request.form['amount'], tr('Importo', 'Amount')),
                date=date.fromisoformat(cost_date_str),
                cost_type=request.form.get('cost_type', 'operativo') if request.form.get('cost_type') in VALID_COST_TYPES else 'operativo',
                notes=request.form.get('notes', '').strip(),
            )
            db.session.add(cost)
            db.session.commit()

            logger.info(f'Cost added: {cost.description} ({cost.amount}) to activity {activity.title} (ID: {activity.id}) by user {current_user.username}')
            log_action('create', 'ActivityCost', cost.id,
                       f'Aggiunto costo "{cost.description}" all\'attività "{activity.title}"',
                       new_values=model_to_dict(cost, COST_FIELDS))

            flash(tr('Costo aggiunto.', 'Cost added.'), 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError, InvalidOperation) as e:
            logger.error(f'Error adding cost to activity {id}: {str(e)}', exc_info=True)
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('activities/cost_form.html', activity=activity, cost=None)


@activities_bp.route('/<int:id>/costs/<int:cost_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_cost(id, cost_id):
    activity = db.get_or_404(RevenueActivity, id)
    cost = db.get_or_404(ActivityCost, cost_id)

    if request.method == 'POST':
        try:
            old_values = model_to_dict(cost, COST_FIELDS)

            cost_desc = _require_non_empty(request.form.get('description', ''), tr('Descrizione', 'Description'))
            cost_date_str = _require_non_empty(request.form.get('date', ''), tr('Data', 'Date'))

            cost.category = request.form['category'] if request.form['category'] in VALID_COST_CATEGORIES else 'altro'
            cost.description = cost_desc
            cost.amount = _validate_decimal(request.form['amount'], tr('Importo', 'Amount'))
            cost.date = date.fromisoformat(cost_date_str)
            cost.cost_type = request.form.get('cost_type', 'operativo') if request.form.get('cost_type') in VALID_COST_TYPES else 'operativo'
            cost.notes = request.form.get('notes', '').strip()

            db.session.commit()

            log_action('update', 'ActivityCost', cost.id,
                       f'Modificato costo "{cost.description}"',
                       old_values=old_values,
                       new_values=model_to_dict(cost, COST_FIELDS))

            flash(tr('Costo aggiornato.', 'Cost updated.'), 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError, InvalidOperation) as e:
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('activities/cost_form.html', activity=activity, cost=cost)


@activities_bp.route('/<int:id>/costs/<int:cost_id>/delete', methods=['POST'])
@login_required
def delete_cost(id, cost_id):
    cost = db.get_or_404(ActivityCost, cost_id)
    desc = cost.description

    logger.info(f'Cost deleted: {desc} (ID: {cost_id}) from activity {id} by user {current_user.username}')
    log_action('delete', 'ActivityCost', cost.id,
               f'Eliminato costo "{desc}"',
               old_values=model_to_dict(cost, COST_FIELDS))

    db.session.delete(cost)
    db.session.commit()
    flash(tr(f'Costo "{desc}" eliminato.', f'Cost "{desc}" deleted.'), 'success')
    return redirect(url_for('activities.detail', id=id))


# --- Participants sub-routes ---

PARTICIPANT_FIELDS = ['participant_name', 'role_description', 'work_share',
                      'fixed_compensation', 'notes']


@activities_bp.route('/<int:id>/participants/add', methods=['GET', 'POST'])
@login_required
def add_participant(id):
    activity = db.get_or_404(RevenueActivity, id)
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()

    if request.method == 'POST':
        try:
            p_name = _require_non_empty(request.form.get('participant_name', ''), tr('Nome partecipante', 'Participant name'))

            p = ActivityParticipant(
                activity_id=activity.id,
                participant_name=p_name,
                user_id=int(request.form['user_id']) if request.form.get('user_id') else None,
                role_description=request.form.get('role_description', '').strip(),
                work_share=_validate_decimal(request.form.get('work_share', '0'), tr('Quota lavoro', 'Work share')),
                fixed_compensation=_validate_decimal(request.form.get('fixed_compensation', '0'), tr('Compenso fisso', 'Fixed compensation')),
                notes=request.form.get('notes', '').strip(),
            )
            db.session.add(p)
            db.session.commit()

            log_action('create', 'ActivityParticipant', p.id,
                       f'Aggiunto partecipante "{p.participant_name}" all\'attività "{activity.title}"',
                       new_values=model_to_dict(p, PARTICIPANT_FIELDS))

            flash(tr('Partecipante aggiunto.', 'Participant added.'), 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError, InvalidOperation) as e:
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('activities/participant_form.html', activity=activity, participant=None, users=users)


@activities_bp.route('/<int:id>/participants/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
def edit_participant(id, pid):
    activity = db.get_or_404(RevenueActivity, id)
    p = db.get_or_404(ActivityParticipant, pid)
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()

    if request.method == 'POST':
        try:
            old_values = model_to_dict(p, PARTICIPANT_FIELDS)

            p_name = _require_non_empty(request.form.get('participant_name', ''), tr('Nome partecipante', 'Participant name'))

            p.participant_name = p_name
            p.user_id = int(request.form['user_id']) if request.form.get('user_id') else None
            p.role_description = request.form.get('role_description', '').strip()
            p.work_share = _validate_decimal(request.form.get('work_share', '0'), tr('Quota lavoro', 'Work share'))
            p.fixed_compensation = _validate_decimal(request.form.get('fixed_compensation', '0'), tr('Compenso fisso', 'Fixed compensation'))
            p.notes = request.form.get('notes', '').strip()

            db.session.commit()

            log_action('update', 'ActivityParticipant', p.id,
                       f'Modificato partecipante "{p.participant_name}"',
                       old_values=old_values,
                       new_values=model_to_dict(p, PARTICIPANT_FIELDS))

            flash(tr('Partecipante aggiornato.', 'Participant updated.'), 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError, InvalidOperation) as e:
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('activities/participant_form.html', activity=activity, participant=p, users=users)


@activities_bp.route('/<int:id>/participants/<int:pid>/delete', methods=['POST'])
@login_required
def delete_participant(id, pid):
    p = db.get_or_404(ActivityParticipant, pid)
    name = p.participant_name

    logger.info(f'Participant deleted: {name} (ID: {pid}) from activity {id} by user {current_user.username}')
    log_action('delete', 'ActivityParticipant', p.id,
               f'Eliminato partecipante "{name}"',
               old_values=model_to_dict(p, PARTICIPANT_FIELDS))

    db.session.delete(p)
    db.session.commit()
    flash(tr(f'Partecipante "{name}" rimosso.', f'Participant "{name}" removed.'), 'success')
    return redirect(url_for('activities.detail', id=id))
