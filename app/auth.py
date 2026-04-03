from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from .audit_service import log_action
from .logging_config import get_logger
from .i18n import tr

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__)


def _is_safe_url(target):
    """Validate that redirect target is a safe, relative URL."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        logger.debug(f'Login attempt for username: {username}')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active_user:
            session.clear()  # Prevent session fixation
            login_user(user)
            session.permanent = True
            logger.info(f'User logged in successfully: {user.username} (ID: {user.id})')
            log_action('login', 'User', user.id, f'Login utente: {user.username}')
            next_page = request.args.get('next')
            if not _is_safe_url(next_page):
                next_page = None
            return redirect(next_page or url_for('dashboard.index'))

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
