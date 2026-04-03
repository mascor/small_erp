from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import db
from .models import RevenueActivity, Agent, ActivityCost, ActivityParticipant, User
from .services import calc_activity_totals
from .audit_service import log_action, model_to_dict

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')

ACTIVITY_FIELDS = ['title', 'description', 'date', 'status', 'total_revenue',
                    'agent_id', 'agent_percentage', 'notes']


@activities_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    query = RevenueActivity.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    activities = query.order_by(RevenueActivity.date.desc()).all()
    return render_template('activities/index.html', activities=activities, status_filter=status_filter)


@activities_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    agents = Agent.query.filter_by(is_active=True).order_by(Agent.last_name).all()

    if request.method == 'POST':
        try:
            activity = RevenueActivity(
                title=request.form['title'].strip(),
                description=request.form.get('description', '').strip(),
                date=date.fromisoformat(request.form['date']),
                status=request.form.get('status', 'bozza'),
                total_revenue=Decimal(request.form['total_revenue'].replace(',', '.')),
                agent_id=int(request.form['agent_id']) if request.form.get('agent_id') else None,
                agent_percentage=Decimal(request.form.get('agent_percentage', '0').replace(',', '.')),
                notes=request.form.get('notes', '').strip(),
                created_by=current_user.id,
            )
            db.session.add(activity)
            db.session.commit()

            log_action('create', 'RevenueActivity', activity.id,
                       f'Creata attività: {activity.title}',
                       new_values=model_to_dict(activity, ACTIVITY_FIELDS))

            flash('Attività creata con successo.', 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError) as e:
            flash(f'Errore nei dati inseriti: {e}', 'error')

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
    agents = Agent.query.filter_by(is_active=True).order_by(Agent.last_name).all()

    if request.method == 'POST':
        try:
            old_values = model_to_dict(activity, ACTIVITY_FIELDS)
            old_status = activity.status

            activity.title = request.form['title'].strip()
            activity.description = request.form.get('description', '').strip()
            activity.date = date.fromisoformat(request.form['date'])
            activity.status = request.form.get('status', 'bozza')
            activity.total_revenue = Decimal(request.form['total_revenue'].replace(',', '.'))
            activity.agent_id = int(request.form['agent_id']) if request.form.get('agent_id') else None
            activity.agent_percentage = Decimal(request.form.get('agent_percentage', '0').replace(',', '.'))
            activity.notes = request.form.get('notes', '').strip()

            db.session.commit()

            action = 'status_change' if old_status != activity.status else 'update'
            log_action(action, 'RevenueActivity', activity.id,
                       f'Modificata attività: {activity.title}',
                       old_values=old_values,
                       new_values=model_to_dict(activity, ACTIVITY_FIELDS))

            flash('Attività aggiornata.', 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError) as e:
            flash(f'Errore nei dati inseriti: {e}', 'error')

    return render_template('activities/form.html', activity=activity, agents=agents)


@activities_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    activity = db.get_or_404(RevenueActivity, id)
    title = activity.title

    log_action('delete', 'RevenueActivity', activity.id,
               f'Eliminata attività: {title}',
               old_values=model_to_dict(activity, ACTIVITY_FIELDS))

    db.session.delete(activity)
    db.session.commit()
    flash(f'Attività "{title}" eliminata.', 'success')
    return redirect(url_for('activities.index'))


# --- Costs sub-routes ---

COST_FIELDS = ['category', 'description', 'amount', 'date', 'cost_type', 'notes']


@activities_bp.route('/<int:id>/costs/add', methods=['GET', 'POST'])
@login_required
def add_cost(id):
    activity = db.get_or_404(RevenueActivity, id)

    if request.method == 'POST':
        try:
            cost = ActivityCost(
                activity_id=activity.id,
                category=request.form['category'],
                description=request.form['description'].strip(),
                amount=Decimal(request.form['amount'].replace(',', '.')),
                date=date.fromisoformat(request.form['date']),
                cost_type=request.form.get('cost_type', 'operativo'),
                notes=request.form.get('notes', '').strip(),
            )
            db.session.add(cost)
            db.session.commit()

            log_action('create', 'ActivityCost', cost.id,
                       f'Aggiunto costo "{cost.description}" all\'attività "{activity.title}"',
                       new_values=model_to_dict(cost, COST_FIELDS))

            flash('Costo aggiunto.', 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError) as e:
            flash(f'Errore: {e}', 'error')

    return render_template('activities/cost_form.html', activity=activity, cost=None)


@activities_bp.route('/<int:id>/costs/<int:cost_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_cost(id, cost_id):
    activity = db.get_or_404(RevenueActivity, id)
    cost = db.get_or_404(ActivityCost, cost_id)

    if request.method == 'POST':
        try:
            old_values = model_to_dict(cost, COST_FIELDS)

            cost.category = request.form['category']
            cost.description = request.form['description'].strip()
            cost.amount = Decimal(request.form['amount'].replace(',', '.'))
            cost.date = date.fromisoformat(request.form['date'])
            cost.cost_type = request.form.get('cost_type', 'operativo')
            cost.notes = request.form.get('notes', '').strip()

            db.session.commit()

            log_action('update', 'ActivityCost', cost.id,
                       f'Modificato costo "{cost.description}"',
                       old_values=old_values,
                       new_values=model_to_dict(cost, COST_FIELDS))

            flash('Costo aggiornato.', 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError) as e:
            flash(f'Errore: {e}', 'error')

    return render_template('activities/cost_form.html', activity=activity, cost=cost)


@activities_bp.route('/<int:id>/costs/<int:cost_id>/delete', methods=['POST'])
@login_required
def delete_cost(id, cost_id):
    cost = db.get_or_404(ActivityCost, cost_id)
    desc = cost.description

    log_action('delete', 'ActivityCost', cost.id,
               f'Eliminato costo "{desc}"',
               old_values=model_to_dict(cost, COST_FIELDS))

    db.session.delete(cost)
    db.session.commit()
    flash(f'Costo "{desc}" eliminato.', 'success')
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
            p = ActivityParticipant(
                activity_id=activity.id,
                participant_name=request.form['participant_name'].strip(),
                user_id=int(request.form['user_id']) if request.form.get('user_id') else None,
                role_description=request.form.get('role_description', '').strip(),
                work_share=Decimal(request.form.get('work_share', '0').replace(',', '.')),
                fixed_compensation=Decimal(request.form.get('fixed_compensation', '0').replace(',', '.')),
                notes=request.form.get('notes', '').strip(),
            )
            db.session.add(p)
            db.session.commit()

            log_action('create', 'ActivityParticipant', p.id,
                       f'Aggiunto partecipante "{p.participant_name}" all\'attività "{activity.title}"',
                       new_values=model_to_dict(p, PARTICIPANT_FIELDS))

            flash('Partecipante aggiunto.', 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError) as e:
            flash(f'Errore: {e}', 'error')

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

            p.participant_name = request.form['participant_name'].strip()
            p.user_id = int(request.form['user_id']) if request.form.get('user_id') else None
            p.role_description = request.form.get('role_description', '').strip()
            p.work_share = Decimal(request.form.get('work_share', '0').replace(',', '.'))
            p.fixed_compensation = Decimal(request.form.get('fixed_compensation', '0').replace(',', '.'))
            p.notes = request.form.get('notes', '').strip()

            db.session.commit()

            log_action('update', 'ActivityParticipant', p.id,
                       f'Modificato partecipante "{p.participant_name}"',
                       old_values=old_values,
                       new_values=model_to_dict(p, PARTICIPANT_FIELDS))

            flash('Partecipante aggiornato.', 'success')
            return redirect(url_for('activities.detail', id=activity.id))
        except (ValueError, KeyError) as e:
            flash(f'Errore: {e}', 'error')

    return render_template('activities/participant_form.html', activity=activity, participant=p, users=users)


@activities_bp.route('/<int:id>/participants/<int:pid>/delete', methods=['POST'])
@login_required
def delete_participant(id, pid):
    p = db.get_or_404(ActivityParticipant, pid)
    name = p.participant_name

    log_action('delete', 'ActivityParticipant', p.id,
               f'Eliminato partecipante "{name}"',
               old_values=model_to_dict(p, PARTICIPANT_FIELDS))

    db.session.delete(p)
    db.session.commit()
    flash(f'Partecipante "{name}" rimosso.', 'success')
    return redirect(url_for('activities.detail', id=id))
