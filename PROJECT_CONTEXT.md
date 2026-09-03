# 🔄 POLYGONUM - Contesto Progetto

## 📋 Cos'è Polygonum

**Polygonum** è una piattaforma web per lo scambio di oggetti basata su Django. Il sistema permette agli utenti di:
- Pubblicare annunci di oggetti da scambiare
- Trovare catene di scambio multi-hop (es: A→B→C→A)
- Comunicare tramite messaggistica interna
- Ricevere notifiche per match e proposte
- Utilizzare il piano gratuito; i nuovi acquisti Premium sono disabilitati

---

## 🛠️ Stack Tecnologico

### Backend
- **Framework**: Django 5.2.6
- **Database**: PostgreSQL (produzione) / SQLite (sviluppo)
- **Server**: Gunicorn + WhiteNoise (static files)
- **Storage**: Cloudinary (immagini con moderazione automatica)

### Librerie principali
- `nltk` - Matching sinonimi per ricerca annunci
- `pillow` - Gestione immagini
- `psycopg2-binary` - Driver PostgreSQL
- `requests` - HTTP client per webhook

### Deployment
- **Hosting**: Render.com
- **Database**: Render PostgreSQL
- **CDN**: Cloudinary

---

## 📁 Struttura Progetto

```
scambio_sito/
├── scambi/              # App principale Django
│   ├── models.py        # Annuncio, Ciclo, Messaggio, Notifica, etc.
│   ├── views.py         # ~140 endpoints (142KB!)
│   ├── matching.py      # Algoritmo calcolo catene (81KB)
│   ├── notifications.py # Sistema notifiche
│   ├── forms.py         # Form annunci/profilo
│   ├── templates/       # Template HTML
│   └── static/          # CSS/JS/img
├── scambio_sito/        # Settings Django
├── manage.py
├── requirements.txt
└── render.yaml          # Config deployment Render
```

---

## 🎯 Funzionalità Principali

### 1. Annunci
- Creazione/modifica/cancellazione
- Categorie: 5 fasce di prezzo (€0-20, €20-50, €50-150, €150-500, €500+)
- Upload immagini con moderazione Cloudinary
- Ricerca con sinonimi (NLTK)
- Preferiti

### 2. Catene di Scambio
- **Algoritmo matching**: trova cicli di scambio multi-utente
- Proposte catene con approvazione tutti i partecipanti
- Visualizzazione grafica catene attivabili
- Notifiche push per nuove catene

### 3. Messaggistica
- Chat 1-to-1 tra utenti
- Link diretto da annuncio → messaggio
- Notifiche nuovi messaggi

### 4. Piani account
- Piano gratuito: 5 annunci "Offro" e 5 annunci "Cerco" attivi
- Nuovi acquisti Premium e pagamenti online disabilitati
- Campi Premium esistenti mantenuti solo per compatibilità con i dati storici

### 5. Newsletter
- Comando custom `python manage.py invia_newsletter`
- Template HTML personalizzabile
- Link disiscrizione automatico

---

## 📄 File Documentazione Esistenti

| File | Descrizione |
|------|-------------|
| `STRUTTURA_SITO.md` | Mappa completa di tutti i 134+ endpoint |
| `ISTRUZIONI_FASCIA_PREZZO.md` | Sistema fasce di prezzo e matching |
| `NEWSLETTER_GUIDA.md` | Come inviare newsletter personalizzate |
| `CLOUDINARY_SETUP.md` | Setup moderazione immagini |
| `PIANO_MODIFICA_CYCLE_CALCULATOR.md` | Piano modifica algoritmo cicli |
| `SPIEGAZIONE_PROBLEMA_BASSO.md` | Debug matching issue |

---

## 🚀 Comandi Utili

### Sviluppo locale
```bash
# Attiva virtual environment
source ../scambio_env/bin/activate

# Migrazioni
python manage.py makemigrations
python manage.py migrate

# Server sviluppo
python manage.py runserver

# Shell Django
python manage.py shell
```

### Comandi custom
```bash
# Popolare fasce prezzo annunci esistenti
python manage.py popola_fasce_prezzo --dry-run

# Inviare newsletter
python manage.py invia_newsletter \
  --oggetto "Titolo" \
  --messaggio "<p>Messaggio HTML</p>" \
  --dry-run
```

### Deployment Render
- **Dashboard**: https://dashboard.render.com/web/srv-d37eabnfte5s73b7hqu0
- Deploy automatico da git push su main
- Shell remota per comandi management

---

## 🔑 Variabili Ambiente (.env)

Vedi `.env.example` per la lista completa. Principali:
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `CLOUDINARY_URL` - Cloudinary API credentials
- `STRIPE_*` - Chiavi Stripe (test/prod)
- `EMAIL_*` - SMTP settings

---

## 🐛 Debug Views

Pagine di debug disponibili (da rimuovere in produzione):
- `/debug/basso/` - Debug matching basso
- `/debug/view-catene/` - Visualizza catene
- `/debug/cyclefinder-basso/` - Test algoritmo cicli

Script di debug in root:
- `debug_catene_step_by_step.py`
- `diagnosi_completa_basso.py`
- `test_match_synth.py`

---

## 📊 Modelli Principali

| Model | Descrizione |
|-------|-------------|
| `Annuncio` | Oggetto in scambio con fascia_prezzo |
| `Ciclo` | Catena di scambio (es: A→B→C→A) |
| `PropostaCiclo` | Proposta catena con stato approvazione |
| `Messaggio` | Chat tra utenti |
| `Notifica` | Notifiche push |
| `Provincia/Citta` | Geolocalizzazione annunci |
| `CustomUser` | Utente con premium/email_verificata |

---

## 🎨 Frontend

- **Template engine**: Django Templates
- **CSS**: Bootstrap 5 + custom CSS
- **JS**: Vanilla JS + AJAX per ricerca/messaggi
- **Icons**: Font Awesome
- **Gradiente brand**: #667eea → #764ba2 (viola-blu)

---

## 🔄 Workflow Tipico

1. **Utente registra** → verifica email
2. **Crea annuncio** → seleziona fascia prezzo → upload immagine
3. **Sistema calcola catene** di scambio con algoritmo matching
4. **Utente riceve notifica** → visualizza catena → approva/rifiuta
5. **Se tutti approvano** → catena si attiva → scambio avviene

---

## 📍 Percorsi Importanti

- **Progetto**: `/Users/tommasocus/Documents/POLYGONUM WEBSITE/scambio_sito`
- **Virtual env**: `/Users/tommasocus/Documents/POLYGONUM WEBSITE/scambio_env`
- **Database locale**: `db.sqlite3`

---

## 🚨 Note Importanti

- Il file `views.py` è molto grande (142KB, 140+ endpoint) → considerare refactoring
- `matching.py` contiene l'algoritmo core (81KB) → ben documentato
- Sistema moderazione Cloudinary attivo → webhook `/webhook/cloudinary-moderation/`
- Utente admin creato via `make_user_premium.py`

---

## 🔧 Troubleshooting: Proposte Catene Scadute

### Problema
Le catene di scambio con proposte scadute continuano a mostrare:
- Badge "Scade oggi" anche se la scadenza è passata da mesi
- Badge "Interessato" ✓ su catene con proposte vecchie
- Quando si riclicca "Mi interessa", la catena non appare in `/mie-proposte-catene/`
- Le proposte vecchie vengono riutilizzate invece di crearne di nuove

### Causa
Le proposte catene hanno una **scadenza di 7 giorni** (`data_scadenza`). Dopo questo periodo:
- La proposta è tecnicamente scaduta ma rimane nel database
- Le query NON filtravano le proposte scadute
- Il sistema cercava di riattivare proposte vecchie invece di crearne di nuove
- I cicli venivano salvati senza il campo `utenti` nei dettagli, impedendo la visualizzazione

### Diagnosi
```bash
# 1. Controlla cicli nel database
cd "/path/to/scambio_sito"
sqlite3 db.sqlite3 "SELECT id, users, lunghezza, calcolato_at FROM scambi_cicloscambio WHERE users LIKE '%USER_ID%' ORDER BY calcolato_at DESC LIMIT 5;"

# 2. Verifica campo utenti nei dettagli
sqlite3 db.sqlite3 "SELECT dettagli FROM scambi_cicloscambio WHERE id=CICLO_ID;" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Campo utenti presente:', 'utenti' in data)
print('Utenti:', data.get('utenti', []))
"

# 3. Controlla proposte scadute
sqlite3 db.sqlite3 "SELECT p.id, p.ciclo_id, p.stato, p.data_scadenza FROM scambi_propostacatena p WHERE p.data_scadenza < datetime('now');"
```

### Soluzione Applicata (2026-03-05)

#### 1. Campo `utenti` mancante nei cicli (`matching.py:1316`)
**Problema**: `_get_dettagli_ciclo()` non includeva la lista utenti
```python
# PRIMA (bug)
dettagli = {
    'scambi': [],
    'oggetti': [],
    'timestamp': datetime.now().isoformat()
}

# DOPO (fix)
dettagli = {
    'scambi': [],
    'oggetti': [],
    'utenti': [],  # ← AGGIUNTO
    'timestamp': datetime.now().isoformat()
}
# + costruzione lista utenti con user, offerta, richiede
```

#### 2. Filtrare proposte scadute nelle query (`views.py`)

**A) Query `cicli_interessati` (3 occorrenze: riga ~750, ~1212, ~1366)**
```python
# PRIMA
cicli_interessati = set(
    str(cid) for cid in RispostaProposta.objects.filter(
        utente=request.user,
        risposta='interessato'
    ).values_list('proposta__ciclo_id', flat=True)
)

# DOPO
cicli_interessati = set(
    str(cid) for cid in RispostaProposta.objects.filter(
        utente=request.user,
        risposta='interessato',
        proposta__data_scadenza__gt=timezone.now()  # ← AGGIUNTO
    ).values_list('proposta__ciclo_id', flat=True)
)
```

**B) View `proponi_catena` (riga ~2599)**
```python
# PRIMA
proposta_esistente = PropostaCatena.objects.filter(ciclo=ciclo).first()

# DOPO
proposta_esistente = PropostaCatena.objects.filter(
    ciclo=ciclo,
    data_scadenza__gt=timezone.now()  # ← AGGIUNTO
).first()
```

**C) View `stato_proposta_catena` (riga ~2864)**
```python
# PRIMA
proposta = PropostaCatena.objects.filter(
    ciclo=ciclo,
    stato__in=['in_attesa', 'tutti_interessati', 'annullata', 'rifiutata']
).first()

# DOPO
proposta = PropostaCatena.objects.filter(
    ciclo=ciclo,
    stato__in=['in_attesa', 'tutti_interessati', 'annullata', 'rifiutata'],
    data_scadenza__gt=timezone.now()  # ← AGGIUNTO
).first()
```

**D) View `mie_proposte_catene` (riga ~2918)**
```python
# PRIMA
if proposta.stato in ['annullata', 'rifiutata']:
    continue

# DOPO
if proposta.stato in ['annullata', 'rifiutata']:
    continue

if proposta.is_scaduta():  # ← AGGIUNTO
    continue
```

#### 3. Ricalcolare i cicli in produzione
```bash
# Nella shell di Render
python manage.py calcola_cicli

# Output atteso:
# ✅ Trovati X cicli unici
# 💾 Salvataggio completato: Y cicli aggiornati
```

### Risultato
Dopo i fix:
- ✅ Proposte scadute NON mostrano più badge "Interessato" o "Scade oggi"
- ✅ Cliccando "Mi interessa" su catene vecchie, si crea una NUOVA proposta con scadenza 7 giorni
- ✅ Le catene appaiono correttamente in `/mie-proposte-catene/`
- ✅ I cicli hanno il campo `utenti` e vengono visualizzati correttamente

### File Modificati
- `scambi/matching.py` - Aggiunto campo `utenti` in `_get_dettagli_ciclo()`
- `scambi/views.py` - Filtrate proposte scadute in 5 punti diversi
- Commit: `3ff3d36`, `b30fad3`, `0efbe82`

### Prevenzione
Per evitare il problema in futuro:
1. **Sempre filtrare** proposte scadute quando si caricano `cicli_interessati`
2. **Sempre usare** `data_scadenza__gt=timezone.now()` nelle query PropostaCatena
3. **Verificare** che i cicli abbiano il campo `utenti` dopo ogni modifica a `matching.py`
4. **Ricalcolare** i cicli dopo deploy di modifiche all'algoritmo matching

### Pagine Coinvolte
- `/catene-scambio/` - Tutte le catene disponibili
- `/le-mie-catene/` - Catene che coinvolgono i tuoi annunci
- `/mie-proposte-catene/` - Catene a cui hai dato "Mi interessa"

---

## 📝 TODO / Prossimi Sviluppi

- [ ] Refactoring `views.py` in più file
- [ ] Rimuovere debug views in produzione
- [ ] Ottimizzare algoritmo matching per grandi volumi
- [ ] Migliorare UI mobile
- [ ] Sistema valutazioni post-scambio

---

**Ultimo aggiornamento**: 2026-03-05
**Sviluppatore**: Tommaso Cusano
**Sito**: polygonum.io
