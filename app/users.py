from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import db
from .models import User
from .audit_service import log_action, model_to_dict
from functools import wraps

users_bp = Blueprint('users', __name__, url_prefix='/users')

USER_FIELDS = ['username', 'email', 'full_name', 'role', 'is_active_user']


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Accesso non autorizzato.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@users_bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.full_name).all()
    return render_template('users/index.html', users=users)


@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()

        if User.query.filter_by(username=username).first():
            flash('Username già in uso.', 'error')
            return render_template('users/form.html', user=None)

        if User.query.filter_by(email=email).first():
            flash('Email già in uso.', 'error')
            return render_template('users/form.html', user=None)

        password = request.form['password']
        if len(password) < 6:
            flash('La password deve avere almeno 6 caratteri.', 'error')
            return render_template('users/form.html', user=None)

        role = request.form.get('role', 'operatore')
        if role == 'superadmin' and not current_user.is_superadmin:
            flash('Solo il superadmin può creare altri superadmin.', 'error')
            return render_template('users/form.html', user=None)

        user = User(
            username=username,
            email=email,
            full_name=request.form['full_name'].strip(),
            role=role,
            is_active_user='is_active' in request.form,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        log_action('user_create', 'User', user.id,
                   f'Creato utente: {user.username} (ruolo: {user.role})',
                   new_values=model_to_dict(user, USER_FIELDS))

        flash('Utente creato.', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/form.html', user=None)


@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    user = db.get_or_404(User, id)

    if user.is_superadmin and not current_user.is_superadmin:
        flash('Non puoi modificare il superadmin.', 'error')
        return redirect(url_for('users.index'))

    if request.method == 'POST':
        old_values = model_to_dict(user, USER_FIELDS)

        email = request.form['email'].strip()
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            flash('Email già in uso.', 'error')
            return render_template('users/form.html', user=user)

        user.email = email
        user.full_name = request.form['full_name'].strip()

        role = request.form.get('role', user.role)
        if role == 'superadmin' and not current_user.is_superadmin:
            flash('Solo il superadmin può assegnare il ruolo superadmin.', 'error')
        else:
            user.role = role

        user.is_active_user = 'is_active' in request.form

        new_password = request.form.get('password', '').strip()
        if new_password:
            if len(new_password) < 6:
                flash('La password deve avere almeno 6 caratteri.', 'error')
                return render_template('users/form.html', user=user)
            user.set_password(new_password)

        db.session.commit()

        log_action('user_update', 'User', user.id,
                   f'Modificato utente: {user.username}',
                   old_values=old_values,
                   new_values=model_to_dict(user, USER_FIELDS))

        flash('Utente aggiornato.', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/form.html', user=user)
