"""Centralized audit logging service."""
import json
from datetime import datetime
from flask import request
from flask_login import current_user
from . import db
from .models import AuditLog
from .logging_config import get_logger

logger = get_logger(__name__)


def log_action(action_type, entity_type=None, entity_id=None, description='',
               old_values=None, new_values=None):
    """Record an audit log entry."""
    username = 'system'
    user_id = None

    if current_user and hasattr(current_user, 'username') and current_user.is_authenticated:
        username = current_user.username
        user_id = current_user.id

    ip_address = None
    try:
        ip_address = request.remote_addr
    except RuntimeError:
        pass

    entry = AuditLog(
        user_id=user_id,
        username=username,
        timestamp=datetime.utcnow(),
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description or '',
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        ip_address=ip_address,
    )
    db.session.add(entry)
    db.session.commit()
    
    logger.debug(f'Audit log recorded: action={action_type}, entity={entity_type}, entity_id={entity_id}, user={username}, ip={ip_address}')


def model_to_dict(obj, fields):
    """Convert model fields to a dictionary for audit comparison."""
    result = {}
    for f in fields:
        val = getattr(obj, f, None)
        if isinstance(val, bool) or val is None:
            result[f] = val
        else:
            result[f] = str(val)
    return result
