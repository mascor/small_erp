from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from .audit_service import log_action

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active_user:
            login_user(user)
            log_action('login', 'User', user.id, f'Login utente: {user.username}')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))

        flash('Credenziali non valide o utente disattivato.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_action('logout', 'User', current_user.id, f'Logout utente: {current_user.username}')
    logout_user()
    flash('Logout effettuato.', 'success')
    return redirect(url_for('auth.login'))
