"""Seed the database with demo data for testing."""
from datetime import date, datetime
from decimal import Decimal
from app import create_app, db
from app.models import User, Agent, RevenueActivity, ActivityCost, ActivityParticipant, AuditLog


def seed():
    app = create_app()
    with app.app_context():
        # Check if data already exists
        if Agent.query.first():
            print('Dati demo già presenti. Seed non eseguito.')
            return

        # Create demo users
        op1 = User(username='mario.rossi', email='mario@erp.local',
                    full_name='Mario Rossi', role='operatore', is_active_user=True)
        op1.set_password('demo123')

        op2 = User(username='laura.bianchi', email='laura@erp.local',
                    full_name='Laura Bianchi', role='admin', is_active_user=True)
        op2.set_password('demo123')

        db.session.add_all([op1, op2])
        db.session.flush()

        # Create agents
        agents = [
            Agent(first_name='Marco', last_name='Verdi', email='marco.verdi@mail.it',
                  default_percentage=Decimal('10'), is_active=True, notes='Agente senior'),
            Agent(first_name='Anna', last_name='Neri', email='anna.neri@mail.it',
                  default_percentage=Decimal('8'), is_active=True, notes='Agente area Nord'),
            Agent(first_name='Luca', last_name='Gialli', email='luca.gialli@mail.it',
                  default_percentage=Decimal('12'), is_active=True, notes='Agente area Sud'),
        ]
        db.session.add_all(agents)
        db.session.flush()

        today = date.today()
        month = today.month
        year = today.year

        # Create revenue activities
        activities_data = [
            {
                'title': 'Progetto Sito Web Aziendale',
                'description': 'Realizzazione sito web corporate per azienda metalmeccanica',
                'date': date(year, month, 5),
                'status': 'confermata',
                'total_revenue': Decimal('15000'),
                'agent': agents[0],
                'agent_percentage': Decimal('10'),
                'costs': [
                    ('consulenza', 'Consulenza UX/UI', Decimal('1500'), 'operativo'),
                    ('materiale', 'Hosting e dominio', Decimal('200'), 'operativo'),
                    ('altro', 'Licenze software', Decimal('350'), 'extra'),
                ],
                'participants': [
                    ('Mario Rossi', op1.id, 'Sviluppatore Frontend', Decimal('50'), Decimal('500')),
                    ('Laura Bianchi', op2.id, 'Project Manager', Decimal('30'), Decimal('300')),
                    ('Paolo Conti', None, 'Sviluppatore Backend', Decimal('20'), Decimal('0')),
                ],
            },
            {
                'title': 'Campagna Marketing Digitale',
                'description': 'Gestione campagna social media per catena di ristoranti',
                'date': date(year, month, 10),
                'status': 'confermata',
                'total_revenue': Decimal('8000'),
                'agent': agents[1],
                'agent_percentage': Decimal('8'),
                'costs': [
                    ('marketing', 'Budget pubblicitario', Decimal('2000'), 'operativo'),
                    ('consulenza', 'Copywriting', Decimal('600'), 'operativo'),
                    ('spese_vive', 'Shooting fotografico', Decimal('800'), 'extra'),
                ],
                'participants': [
                    ('Laura Bianchi', op2.id, 'Social Media Manager', Decimal('60'), Decimal('0')),
                    ('Mario Rossi', op1.id, 'Graphic Designer', Decimal('40'), Decimal('200')),
                ],
            },
            {
                'title': 'Consulenza Strategica PMI',
                'description': 'Analisi e piano strategico triennale',
                'date': date(year, month, 15),
                'status': 'chiusa',
                'total_revenue': Decimal('25000'),
                'agent': agents[2],
                'agent_percentage': Decimal('12'),
                'costs': [
                    ('consulenza', 'Analisi di mercato esterna', Decimal('3000'), 'operativo'),
                    ('trasporto', 'Trasferte', Decimal('1200'), 'operativo'),
                    ('materiale', 'Report e documentazione', Decimal('500'), 'operativo'),
                    ('spese_vive', 'Pranzi di lavoro', Decimal('350'), 'extra'),
                ],
                'participants': [
                    ('Laura Bianchi', op2.id, 'Lead Consultant', Decimal('50'), Decimal('1000')),
                    ('Mario Rossi', op1.id, 'Analista', Decimal('30'), Decimal('0')),
                    ('Elena Ferrara', None, 'Senior Advisor', Decimal('20'), Decimal('2000')),
                ],
            },
            {
                'title': 'App Mobile E-commerce',
                'description': 'Sviluppo app iOS e Android per negozio online',
                'date': date(year, month, 2),
                'status': 'bozza',
                'total_revenue': Decimal('35000'),
                'agent': agents[0],
                'agent_percentage': Decimal('10'),
                'costs': [
                    ('consulenza', 'Design UX mobile', Decimal('4000'), 'operativo'),
                    ('materiale', 'Licenze Apple/Google Developer', Decimal('300'), 'operativo'),
                ],
                'participants': [
                    ('Paolo Conti', None, 'Mobile Developer', Decimal('50'), Decimal('0')),
                    ('Mario Rossi', op1.id, 'Backend Developer', Decimal('30'), Decimal('0')),
                    ('Laura Bianchi', op2.id, 'QA Lead', Decimal('20'), Decimal('0')),
                ],
            },
            {
                'title': 'Formazione Aziendale IT',
                'description': 'Corso di formazione su cybersecurity per 30 dipendenti',
                'date': date(year, month, 20),
                'status': 'confermata',
                'total_revenue': Decimal('6000'),
                'agent': agents[1],
                'agent_percentage': Decimal('8'),
                'costs': [
                    ('materiale', 'Materiale didattico', Decimal('400'), 'operativo'),
                    ('trasporto', 'Trasferta formatore', Decimal('250'), 'operativo'),
                    ('spese_vive', 'Coffee break', Decimal('150'), 'extra'),
                ],
                'participants': [
                    ('Mario Rossi', op1.id, 'Formatore', Decimal('70'), Decimal('500')),
                    ('Laura Bianchi', op2.id, 'Coordinamento', Decimal('30'), Decimal('0')),
                ],
            },
        ]

        admin = User.query.filter_by(username='admin').first()

        for data in activities_data:
            act = RevenueActivity(
                title=data['title'],
                description=data['description'],
                date=data['date'],
                status=data['status'],
                total_revenue=data['total_revenue'],
                agent_id=data['agent'].id,
                agent_percentage=data['agent_percentage'],
                created_by=admin.id if admin else None,
            )
            db.session.add(act)
            db.session.flush()

            for cat, desc, amount, ctype in data['costs']:
                cost = ActivityCost(
                    activity_id=act.id,
                    category=cat,
                    description=desc,
                    amount=amount,
                    date=data['date'],
                    cost_type=ctype,
                )
                db.session.add(cost)

            for name, uid, role, share, fixed in data['participants']:
                part = ActivityParticipant(
                    activity_id=act.id,
                    participant_name=name,
                    user_id=uid,
                    role_description=role,
                    work_share=share,
                    fixed_compensation=fixed,
                )
                db.session.add(part)

        # Add some audit logs
        sample_logs = [
            AuditLog(user_id=admin.id if admin else None, username='admin',
                     timestamp=datetime(year, month, 1, 9, 0),
                     action_type='login', entity_type='User',
                     description='Login utente: admin', ip_address='127.0.0.1'),
            AuditLog(user_id=admin.id if admin else None, username='admin',
                     timestamp=datetime(year, month, 1, 9, 5),
                     action_type='create', entity_type='Agent',
                     entity_id=agents[0].id,
                     description='Creato agente: Marco Verdi', ip_address='127.0.0.1'),
            AuditLog(user_id=admin.id if admin else None, username='admin',
                     timestamp=datetime(year, month, 1, 9, 10),
                     action_type='create', entity_type='RevenueActivity',
                     description='Creata attività: Progetto Sito Web Aziendale', ip_address='127.0.0.1'),
        ]
        db.session.add_all(sample_logs)

        db.session.commit()
        print('Dati demo inseriti con successo!')
        print(f'  - 2 utenti operativi (mario.rossi / laura.bianchi, password: demo123)')
        print(f'  - 3 agenti')
        print(f'  - 5 attività di ricavo con costi e partecipanti')
        print(f'  - 3 log di audit di esempio')


if __name__ == '__main__':
    seed()
