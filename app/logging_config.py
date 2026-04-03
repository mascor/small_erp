"""Centralized logging configuration with daily rotation."""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


def configure_logging(app, log_dir='logs'):
    """Configure application logging with daily rotation."""
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Remove existing handlers to avoid conflicts
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Define log files
    log_files = {
        'app.log': logging.INFO,
        'error.log': logging.ERROR,
        'debug.log': logging.DEBUG,
    }

    # Configure handlers
    for log_file, level in log_files.items():
        file_path = os.path.join(log_dir, log_file)
        
        # RotatingFileHandler - rotea a mezzanotte ogni giorno (maxBytes=0 disabilita rotazione per size)
        # Useremo TimedRotatingFileHandler per migliore rotazione giornaliera
        from logging.handlers import TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(
            filename=file_path,
            when='midnight',  # Rotazione a mezzanotte
            interval=1,        # Ogni 1 giorno
            backupCount=30,    # Mantieni ultimi 30 giorni di log
            encoding='utf-8'
        )
        handler.setLevel(level)
        handler.setFormatter(detailed_formatter)
        app.logger.addHandler(handler)

    # Also add console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)
    app.logger.addHandler(console_handler)

    # Set Flask app logger level
    app.logger.setLevel(logging.DEBUG)

    # Configure werkzeug logger (Flask's request/response logger)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    for handler in app.logger.handlers:
        werkzeug_logger.addHandler(handler)

    # Log startup message
    app.logger.info('=' * 80)
    app.logger.info(f'Application started at {datetime.now().isoformat()}')
    app.logger.info('=' * 80)

    return app.logger


def get_logger(name):
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)
