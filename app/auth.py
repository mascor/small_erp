import hmac
import os
import re
from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from . import limiter
from .models import User
from .audit_service import log_action
from .logging_config import get_logger
from .i18n import tr

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__)

# --- Account lockout state (in-memory, resets on restart) ---
_lockout_lock = Lock()
_failed_attempts: dict[str, dict] = {}  # {username: {count, locked_until}}

LOCKOUT_MAX_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def _is_locked(username: str) -> bool:
    with _lockout_lock:
        state = _failed_attempts.get(username)
        if not state:
            return False
        locked_until = state.get('locked_until')
        if locked_until and datetime.utcnow() < locked_until:
            return True
        # Lock expired — clear it
        if locked_until:
            _failed_attempts.pop(username, None)
        return False


def _record_failure(username: str) -> None:
    with _lockout_lock:
        state = _failed_attempts.setdefault(username, {'count': 0, 'locked_until': None})
        state['count'] += 1
        if state['count'] >= LOCKOUT_MAX_ATTEMPTS:
            state['locked_until'] = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            logger.warning(
                f'Account locked for {LOCKOUT_DURATION_MINUTES} min after '
                f'{LOCKOUT_MAX_ATTEMPTS} failed attempts: username={username}'
            )


def _clear_failures(username: str) -> None:
    with _lockout_lock:
        _failed_attempts.pop(username, None)


def _is_safe_url(target):
    """Validate that redirect target is a safe, relative URL."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme


def _is_valid_login(user, password):
    """Validate credentials, using .env for the admin superadmin account."""
    if not user or not user.is_active_user:
        return False

    if user.is_superadmin and user.username == 'admin':
        env_password = os.environ.get('SUPERADMIN_PASSWORD')
        if not env_password:
            logger.error('SUPERADMIN_PASSWORD is not configured; admin login is disabled')
            return False
        return hmac.compare_digest(password, env_password)

    return user.check_password(password)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        logger.debug(f'Login attempt for username: {username}')

        # Check lockout before touching the DB
        if _is_locked(username):
            logger.warning(
                f'Login blocked — account locked: username={username} IP={request.remote_addr}'
            )
            flash(tr('Credenziali non valide o utente disattivato.', 'Invalid credentials or disabled user.'), 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if _is_valid_login(user, password):
            _clear_failures(username)
            session.clear()  # Prevent session fixation
            login_user(user)
            session.permanent = True
            logger.info(f'User logged in successfully: {user.username} (ID: {user.id})')
            log_action('login', 'User', user.id, f'Login utente: {user.username}')
            next_page = request.args.get('next')
            if not _is_safe_url(next_page):
                next_page = None
            return redirect(next_page or url_for('dashboard.index'))

        _record_failure(username)
        logger.warning(f'Failed login attempt for username: {username} from IP: {request.remote_addr}')
        flash(tr('Credenziali non valide o utente disattivato.', 'Invalid credentials or disabled user.'), 'error')

    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    username = current_user.username
    logger.info(f'User logging out: {username} (ID: {current_user.id})')
    log_action('logout', 'User', current_user.id, f'Logout utente: {current_user.username}')
    logout_user()
    session.clear()
    flash(tr('Logout effettuato.', 'You have been logged out.'), 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    from . import db
    from .users import _validate_password

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if password != confirm:
            flash(tr('Le password non coincidono.', 'Passwords do not match.'), 'error')
            return render_template('change_password.html')

        err = _validate_password(password)
        if err:
            flash(err, 'error')
            return render_template('change_password.html')

        current_user.set_password(password)
        current_user.must_change_password = False
        db.session.commit()

        log_action('update', 'User', current_user.id,
                   f'Password cambiata da utente: {current_user.username}')
        logger.info(f'User changed password: {current_user.username} (ID: {current_user.id})')
        flash(tr('Password cambiata con successo.', 'Password changed successfully.'), 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('change_password.html')
