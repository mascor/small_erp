from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import db
from .models import User
from .audit_service import log_action, model_to_dict
from .logging_config import get_logger
from .i18n import tr
from functools import wraps
import re

logger = get_logger(__name__)

users_bp = Blueprint('users', __name__, url_prefix='/users')

USER_FIELDS = ['username', 'is_active_user']


def _validate_password(password):
    """Validate password strength. Returns error message or None."""
    if len(password) < 12:
        return tr('La password deve avere almeno 12 caratteri.', 'Password must be at least 12 characters long.')
    if not re.search(r'[A-Z]', password):
        return tr('La password deve contenere almeno una maiuscola.', 'Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        return tr('La password deve contenere almeno una minuscola.', 'Password must contain at least one lowercase letter.')
    if not re.search(r'[0-9]', password):
        return tr('La password deve contenere almeno un numero.', 'Password must contain at least one digit.')
    return None


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash(tr('Accesso non autorizzato.', 'Unauthorized access.'), 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@users_bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.username).all()
    return render_template('users/index.html', users=users)


@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    if request.method == 'POST':
        username = request.form['username'].strip()

        if User.query.filter_by(username=username).first():
            logger.warning(f'Attempt to create user with duplicate username: {username} by user {current_user.username}')
            flash(tr('Username già in uso.', 'Username already in use.'), 'error')
            return render_template('users/form.html', user=None)

        password = request.form['password']
        pw_err = _validate_password(password)
        if pw_err:
            flash(pw_err, 'error')
            return render_template('users/form.html', user=None)

        user = User(
            username=username,
            # Keep required legacy fields populated while hiding them from UI.
            email=f'{username}@erp.local',
            full_name=username,
            role='operatore',
            is_active_user='is_active' in request.form,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        logger.info(f'User created: {username} (ID: {user.id}) by user {current_user.username}')
        log_action('user_create', 'User', user.id,
                   f'Creato utente: {user.username}',
                   new_values=model_to_dict(user, USER_FIELDS))

        flash(tr('Utente creato.', 'User created.'), 'success')
        return redirect(url_for('users.index'))

    return render_template('users/form.html', user=None)


@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    user = db.get_or_404(User, id)

    if user.is_superadmin and not current_user.is_superadmin:
        logger.warning(f'Attempt to edit superadmin by non-superadmin user: {current_user.username}')
        flash(tr('Non puoi modificare il superadmin.', 'You cannot edit the superadmin.'), 'error')
        return redirect(url_for('users.index'))

    if request.method == 'POST':
        old_values = model_to_dict(user, USER_FIELDS)

        user.is_active_user = 'is_active' in request.form

        new_password = request.form.get('password', '').strip()
        if new_password:
            pw_err = _validate_password(new_password)
            if pw_err:
                flash(pw_err, 'error')
                return render_template('users/form.html', user=user)
            user.set_password(new_password)
            logger.info(f'Password changed for user: {user.username} (ID: {user.id}) by user {current_user.username}')

        db.session.commit()

        logger.info(f'User updated: {user.username} (ID: {id}) by user {current_user.username}')
        log_action('user_update', 'User', user.id,
                   f'Modificato utente: {user.username}',
                   old_values=old_values,
                   new_values=model_to_dict(user, USER_FIELDS))

        flash(tr('Utente aggiornato.', 'User updated.'), 'success')
        return redirect(url_for('users.index'))

    return render_template('users/form.html', user=user)
