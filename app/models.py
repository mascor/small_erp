from datetime import datetime, date
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_active(self):
        return self.is_active_user

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Agent(db.Model):
    __tablename__ = 'agents'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False, default='')
    email = db.Column(db.String(120))
    default_percentage = db.Column(db.Numeric(5, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    activities = db.relationship('RevenueActivity', backref='agent', lazy='dynamic')

    @property
    def full_name(self):
        parts = [self.first_name, self.last_name]
        return ' '.join(p for p in parts if p).strip()

    def __repr__(self):
        return f'<Agent {self.full_name}>'


class RevenueActivity(db.Model):
    __tablename__ = 'revenue_activities'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False, default='bozza')  # bozza, confermata, chiusa
    total_revenue = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=True)
    agent_percentage = db.Column(db.Numeric(5, 2), default=0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    costs = db.relationship('ActivityCost', backref='activity', lazy='dynamic', cascade='all, delete-orphan')
    participants = db.relationship('ActivityParticipant', backref='activity', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', backref='created_activities')

    STATUS_LABELS = {
        'bozza': 'Bozza',
        'confermata': 'Confermata',
        'chiusa': 'Chiusa'
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    def __repr__(self):
        return f'<RevenueActivity {self.title}>'


class ActivityCost(db.Model):
    __tablename__ = 'activity_costs'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('revenue_activities.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    date = db.Column(db.Date, nullable=False, default=date.today)
    cost_type = db.Column(db.String(20), nullable=False, default='operativo')  # operativo, extra
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    CATEGORIES = [
        ('materiale', 'Materiale'),
        ('trasporto', 'Trasporto'),
        ('consulenza', 'Consulenza'),
        ('marketing', 'Marketing'),
        ('spese_vive', 'Spese vive'),
        ('altro', 'Altro'),
    ]

    COST_TYPES = [
        ('operativo', 'Costo operativo'),
        ('extra', 'Spesa extra'),
    ]

    def __repr__(self):
        return f'<ActivityCost {self.description} {self.amount}>'


class ActivityParticipant(db.Model):
    __tablename__ = 'activity_participants'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('revenue_activities.id'), nullable=False)
    participant_name = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    role_description = db.Column(db.String(200))
    work_share = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    fixed_compensation = db.Column(db.Numeric(12, 2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='participations')

    def __repr__(self):
        return f'<ActivityParticipant {self.participant_name}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(80), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text, nullable=False)
    old_values = db.Column(db.Text)
    new_values = db.Column(db.Text)
    ip_address = db.Column(db.String(45))

    ACTION_TYPES = [
        'login', 'logout', 'create', 'update', 'delete', 'status_change',
        'user_create', 'user_update',
    ]

    def __repr__(self):
        return f'<AuditLog {self.action_type} by {self.username}>'
