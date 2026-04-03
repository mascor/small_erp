"""Initialize the database and create superadmin if not exists."""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app, db
from app.models import User


def init():
    app = create_app()
    with app.app_context():
        db.create_all()
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
            print(f'Superadmin creato: username=admin, password={password}')
        else:
            print('Superadmin già esistente.')


if __name__ == '__main__':
    init()
