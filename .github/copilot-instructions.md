# GitHub Copilot Instructions — Small ERP

## Regola Documentazione (Markdown)

Per questo repository, Copilot deve seguire sempre queste regole:

1. Non creare nuovi file `.md`.
2. Per la documentazione generale, aggiornare solo `README.md`.
3. Per le regole operative dell'agente, aggiornare solo `.github/copilot-instructions.md`.
4. Se serve spostare o consolidare documentazione esistente, migrare prima i contenuti utili in `README.md`, poi rimuovere i file Markdown ridondanti.

## Regola Versione

Ad ogni commit significativo (nuova feature, bugfix, modifica rilevante) **aggiornare** `app/version.py`:

```python
APP_VERSION = "MAJOR.MINOR.PATCH"
```

- **MAJOR**: cambiamenti incompatibili o ristrutturazioni architetturali
- **MINOR**: nuove funzionalità retrocompatibili
- **PATCH**: bugfix e piccole correzioni

La versione viene mostrata nella sidebar dell'interfaccia web.

## Regola Fondamentale: Test Obbligatori

**Ogni volta che viene creata una nuova funzione, corretto un bug, o apportata una modifica significativa al codice, è OBBLIGATORIO:**

1. **Creare nuovi test** che coprano la modifica effettuata
2. **Eseguire l'intera suite di pytest** con il comando:
   ```bash
   cd /opt/small_erp && python -m pytest tests/ -v --tb=short
   ```
3. **Verificare che tutti i test passino** (zero failure) prima di considerare la modifica completata
4. Se un test fallisce, correggere il codice o il test prima di procedere

Non saltare mai la fase di testing. Un codice senza test non è considerato completo.

---

## Panoramica del Progetto

Small ERP è un'applicazione web Flask per la gestione di attività a ricavo, agenti, partecipanti e calcoli finanziari con audit logging completo.

### Stack Tecnologico

- **Framework:** Flask 3.1.0
- **Database:** SQLite con SQLAlchemy ORM
- **Autenticazione:** Flask-Login 0.6.3
- **Form:** Flask-WTF 1.2.2 + WTForms 3.2.1
- **Testing:** pytest 7.4.3 + pytest-cov 4.1.0
- **Internazionalizzazione:** Bilingue italiano/inglese tramite `app/i18n.py`
- **Logging:** TimedRotatingFileHandler con rotazione giornaliera

---

## Struttura del Progetto

```
/opt/small_erp/
├── app/
│   ├── __init__.py          # App factory (create_app), estensioni, filtri template
│   ├── models.py            # Modelli SQLAlchemy (User, Agent, RevenueActivity, ActivityCost, ActivityParticipant, AuditLog)
│   ├── services.py          # Logica di business e calcoli finanziari (Decimal con ROUND_HALF_UP)
│   ├── audit_service.py     # Servizio centralizzato di audit logging
│   ├── auth.py              # Blueprint autenticazione (login/logout)
│   ├── dashboard.py         # Blueprint dashboard
│   ├── activities.py        # Blueprint attività (CRUD attività, costi, partecipanti)
│   ├── agents.py            # Blueprint agenti
│   ├── users.py             # Blueprint gestione utenti (admin only)
│   ├── reports.py           # Blueprint report mensili
│   ├── audit.py             # Blueprint visualizzazione audit log (superadmin only)
│   ├── i18n.py              # Internazionalizzazione (it/en)
│   ├── logging_config.py    # Configurazione logging multilivello
│   ├── templates/           # Template Jinja2
│   └── static/              # File statici (CSS)
├── tests/
│   ├── conftest.py          # Fixture pytest (app, client, utenti, agent, activity, ecc.)
│   ├── test_auth.py         # Test autenticazione e autorizzazione
│   ├── test_models.py       # Test modelli e relazioni
│   ├── test_services.py     # Test calcoli finanziari e servizi
│   ├── test_routes.py       # Test route HTTP e CRUD
│   └── test_audit_service.py# Test servizio di audit
├── init_db.py               # Inizializzazione DB e superadmin
├── seed_demo.py             # Dati demo per sviluppo
├── run.py                   # Entry point (Flask dev server)
├── pytest.ini               # Configurazione pytest
└── requirements.txt         # Dipendenze Python
```

---

## Modelli Dati

### User

- Campi: `id`, `username` (unico), `email` (unico), `password_hash`, `full_name`, `is_superadmin`, `is_active_user`, `created_at`, `updated_at`
- `is_superadmin`: boolean, True solo per l'utente superadmin (creato da `.env`)
- Proprietà: `is_active`
- Metodi: `set_password()`, `check_password()`

### Agent

- Campi: `id`, `first_name`, `default_percentage` (Numeric 5,2), `is_active`, `notes`, `created_at`, `updated_at`
- Proprietà: `full_name` (restituisce `first_name`)

### RevenueActivity

- Campi: `id`, `title`, `description`, `date`, `status`, `total_revenue`, `agent_id`, `agent_percentage`, `notes`, `created_by`, `created_at`, `updated_at`
- Stati: `bozza`, `confermata`, `chiusa`
- Relazioni: `costs`, `participants`, `creator` (cascade delete su costs e participants)

### ActivityCost

- Campi: `id`, `activity_id`, `category`, `description`, `amount`, `date`, `cost_type`, `notes`, `created_at`
- Categorie: `materiale`, `trasporto`, `consulenza`, `marketing`, `spese_vive`, `altro`
- Tipi costo: `operativo`, `extra`

### ActivityParticipant

- Campi: `id`, `activity_id`, `participant_name`, `user_id` (nullable), `role_description`, `work_share`, `fixed_compensation`, `notes`, `created_at`

### AuditLog

- Campi: `id`, `user_id`, `username`, `timestamp`, `action_type`, `entity_type`, `entity_id`, `description`, `old_values` (JSON), `new_values` (JSON), `ip_address`
- Tipi azione: `login`, `logout`, `create`, `update`, `delete`, `status_change`, `user_create`, `user_update`

---

## Convenzioni di Codice

### Calcoli Finanziari

- Usare SEMPRE `Decimal` da `decimal` (mai `float`) per calcoli monetari
- Arrotondamento: `ROUND_HALF_UP` con 2 decimali
- Usare `to_decimal()` da `app/services.py` per conversioni sicure
- Formule principali in `calc_activity_totals()` e `calc_agent_compensation()`

### Accesso al Database

- Usare `db.session` per tutte le operazioni
- `db.session.commit()` dopo ogni modifica
- `db.session.rollback()` in caso di errore
- `get_or_404()` per lookup per ID nelle route

### Audit Logging

- Ogni operazione CRUD DEVE registrare un audit log tramite `log_action()` da `app/audit_service.py`
- Usare `model_to_dict()` per catturare old/new values
- Campi da tracciare definiti come lista per ogni modello

### Autenticazione e Autorizzazione

- Route protette con `@login_required`
- Route superadmin (utenti e audit) con decorator `@superadmin_required`
- I decoratori sono definiti localmente in `app/users.py` e `app/audit.py`

### Internazionalizzazione

- Usare `tr('testo italiano', 'english text')` per testi bilingui
- Label di stato: `status_label(status)` da `app/i18n.py`
- Lingue supportate: `it`, `en`

### Blueprint e Route

- Ogni modulo funzionale è un Blueprint Flask separato
- URL prefix coerente per ogni blueprint: `/activities`, `/agents`, `/users`, `/reports`, `/audit`
- Filtri template registrati nell'app factory: `currency()`, `percentage()`

---

## Linee Guida per i Test

### Struttura dei Test

I test DEVONO seguire la struttura esistente in `tests/`:

- **`tests/conftest.py`** — Fixture condivise: `app`, `client`, `superadmin_user`, `admin_user` (utente normale), `operator_user` (utente normale), `agent`, `revenue_activity`, `activity_cost`, `activity_participant`, `audit_log`
- **`tests/test_models.py`** — Test dei modelli: creazione, proprietà, relazioni, cascade
- **`tests/test_services.py`** — Test dei servizi: calcoli finanziari, edge cases, arrotondamenti
- **`tests/test_auth.py`** — Test autenticazione: login, logout, decoratori, permessi
- **`tests/test_routes.py`** — Test delle route HTTP: CRUD completo, filtri, permessi
- **`tests/test_audit_service.py`** — Test audit: logging, serializzazione, query

### Pattern per i Test

```python
# Usare i marker pytest definiti in pytest.ini
@pytest.mark.unit
@pytest.mark.services
def test_nome_descrittivo(client, agent, revenue_activity):
    """Descrizione del comportamento atteso."""
    # Arrange (setup dati)
    # Act (esegui operazione)
    # Assert (verifica risultati)
```

### Marker Disponibili

- `unit` — Test unitari
- `integration` — Test di integrazione
- `auth` — Test autenticazione
- `routes` — Test route HTTP
- `models` — Test modelli
- `services` — Test servizi/calcoli
- `slow` — Test lenti

### Login nei Test

```python
# Per autenticarsi nei test delle route
client.post('/login', data={
    'username': 'admin',
    'password': 'testpass123'
}, follow_redirects=True)
```

### Fixture del Database

- L'app di test usa SQLite in-memory (`sqlite://`)
- CSRF disabilitato in testing (`WTF_CSRF_ENABLED = False`)
- Ogni test ha un DB pulito grazie alle fixture
- Le fixture sono concatenabili (es. `activity_cost` dipende da `revenue_activity` che dipende da `agent`)

### Esecuzione Test

```bash
# Esecuzione completa (OBBLIGATORIA dopo ogni modifica)
python -m pytest tests/ -v --tb=short

# Con copertura
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# Solo un file di test
python -m pytest tests/test_services.py -v

# Solo un marker specifico
python -m pytest tests/ -m unit -v
```

---

## Checklist per Ogni Modifica

1. [ ] Il codice segue le convenzioni esistenti (Decimal, audit, i18n)
2. [ ] I test per la modifica sono stati scritti in `tests/`
3. [ ] I test coprono: caso normale, edge case, errore atteso
4. [ ] La suite completa di pytest passa senza errori
5. [ ] Se è una nuova route: test di accesso autenticato/non autenticato
6. [ ] Se tocca calcoli: test con valori zero, negativi, decimali
7. [ ] Se modifica modelli: test creazione, relazioni, proprietà
8. [ ] Audit logging inserito per operazioni CRUD

---

## Configurazione Ambiente

- **Variabili d'ambiente** in `.env`: `SECRET_KEY`, `SUPERADMIN_PASSWORD`, `DATABASE_PATH`
- **Database di produzione**: `instance/erp.db`
- **Log**: `logs/app.log`, `logs/error.log`, `logs/debug.log` (rotazione giornaliera, 30 giorni)
- **Virtual environment**: `env/`
