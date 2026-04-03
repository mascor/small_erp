"""Run the Small ERP application."""
import logging
import os
from app import create_app

app = create_app()
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info(f'Starting Small ERP application (debug={debug})')
    app.run(debug=debug, host='127.0.0.1', port=5000)
