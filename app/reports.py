from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from .services import calc_monthly_report
from .logging_config import get_logger
from .i18n import month_name, month_options

logger = get_logger(__name__)

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    try:
        today = date.today()
        year = request.args.get('year', today.year, type=int)
        month = request.args.get('month', today.month, type=int)

        logger.debug(f'Report accessed for {year}-{month:02d} by user: {current_user.username}')
        report = calc_monthly_report(year, month)
        report['month_name'] = month_name(month)
        months = month_options()

        years = list(range(today.year - 5, today.year + 2))

        logger.debug(f'Report calculated successfully for {year}-{month:02d}')
        return render_template('reports/index.html',
                               report=report,
                               months=months,
                               years=years,
                               selected_year=year,
                               selected_month=month)
    except Exception as e:
        logger.error(f'Error generating report: {str(e)}', exc_info=True)
        raise
