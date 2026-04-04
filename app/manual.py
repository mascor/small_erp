from flask import Blueprint, render_template
from flask_login import login_required

manual_bp = Blueprint('manual', __name__)


@manual_bp.route('/manual')
@login_required
def index():
    return render_template('manual.html')
