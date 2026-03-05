# 🔄 POLYGONUM - Contesto Progetto

## 📋 Cos'è Polygonum

**Polygonum** è una piattaforma web per lo scambio di oggetti basata su Django. Il sistema permette agli utenti di:
- Pubblicare annunci di oggetti da scambiare
- Trovare catene di scambio multi-hop (es: A→B→C→A)
- Comunicare tramite messaggistica interna
- Ricevere notifiche per match e proposte
- Accedere a funzionalità premium (Stripe)

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

### 4. Sistema Premium
- Checkout Stripe
- Funzionalità extra per utenti premium
- Gestione abbonamenti

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
