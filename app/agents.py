from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import db
from .models import Agent
from .audit_service import log_action, model_to_dict
from .logging_config import get_logger
from .i18n import tr

logger = get_logger(__name__)

agents_bp = Blueprint('agents', __name__, url_prefix='/agents')

AGENT_FIELDS = ['first_name', 'default_percentage', 'is_active', 'notes']


@agents_bp.route('/')
@login_required
def index():
    agents = Agent.query.order_by(Agent.first_name).all()
    return render_template('agents/index.html', agents=agents)


@agents_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            agent_name = request.form.get('first_name', '').strip()
            if not agent_name:
                raise ValueError(tr('Il nome dell\'agente e obbligatorio.', 'Agent name is required.'))
            pct_str = request.form.get('default_percentage', '0').replace(',', '.')
            pct_val = Decimal(pct_str)
            if pct_val < 0 or pct_val > Decimal('100'):
                raise ValueError(tr('La percentuale deve essere tra 0 e 100.', 'Percentage must be between 0 and 100.'))

            agent = Agent(
                first_name=agent_name,
                default_percentage=pct_val,
                is_active='is_active' in request.form,
                notes=request.form.get('notes', '').strip(),
            )
            db.session.add(agent)
            db.session.commit()

            logger.info(f'Agent created: {agent.full_name} (ID: {agent.id}) by user {current_user.username}')
            log_action('create', 'Agent', agent.id,
                       f'Creato agente: {agent.full_name}',
                       new_values=model_to_dict(agent, AGENT_FIELDS))

            flash(tr('Agente creato con successo.', 'Agent created successfully.'), 'success')
            return redirect(url_for('agents.index'))
        except (ValueError, KeyError, InvalidOperation) as e:
            logger.error(f'Error creating agent: {str(e)}', exc_info=True)
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('agents/form.html', agent=None)


@agents_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    agent = db.get_or_404(Agent, id)

    if request.method == 'POST':
        try:
            old_values = model_to_dict(agent, AGENT_FIELDS)

            agent_name = request.form.get('first_name', '').strip()
            if not agent_name:
                raise ValueError(tr('Il nome dell\'agente e obbligatorio.', 'Agent name is required.'))
            pct_str = request.form.get('default_percentage', '0').replace(',', '.')
            pct_val = Decimal(pct_str)
            if pct_val < 0 or pct_val > Decimal('100'):
                raise ValueError(tr('La percentuale deve essere tra 0 e 100.', 'Percentage must be between 0 and 100.'))

            agent.first_name = agent_name
            agent.default_percentage = pct_val
            agent.is_active = 'is_active' in request.form
            agent.notes = request.form.get('notes', '').strip()

            db.session.commit()

            logger.info(f'Agent updated: {agent.full_name} (ID: {id}) by user {current_user.username}')
            log_action('update', 'Agent', agent.id,
                       f'Modificato agente: {agent.full_name}',
                       old_values=old_values,
                       new_values=model_to_dict(agent, AGENT_FIELDS))

            flash(tr('Agente aggiornato.', 'Agent updated.'), 'success')
            return redirect(url_for('agents.index'))
        except (ValueError, KeyError, InvalidOperation) as e:
            logger.error(f'Error updating agent {id}: {str(e)}', exc_info=True)
            flash(tr('Errore nei dati inseriti.', 'Invalid input data.'), 'error')

    return render_template('agents/form.html', agent=agent)


@agents_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    agent = db.get_or_404(Agent, id)
    name = agent.full_name

    if agent.activities.count() > 0:
        logger.warning(f'Attempt to delete agent {name} (ID: {id}) with linked activities by user {current_user.username}')
        flash(
            tr(
                f'Impossibile eliminare l\'agente "{name}": ha attività collegate.',
                f'Cannot delete agent "{name}": linked activities exist.'
            ),
            'error'
        )
        return redirect(url_for('agents.index'))

    logger.info(f'Agent deleted: {name} (ID: {id}) by user {current_user.username}')
    log_action('delete', 'Agent', agent.id,
               f'Eliminato agente: {name}',
               old_values=model_to_dict(agent, AGENT_FIELDS))

    db.session.delete(agent)
    db.session.commit()
    flash(tr(f'Agente "{name}" eliminato.', f'Agent "{name}" deleted.'), 'success')
    return redirect(url_for('agents.index'))
