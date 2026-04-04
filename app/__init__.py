import os
from flask import Flask, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from .logging_config import configure_logging
from .i18n import get_lang, tr, status_label, role_label, SUPPORTED_LANGS

load_dotenv()

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = None
login_manager.login_message_category = 'warning'


def create_app(test_config=None):
    app = Flask(__name__)

    # Configure logging
    log_dir = os.environ.get('LOG_DIR', 'logs')
    configure_logging(app, log_dir)
    app.logger.info(f'Application initialized with logs directory: {log_dir}')

    db_path = os.environ.get('DATABASE_PATH', 'erp.db')
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    if not os.path.isabs(db_path):
        db_path = os.path.join(project_root, db_path)

    legacy_instance_db = os.path.join(project_root, 'instance', 'erp.db')
    if (
        os.path.basename(db_path) == 'erp.db'
        and os.path.exists(legacy_instance_db)
        and (not os.path.exists(db_path) or os.path.getsize(db_path) == 0)
    ):
        db_path = legacy_instance_db

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
    )

    if test_config:
        app.config.update(test_config)

    secret_key = app.config.get('SECRET_KEY')
    if not secret_key or len(secret_key) < 16:
        if not app.config.get('TESTING'):
            raise ValueError(
                "SECRET_KEY environment variable must be set (min 16 chars). "
                "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        app.config['SECRET_KEY'] = 'test-only-insecure-key-not-for-production'

    app.logger.info(f"Using database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        flash(tr('Effettua il login per accedere.', 'Please sign in to continue.'), 'warning')
        # Preserve only a relative path so auth.login can safely honor next.
        next_path = request.full_path if request.query_string else request.path
        return redirect(url_for('auth.login', next=next_path))

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError, SQLAlchemyError):
            app.logger.warning('Failed to load user from session; forcing anonymous context.')
            return None

    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .activities import activities_bp
    from .agents import agents_bp
    from .users import users_bp
    from .reports import reports_bp
    from .audit import audit_bp
    from .manual import manual_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(manual_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    @app.route('/set-language', methods=['POST'])
    def set_language():
        from urllib.parse import urlparse
        lang = request.form.get('lang', 'it')
        if lang in SUPPORTED_LANGS:
            session['lang'] = lang

        next_url = request.form.get('next') or request.referrer or url_for('dashboard.index')
        parsed = urlparse(next_url)
        if parsed.netloc or parsed.scheme:
            next_url = url_for('dashboard.index')
        return redirect(next_url)

    @app.context_processor
    def inject_i18n_helpers():
        from datetime import date as _date
        return {
            'current_lang': get_lang(),
            'tr': tr,
            'status_label': status_label,
            'role_label': role_label,
            'today': _date.today().isoformat(),
        }

    app.jinja_env.globals.update(
        tr=tr,
        status_label=status_label,
        role_label=role_label,
    )

    @app.template_filter('currency')
    def currency_filter(value):
        if value is None:
            return '0,00'
        return f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    @app.template_filter('percentage')
    def percentage_filter(value):
        if value is None:
            return '0,00%'
        return f'{value:.2f}%'.replace('.', ',')

    return app
