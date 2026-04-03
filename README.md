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

Le credenziali del superadmin sono configurate nel file `.env` (variabile `SUPERADMIN_PASSWORD`).
Gli utenti demo (`mario.rossi`, `laura.bianchi`) vengono creati solo eseguendo `seed_demo.py`.

> **Importante:** cambiare le password al primo accesso. Non usare le credenziali di default in produzione.

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

## Testing (Fonte Unica)

Questo progetto usa `pytest` come suite ufficiale di test.

### Comando obbligatorio dopo ogni modifica

```bash
cd /opt/small_erp && python -m pytest tests/ -v --tb=short
```

### Comandi utili

```bash
# Tutti i test con coverage
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# Solo un file
python -m pytest tests/test_services.py -v

# Solo un marker
python -m pytest tests/ -m unit -v
```

### Marker disponibili

- `unit`
- `integration`
- `auth`
- `routes`
- `models`
- `services`
- `slow`

### Fixture principali

Le fixture condivise sono in `tests/conftest.py` e includono: `app`, `client`, `superadmin_user`, `admin_user`, `operator_user`, `agent`, `revenue_activity`, `activity_cost`, `activity_participant`, `audit_log`.

### Note rapide sulla quality baseline

- La suite include test su modelli, servizi, autenticazione, route e audit.
- I moduli critici (`app/audit_service.py`, `app/models.py`) hanno copertura molto alta.

## Logging (Fonte Unica)

Il sistema di logging applicativo salva i file nella directory `logs/` (configurabile con `LOG_DIR` nel file `.env`).

### File di log

- `logs/app.log`: log applicativi generali
- `logs/error.log`: solo errori e criticità
- `logs/debug.log`: dettaglio completo

### Rotazione

- Rotazione giornaliera a mezzanotte
- Retention predefinita: 30 giorni

### Comandi operativi utili

```bash
# Segui i log in tempo reale
tail -f logs/app.log

# Cerca errori
grep "ERROR" logs/error.log

# Elenca file log
ls -lah logs/
```

---

## Security Audit Report

**Data:** 3 aprile 2026  
**Eseguito su:** Small ERP (Flask 3.1.0 / SQLite / Python 3.12)  
**Metodologia:** Code review statico + penetration test manuale con test suite automatizzata  
**Test di sicurezza:** `tests/test_security.py` (27 test case)

### Riepilogo vulnerabilità trovate e corrette

| # | ID | Severità | Vulnerabilità | Stato | File |
|---|-----|----------|--------------|-------|------|
| 1 | AUTH-01 | **CRITICA** | Open redirect su `/login?next=` | Corretta | `app/auth.py` |
| 2 | AUTH-02 | **ALTA** | Session fixation (nessuna rigenerazione sessione al login) | Corretta | `app/auth.py` |
| 3 | AUTH-03 | **MEDIA** | Logout via GET (CSRF logout forzato con `<img src="/logout">`) | Corretta | `app/auth.py`, `templates/base.html` |
| 4 | CRYPTO-01 | **CRITICA** | SECRET_KEY debole/hardcoded (`admin123$APA`, fallback `dev-fallback-key`) | Corretta | `app/__init__.py`, `.env` |
| 5 | CRYPTO-02 | **ALTA** | Cookie di sessione senza flag `HttpOnly`, `SameSite`, timeout assente | Corretta | `app/__init__.py` |
| 6 | AUTHZ-01 | **CRITICA** | IDOR su attività: qualsiasi utente poteva edit/delete attività di altri | Corretta | `app/activities.py` |
| 7 | AUTHZ-02 | **ALTA** | Privilege escalation: admin poteva assegnare ruolo `admin` ad altri | Corretta | `app/users.py` |
| 8 | INJ-01 | **MEDIA** | SQL wildcard injection nei filtri audit (`%` e `_` non sanitizzati) | Corretta | `app/audit.py` |
| 9 | INJ-02 | **MEDIA** | Concatenazione stringa data utente senza validazione nel filtro audit | Corretta | `app/audit.py` |
| 10 | INJ-03 | **ALTA** | Reflected XSS via messaggi di errore (eccezione Python nel flash) | Corretta | `app/activities.py`, `app/agents.py` |
| 11 | INPUT-01 | **MEDIA** | Nessun limite su valori decimali negativi o overflow | Corretta | `app/activities.py` |
| 12 | CONF-01 | **CRITICA** | Debug mode attivo di default (`debug=True` in `run.py`) | Corretta | `run.py` |
| 13 | CONF-02 | **MEDIA** | Header HTTP di sicurezza assenti | Corretta | `app/__init__.py` |
| 14 | CONF-03 | **MEDIA** | Password policy debole (min 6 char, nessun requisito complessità) | Corretta | `app/users.py` |
| 15 | CONF-04 | **BASSA** | Credenziali demo stampate in chiaro nell'output di seed_demo.py | Corretta | `seed_demo.py` |
| 16 | CONF-05 | **BASSA** | Database SQLite non cifrato (encryption at rest) | Nota | — |

### Dettaglio correzioni applicate

#### 1. AUTH-01 — Open Redirect
- **Prima:** `redirect(request.args.get('next'))` senza validazione
- **Dopo:** Funzione `_is_safe_url()` verifica che l'URL sia relativo (no `netloc`, no `scheme`)
- **Test:** `TestOpenRedirect` (3 test case)

#### 2. AUTH-02 — Session Fixation
- **Prima:** `login_user(user)` senza invalidare la sessione esistente
- **Dopo:** `session.clear()` prima di `login_user()`, `session.permanent = True` con timeout 30 min
- **Test:** `TestSessionFixation` (1 test case)

#### 3. AUTH-03 — Logout CSRF-safe
- **Prima:** `@auth_bp.route('/logout')` accettava GET → un tag `<img>` poteva forzare il logout
- **Dopo:** `@auth_bp.route('/logout', methods=['POST'])` + form con CSRF token nel template
- **Test:** `TestLogoutMethod` (2 test case)

#### 4. CRYPTO-01 — SECRET_KEY
- **Prima:** `os.environ.get('SECRET_KEY', 'dev-fallback-key')` e `.env` conteneva `admin123$APA`
- **Dopo:** Validazione obbligatoria ≥16 char, errore in produzione se mancante, generato nuovo token 64 hex
- **Test:** `TestSecretKey` (1 test case)

#### 5. CRYPTO-02 — Session Cookie Flags
- **Prima:** Nessun flag di sicurezza configurato
- **Dopo:** `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `PERMANENT_SESSION_LIFETIME=1800`
- **Test:** `TestSessionCookieFlags` (3 test case)

#### 6. AUTHZ-01 — IDOR su Attività
- **Prima:** Qualsiasi utente autenticato poteva modificare/eliminare qualsiasi attività
- **Dopo:** `_can_modify_activity()` verifica che `current_user` sia il creatore o admin
- **Test:** `TestActivityIDOR` (3 test case)

#### 7. AUTHZ-02 — Privilege Escalation
- **Prima:** Un admin poteva assegnare ruolo `admin` creando un account equivalente
- **Dopo:** `_allowed_roles_for()` limita: admin → solo `operatore`, superadmin → tutti i ruoli
- **Whitelist:** status attività, categorie costo, tipi costo validati contro set fissi

#### 8-9. INJ-01/02 — Audit Filter Injection
- **Prima:** `ilike(f'%{username}%')` vulnerabile a wildcard DoS; date concatenate come stringhe
- **Dopo:** Caratteri `%` e `_` rimossi dall'input; date validate con `datetime.fromisoformat()`
- **Test:** `TestAuditFilterInjection`, `TestAuditDateValidation` (4 test case)

#### 10. INJ-03 — XSS via Error Messages
- **Prima:** `flash(f"Errore: {e}")` iniettava il testo dell'eccezione Python nella pagina
- **Dopo:** Messaggi generici hardcoded, dettaglio solo nei log server
- **Test:** `TestXSSErrorMessages` (1 test case)

#### 11. INPUT-01 — Decimal Validation
- **Prima:** `Decimal(user_input)` senza limiti, valori negativi e overflow accettati
- **Dopo:** `_validate_decimal()` rifiuta negativi e valori > 999.999.999,99; `InvalidOperation` catturata
- **Test:** `TestDecimalValidation` (2 test case)

#### 12. CONF-01 — Debug Mode
- **Prima:** `app.run(debug=True)` hardcoded → shell interattiva Werkzeug esposta
- **Dopo:** `debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'`

#### 13. CONF-02 — Security Headers
- **Prima:** Nessun header di sicurezza
- **Dopo:** `@app.after_request` aggiunge:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- **Test:** `TestSecurityHeaders` (1 test case)

#### 14. CONF-03 — Password Policy
- **Prima:** Minimo 6 caratteri, nessun requisito di complessità
- **Dopo:** Minimo 12 caratteri + almeno 1 maiuscola + 1 minuscola + 1 numero
- **Test:** `TestPasswordPolicy` (4 test case)

### Raccomandazioni residue (non implementate)

| Priorità | Raccomandazione | Motivazione |
|----------|----------------|-------------|
| Alta | **Rate limiting su `/login`** | Nessuna protezione contro brute force; installare `flask-limiter` con limite 5 tentativi/minuto |
| Alta | **Account lockout** | Dopo N tentativi falliti, bloccare l'account per X minuti |
| Media | **`SESSION_COOKIE_SECURE=True`** | Da abilitare quando l'app è servita via HTTPS (non abilitato ora per non rompere HTTP locale) |
| Media | **`Strict-Transport-Security` header** | Da aggiungere solo dopo deploy HTTPS |
| Media | **`Content-Security-Policy` header** | Richiede analisi degli asset inline (script/style) prima di attivarlo |
| Media | **Encryption at rest (CONF-05)** | SQLite non supporta cifratura nativa; valutare migrazione a PostgreSQL o `sqlcipher` |
| Media | **CORS configuration** | Se si espongono API REST, configurare `flask-cors` con whitelist di origini |
| Bassa | **Dependency pinning** | Creare `requirements.lock` con `pip freeze` per bloccare le versioni transitive |
| Bassa | **Force password change** | Forzare il cambio password al primo accesso per account creati da admin |
| Bassa | **Log degli accessi in lettura** | Attualmente solo le operazioni CRUD sono loggate, non le letture di dati sensibili |
