"""Initialize the database and create superadmin if not exists."""
import os
import logging
import secrets
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

            # Migration: add must_change_password column if missing (existing DBs)
            from sqlalchemy import text
            with db.engine.connect() as conn:
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
                if 'must_change_password' not in cols:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"
                    ))
                    conn.commit()
                    logger.info('Migration: added must_change_password column to users')
                    print('Migrazione: aggiunta colonna must_change_password agli utenti.')

            env_password = os.environ.get('SUPERADMIN_PASSWORD')
            if not env_password:
                raise ValueError('SUPERADMIN_PASSWORD must be set in .env')

            # The real superadmin password is read from .env at login time.
            # Store only a random non-recoverable hash in DB.
            placeholder_password = secrets.token_urlsafe(64)
            superadmin = User.query.filter_by(username='admin').first()
            if not superadmin:
                superadmin = User(
                    username='admin',
                    email='admin@erp.local',
                    full_name='Super Admin',
                    is_superadmin=True,
                    is_active_user=True,
                )
                superadmin.set_password(placeholder_password)
                db.session.add(superadmin)
                db.session.commit()
                logger.info(f'Superadmin created: username=admin')
                print('Superadmin creato: username=admin (password gestita da .env).')
            else:
                changed = False
                if not superadmin.is_superadmin:
                    superadmin.is_superadmin = True
                    changed = True
                if not superadmin.is_active_user:
                    superadmin.is_active_user = True
                    changed = True

                superadmin.set_password(placeholder_password)
                changed = True

                if changed:
                    db.session.commit()
                    logger.info('Superadmin account realigned: credentials managed by environment')
                else:
                    logger.info('Superadmin already exists')

                print('Superadmin già esistente (password gestita da .env).')
        except Exception as e:
            logger.error(f'Error initializing database: {str(e)}', exc_info=True)
            raise


if __name__ == '__main__':
    init()
