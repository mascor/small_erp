from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required
from .services import calc_monthly_report

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

MONTHS_IT = {
    1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
    5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
    9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
}


@reports_bp.route('/')
@login_required
def index():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    report = calc_monthly_report(year, month)
    report['month_name'] = MONTHS_IT.get(month, '')

    years = list(range(today.year - 5, today.year + 2))

    return render_template('reports/index.html',
                           report=report,
                           months=MONTHS_IT,
                           years=years,
                           selected_year=year,
                           selected_month=month)
