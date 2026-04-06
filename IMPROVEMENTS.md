# Proposte di Miglioramento — Small ERP

Analisi eseguita il 2026-04-05. Il codice è ben strutturato e la security audit è già stata completata.
Le proposte seguenti sono ordinare per **priorità** (Alta / Media / Bassa) e riguardano qualità del codice,
performance, robustezza e testabilità. **Nessun file è stato modificato.**

---

## Priorità Alta

### P1 — N+1 Query in `services.py` (impatto performance)

**File**: [app/services.py](app/services.py)  
**Problema**: `calc_activity_totals()` esegue query separate per `ActivityCost` e `ActivityParticipant`
per ogni attività. Quando viene chiamata dentro `calc_monthly_report()` in un loop, si generano
**N×2 query extra** per N attività chiuse nel mese.

**Soluzione proposta**: usare `joinedload` / `subqueryload` nelle query di `calc_monthly_report()`
oppure passare direttamente i costi già caricati (eager loading):

```python
# Invece di:
activities = RevenueActivity.query.filter(...).all()
for act in activities:
    totals = calc_activity_totals(act)  # esegue 2 query per ognuna

# Usare eager loading:
from sqlalchemy.orm import subqueryload
activities = (
    RevenueActivity.query
    .options(subqueryload(RevenueActivity.costs),
             subqueryload(RevenueActivity.participants))
    .filter(...)
    .all()
)
```

---

### P2 — Host e porta hardcoded in `run.py`

**File**: [run.py](run.py) riga 12  
**Problema**: L'app ascolta sempre su `127.0.0.1:5000`. In ambienti Docker o su server remoti,
il processo non è raggiungibile dall'esterno.

**Soluzione proposta**:
```python
host = os.getenv('FLASK_HOST', '127.0.0.1')
port = int(os.getenv('FLASK_PORT', '5000'))
app.run(host=host, port=port, debug=debug_mode)
```
Aggiungere `FLASK_HOST` e `FLASK_PORT` al `.env` e al `CLAUDE.md`.

---

### P3 — Validazione anno/mese mancante in `reports.py` e `services.py`

**File**: [app/reports.py](app/reports.py) righe 16–26 · [app/services.py](app/services.py) righe 88–96  
**Problema**: Se l'utente passa `?month=13` o `?year=-1`, la query SQLAlchemy non solleva eccezioni
ma restituisce risultati vuoti senza avvisare l'utente. Non è un bug di sicurezza ma porta a
confusione (report vuoto invece di errore esplicito).

**Soluzione proposta**:
```python
if not (1 <= month <= 12):
    flash(tr('invalid_month'), 'error')
    return redirect(url_for('reports.index'))
if not (2000 <= year <= 2100):
    flash(tr('invalid_year'), 'error')
    return redirect(url_for('reports.index'))
```

---

## Priorità Media

### M1 — N+1 Query nelle route `activities.py` e `users.py`

**File**: [app/activities.py](app/activities.py) righe 341, 376 · [app/users.py](app/users.py) righe 147–149  

- In `activities.py`: `User.query.filter_by(is_active_user=True).all()` viene chiamata ad ogni
  apertura del form dei partecipanti. Accettabile con pochi utenti; da ottimizzare oltre ~500 utenti.
- In `users.py`: `len(user.created_activities)` e `len(user.participations)` caricano in memoria
  tutte le righe correlate per fare un conteggio. Preferire query COUNT:
  ```python
  from sqlalchemy import func
  activity_count = db.session.query(func.count(RevenueActivity.id))\
      .filter_by(created_by=user.id).scalar()
  ```

---

### M2 — Paginazione utenti assente in `users.py`

**File**: [app/users.py](app/users.py) riga 45  
**Problema**: `User.query.all()` carica tutti gli utenti in memoria. Se il numero cresce,
la pagina `/users` diventa lenta.

**Soluzione proposta**: usare `.paginate()` come già fatto per le attività:
```python
page = request.args.get('page', 1, type=int)
users = User.query.order_by(User.username).paginate(page=page, per_page=20)
```

---

### M3 — Duplicazione logica in `services.py`

**File**: [app/services.py](app/services.py) righe 147–202  
**Problema**: `calc_dashboard_stats()` ripete gran parte della logica di `calc_monthly_report()`.
Un refactor potrebbe far chiamare `calc_monthly_report()` internamente oppure estrarre
una funzione `_sum_activities(activities)` condivisa.

---

### M4 — Serializzazione JSON di `Decimal` in `audit_service.py`

**File**: [app/audit_service.py](app/audit_service.py) riga 37  
**Problema**: `json.dumps(values, default=str)` converte `Decimal('99.50')` nella stringa
`"Decimal('99.50')"` invece di `"99.50"`. Nei diff dell'audit log il valore risulta illeggibile.

**Soluzione proposta**: encoder personalizzato:
```python
import decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)  # oppure float(obj) se si accetta la perdita di precisione
        return super().default(obj)

json.dumps(values, cls=DecimalEncoder)
```

---

### M5 — Controllo `current_user` in `audit_service.py`

**File**: [app/audit_service.py](app/audit_service.py) riga 19  
**Problema**: `hasattr(current_user, 'username')` è una verifica fragile. Se `current_user` è
un oggetto `AnonymousUser` (Flask-Login), ha attributo `username` ma il suo valore è `None`.

**Soluzione proposta**:
```python
# Invece di:
if hasattr(current_user, 'username'):
# Usare:
if current_user.is_authenticated:
```

---

### M6 — Validazione email agente assente in `models.py`

**File**: [app/models.py](app/models.py) riga 41  
**Problema**: Il campo `email` dell'agente non ha vincolo di unicità né validazione formato.
Due agenti possono avere la stessa email senza errore.

**Soluzione proposta**: aggiungere validazione nel route `agents.py` (non nel modello, per non
modificare lo schema DB):
```python
import re
if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
    flash(tr('invalid_email'), 'error')
    return redirect(...)
```

---

### M7 — Conversione intera non protetta in `activities.py`

**File**: [app/activities.py](app/activities.py) riga 63  
**Problema**: `int(agent_filter)` senza `try-except` solleva `ValueError` se il parametro
`agent` nell'URL è una stringa non numerica (es. `?agent=abc`).

**Soluzione proposta**:
```python
try:
    agent_filter = int(request.args.get('agent', 0))
except (ValueError, TypeError):
    agent_filter = 0
```

---

## Priorità Bassa

### B1 — Timezone-naive timestamps in `models.py`

**File**: [app/models.py](app/models.py) righe 18–19  
**Problema**: `datetime.utcnow` è deprecato da Python 3.12 e crea oggetti naive (senza timezone).
Potenziale confusione se in futuro si aggiunge supporto multi-timezone.

**Soluzione proposta**:
```python
from datetime import datetime, timezone
default=lambda: datetime.now(timezone.utc)
```

---

### B2 — Rotazione log: suffisso data non aggiunto di default

**File**: [app/logging_config.py](app/logging_config.py) righe 37–44  
**Problema**: `TimedRotatingFileHandler` di default rinomina il file aggiungendo la data,
ma il file corrente si chiama sempre `app.log`. Verificare che `backupCount=30` funzioni
correttamente con il path assoluto della directory log.

**Soluzione proposta**: aggiungere un test che verifica la presenza del file log dopo un ciclo
di rotazione, oppure usare `RotatingFileHandler` se la rotazione per dimensione è sufficiente.

---

### B3 — Email legacy hardcoded in `users.py`

**File**: [app/users.py](app/users.py) riga 74  
**Problema**: La creazione utente imposta `email=f'{username}@erp.local'`. Questo valore
potrebbe emergere in log o future funzionalità email.

**Nota**: campo legacy già nascosto nell'UI, quindi impatto basso. Valutare se rimuovere
il campo `email` dal modello in una versione futura (richiede migrazione DB).

---

### B4 — `init_db.py`: sovrascrittura superadmin ad ogni esecuzione

**File**: [init_db.py](init_db.py) righe 45–54  
**Problema**: Ogni volta che si esegue `python init_db.py`, il record superadmin viene
aggiornato (inclusa la generazione di un nuovo placeholder hash). Se il superadmin è stato
modificato manualmente, le modifiche vengono sovrascritte.

**Soluzione proposta**: eseguire l'update solo se il record non esiste ancora:
```python
if not existing_admin:
    # crea nuovo
    ...
# else: non toccare il record esistente
```

---

### B5 — Test incompleti in `test_auth.py`

**File**: [tests/test_auth.py](tests/test_auth.py) righe 43–50  
**Problema**: `test_login_inactive_user()` non contiene asserzioni. Il test passa sempre
anche se il comportamento atteso (login rifiutato) non è implementato.

**Soluzione proposta**: aggiungere:
```python
assert response.status_code == 200  # rimane sulla pagina di login
assert b'inactive' in response.data or response.status_code != 302
```

---

### B6 — Funzione `tr_match()` usata prima della definizione in `test_security.py`

**File**: [tests/test_security.py](tests/test_security.py) riga 179 (uso) / riga 368 (definizione)  
**Problema**: Python risolve i nomi a runtime quindi funziona, ma è fuorviante per chi
legge il file dall'alto verso il basso. Spostare la definizione in cima o in `conftest.py`.

---

### B7 — Dashboard: nessuna cache per statistiche

**File**: [app/dashboard.py](app/dashboard.py) righe 14–21  
**Problema**: Ogni caricamento della dashboard ricalcola tutte le KPI del mese corrente.
Accettabile con pochi dati; da valutare con crescita del volume.

**Soluzione futura** (non urgente): cache con TTL di 60 secondi usando `flask_caching`
o una semplice cache in-memory con `functools.lru_cache` e invalidazione al commit.

---

## Riepilogo per Priorità

| ID | File | Riga/i | Categoria | Priorità |
|----|------|--------|-----------|----------|
| P1 | services.py | 35–40, 107–126 | Performance | Alta |
| P2 | run.py | 12 | Configurazione | Alta |
| P3 | reports.py, services.py | 16–26, 88–96 | Robustezza | Alta |
| M1 | activities.py, users.py | 341, 376, 147–149 | Performance | Media |
| M2 | users.py | 45 | Performance | Media |
| M3 | services.py | 147–202 | Code Quality | Media |
| M4 | audit_service.py | 37 | Bug | Media |
| M5 | audit_service.py | 19 | Robustezza | Media |
| M6 | models.py / agents.py | 41 | Validazione | Media |
| M7 | activities.py | 63 | Robustezza | Media |
| B1 | models.py | 18–19 | Code Quality | Bassa |
| B2 | logging_config.py | 37–44 | Robustezza | Bassa |
| B3 | users.py | 74 | Code Quality | Bassa |
| B4 | init_db.py | 45–54 | Robustezza | Bassa |
| B5 | tests/test_auth.py | 43–50 | Test Coverage | Bassa |
| B6 | tests/test_security.py | 179/368 | Code Quality | Bassa |
| B7 | dashboard.py | 14–21 | Performance | Bassa |

---

*Nessun file del progetto è stato modificato per produrre questa analisi.*
