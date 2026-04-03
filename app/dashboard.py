from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .services import calc_dashboard_stats
from .logging_config import get_logger

logger = get_logger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    try:
        logger.debug(f'Dashboard accessed by user: {current_user.username}')
        stats = calc_dashboard_stats()
        logger.debug(f'Dashboard stats calculated successfully')
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f'Error loading dashboard: {str(e)}', exc_info=True)
        raise
