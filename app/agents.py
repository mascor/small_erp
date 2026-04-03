from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from . import db
from .models import Agent
from .audit_service import log_action, model_to_dict

agents_bp = Blueprint('agents', __name__, url_prefix='/agents')

AGENT_FIELDS = ['first_name', 'last_name', 'email', 'default_percentage', 'is_active', 'notes']


@agents_bp.route('/')
@login_required
def index():
    agents = Agent.query.order_by(Agent.last_name, Agent.first_name).all()
    return render_template('agents/index.html', agents=agents)


@agents_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            agent = Agent(
                first_name=request.form['first_name'].strip(),
                last_name=request.form['last_name'].strip(),
                email=request.form.get('email', '').strip(),
                default_percentage=Decimal(request.form.get('default_percentage', '0').replace(',', '.')),
                is_active='is_active' in request.form,
                notes=request.form.get('notes', '').strip(),
            )
            db.session.add(agent)
            db.session.commit()

            log_action('create', 'Agent', agent.id,
                       f'Creato agente: {agent.full_name}',
                       new_values=model_to_dict(agent, AGENT_FIELDS))

            flash('Agente creato con successo.', 'success')
            return redirect(url_for('agents.index'))
        except (ValueError, KeyError) as e:
            flash(f'Errore: {e}', 'error')

    return render_template('agents/form.html', agent=None)


@agents_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    agent = db.get_or_404(Agent, id)

    if request.method == 'POST':
        try:
            old_values = model_to_dict(agent, AGENT_FIELDS)

            agent.first_name = request.form['first_name'].strip()
            agent.last_name = request.form['last_name'].strip()
            agent.email = request.form.get('email', '').strip()
            agent.default_percentage = Decimal(request.form.get('default_percentage', '0').replace(',', '.'))
            agent.is_active = 'is_active' in request.form
            agent.notes = request.form.get('notes', '').strip()

            db.session.commit()

            log_action('update', 'Agent', agent.id,
                       f'Modificato agente: {agent.full_name}',
                       old_values=old_values,
                       new_values=model_to_dict(agent, AGENT_FIELDS))

            flash('Agente aggiornato.', 'success')
            return redirect(url_for('agents.index'))
        except (ValueError, KeyError) as e:
            flash(f'Errore: {e}', 'error')

    return render_template('agents/form.html', agent=agent)


@agents_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    agent = db.get_or_404(Agent, id)
    name = agent.full_name

    if agent.activities.count() > 0:
        flash(f'Impossibile eliminare l\'agente "{name}": ha attività collegate.', 'error')
        return redirect(url_for('agents.index'))

    log_action('delete', 'Agent', agent.id,
               f'Eliminato agente: {name}',
               old_values=model_to_dict(agent, AGENT_FIELDS))

    db.session.delete(agent)
    db.session.commit()
    flash(f'Agente "{name}" eliminato.', 'success')
    return redirect(url_for('agents.index'))
