import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Effettua il login per accedere.'
login_manager.login_message_category = 'warning'


def create_app():
    app = Flask(__name__)

    db_path = os.environ.get('DATABASE_PATH', 'erp.db')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-fallback-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .activities import activities_bp
    from .agents import agents_bp
    from .users import users_bp
    from .reports import reports_bp
    from .audit import audit_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)

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
