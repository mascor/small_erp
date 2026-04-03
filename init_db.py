"""Initialize the database and create superadmin if not exists."""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

from app import create_app, db
from app.models import User

logger = logging.getLogger(__name__)


def init():
    app = create_app()
    with app.app_context():
        try:
            db.create_all()
            logger.info('Database created successfully')
            print('Database creato con successo.')

            superadmin = User.query.filter_by(username='admin').first()
            if not superadmin:
                password = os.environ.get('SUPERADMIN_PASSWORD', 'admin123')
                superadmin = User(
                    username='admin',
                    email='admin@erp.local',
                    full_name='Super Admin',
                    role='superadmin',
                    is_active_user=True,
                )
                superadmin.set_password(password)
                db.session.add(superadmin)
                db.session.commit()
                logger.info(f'Superadmin created: username=admin')
                print(f'Superadmin creato: username=admin, password={password}')
            else:
                logger.info('Superadmin already exists')
                print('Superadmin già esistente.')
        except Exception as e:
            logger.error(f'Error initializing database: {str(e)}', exc_info=True)
            raise


if __name__ == '__main__':
    init()
