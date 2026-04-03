# Small ERP

Mini ERP locale per la gestione di ricavi, costi, agenti, partecipanti e ripartizione utili.

## Stack Tecnologico

- **Backend**: Python + Flask
- **Database**: SQLite (file locale)
- **ORM**: SQLAlchemy
- **Autenticazione**: Flask-Login
- **Frontend**: Jinja2 + CSS custom

## Setup Rapido

### 1. Crea ambiente virtuale

```bash
cd small_erp
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# oppure: venv\Scripts\activate  # Windows
```

### 2. Installa dipendenze

```bash
pip install -r requirements.txt
```

### 3. Configura variabili ambiente

```bash
cp .env.example .env
# Modifica .env con i tuoi valori:
# - SECRET_KEY: chiave segreta per le sessioni
# - SUPERADMIN_PASSWORD: password dell'admin iniziale
# - DATABASE_PATH: percorso del file SQLite (default: erp.db)
```

### 4. Inizializza database e superadmin

```bash
python init_db.py
```

Questo crea il database SQLite e il superadmin con le credenziali configurate in `.env`.

### 5. (Opzionale) Inserisci dati demo

```bash
python seed_demo.py
```

Inserisce agenti, attività, costi, partecipanti e log di audit di esempio.

### 6. Avvia il server

```bash
python run.py
```

L'applicazione sarà disponibile su **http://127.0.0.1:5000**

## Credenziali Default

| Utente | Username | Password | Ruolo |
|--------|----------|----------|-------|
| Admin | `admin` | `admin123` | Superadmin |
| Mario Rossi | `mario.rossi` | `demo123` | Operatore |
| Laura Bianchi | `laura.bianchi` | `demo123` | Admin |

*(Gli utenti demo vengono creati solo se si esegue `seed_demo.py`)*

## Funzionalità

- **Dashboard**: panoramica KPI del mese corrente
- **Attività di Ricavo**: gestione completa con costi, partecipanti e breakdown economico
- **Agenti**: anagrafica agenti con percentuale commissione predefinita
- **Report Mensili**: report aggregati per mese con riepilogo per agente e partecipante
- **Gestione Utenti**: creazione/modifica/disattivazione utenti con ruoli
- **Audit Log**: tracciamento completo di tutte le operazioni (solo superadmin)

## Ruoli

- **Superadmin**: accesso completo, gestione utenti, audit log
- **Admin**: gestione utenti (escluso superadmin), tutte le funzionalità operative
- **Operatore**: funzionalità operative (attività, agenti, report)

## Struttura Progetto

```
small_erp/
├── app/
│   ├── __init__.py          # App factory Flask
│   ├── models.py            # Modelli SQLAlchemy
│   ├── services.py          # Logica di calcolo centralizzata
│   ├── audit_service.py     # Servizio audit log
│   ├── auth.py              # Autenticazione
│   ├── dashboard.py         # Dashboard
│   ├── activities.py        # CRUD attività, costi, partecipanti
│   ├── agents.py            # CRUD agenti
│   ├── users.py             # Gestione utenti
│   ├── reports.py           # Report mensili
│   ├── audit.py             # Visualizzazione audit log
│   ├── templates/           # Template Jinja2
│   └── static/css/          # Stili CSS
├── init_db.py               # Inizializzazione DB + superadmin
├── seed_demo.py             # Dati demo
├── run.py                   # Entry point
├── requirements.txt
├── .env.example
└── README.md
```
