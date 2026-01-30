# 📧 Guida Newsletter Polygonum

## Come inviare una newsletter personalizzata

### 1. Test in locale (DRY RUN)
```bash
python manage.py invia_newsletter \
  --oggetto "Polygonum cambia indirizzo!" \
  --messaggio "<p>Polygonum ha un nuovo indirizzo: <strong>polygonum.io</strong>!</p><p>Aggiorna i tuoi bookmark e continua a scambiare con la community.</p>" \
  --dry-run
```

### 2. Test a te stesso
```bash
python manage.py invia_newsletter \
  --oggetto "Test Newsletter" \
  --messaggio "<p>Questa è una prova</p>" \
  --test-email "polygonum.noreply@gmail.com"
```

### 3. Invio REALE a tutti
```bash
python manage.py invia_newsletter \
  --oggetto "Novità su Polygonum!" \
  --messaggio "<p>Ciao! Abbiamo grandi novità da condividere con te...</p>"
```

### 4. Solo utenti con email verificata
```bash
python manage.py invia_newsletter \
  --oggetto "..." \
  --messaggio "..." \
  --solo-verificati
```

## Parametri disponibili

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|--------------|-------------|
| `--oggetto` | Testo | ✅ Sì | Oggetto della email |
| `--messaggio` | HTML | ✅ Sì | Corpo del messaggio (HTML supportato) |
| `--dry-run` | Flag | ❌ No | Simula senza inviare |
| `--solo-verificati` | Flag | ❌ No | Solo utenti con email verificata |
| `--test-email` | Email | ❌ No | Invia solo a questo indirizzo |

## Contenuti automatici inclusi

La newsletter include automaticamente:
- **Saluto personalizzato** con link al profilo utente
- **Firma** del team Polygonum
- **CTA "Pubblica un annuncio"** → link a /crea-annuncio/
- **TIPS casuale** (10 tips a rotazione)
- **Annunci in evidenza** (ultimi 4 con immagini)
- **CTA "Tutti gli annunci"** → link a /annunci/
- **Link di disiscrizione** nel footer

## Esempio messaggio HTML personalizzato

```bash
python manage.py invia_newsletter \
  --oggetto "Novità su Polygonum!" \
  --messaggio "<p>Abbiamo grandi novità per te:</p><ul><li><strong>Nuovo dominio:</strong> polygonum.io</li><li><strong>Design migliorato</strong></li><li><strong>Nuove funzionalità</strong></li></ul><p>Continua a scambiare con la community!</p>"
```

## Come eseguire su Render

1. Vai su https://dashboard.render.com/web/srv-d37eabnfte5s73b7hqu0
2. Clicca **"Shell"** nel menu
3. Esegui il comando (senza `--dry-run`)

## Template personalizzabile

Il layout della email è in:
```
scambi/templates/scambi/emails/newsletter.html
```

Puoi modificarlo per cambiare:
- Colori del gradiente
- Font
- Struttura layout
- Footer

## Logo

Il logo viene caricato automaticamente su Cloudinary al primo utilizzo.
Se Cloudinary non è disponibile, usa il logo da `polygonum.io/static/`.

## Sicurezza

- ✅ Il comando chiede conferma prima di inviare
- ✅ `--dry-run` per testare senza rischi
- ✅ `--test-email` per verificare il layout
- ✅ Supporta HTML sicuro (sanitizzato da Django)
