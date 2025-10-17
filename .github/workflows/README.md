# GitHub Actions Workflows

Questo progetto utilizza GitHub Actions per automatizzare task periodici.

## Daily Expiration Check

Il workflow `daily-expiration-check.yml` esegue automaticamente ogni giorno alle 2:00 AM UTC il comando per gestire le scadenze delle proposte di catene di scambio.

### Funzionalità

- Invia reminder agli utenti per proposte in scadenza (≤1 giorno)
- Annulla automaticamente proposte scadute
- Invia notifiche di scadenza
- Crea automaticamente un issue su GitHub in caso di errore

### Configurazione Secrets

Per far funzionare il workflow, devi configurare i seguenti secrets nel repository GitHub:

1. **Vai su**: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

2. **Aggiungi i seguenti secrets**:

   - **`DATABASE_URL`** (Obbligatorio)
     - URL di connessione al database di produzione
     - Formato PostgreSQL: `postgres://user:password@host:port/dbname`
     - Esempio: `postgres://polygonum:mypassword@db.example.com:5432/polygonum_prod`

   - **`DJANGO_SECRET_KEY`** (Opzionale, ma raccomandato)
     - Secret key Django per produzione
     - Se non fornita, usa un valore temporaneo (non sicuro)

   - **`SENDGRID_API_KEY`** (Opzionale)
     - API key di SendGrid per inviare email
     - Se non configurato, usa il console backend (log su console)

### Esecuzione Manuale

Puoi eseguire manualmente il workflow:

1. Vai su `Actions` nel repository GitHub
2. Seleziona `Daily Expiration Check`
3. Clicca su `Run workflow`
4. Seleziona il branch e clicca `Run workflow`

### Orario di Esecuzione

Il workflow è programmato per eseguire alle:
- **2:00 AM UTC** = **3:00 AM CET** (inverno) / **4:00 AM CEST** (estate)

Per modificare l'orario, modifica la linea cron nel file:
```yaml
- cron: '0 2 * * *'  # Modifica qui (formato: minuto ora giorno mese giorno_settimana)
```

Esempi:
- `0 1 * * *` = 1:00 AM UTC
- `30 3 * * *` = 3:30 AM UTC
- `0 0 * * *` = Mezzanotte UTC

### Monitoraggio

- I log di ogni esecuzione sono disponibili nella tab `Actions` del repository
- In caso di errore, viene creato automaticamente un issue nel repository
- Riceverai notifiche email da GitHub per i workflow falliti

### Test Locale

Prima di committare modifiche al workflow, puoi testare il comando localmente:

```bash
# Assicurati di avere le variabili d'ambiente configurate
python manage.py gestisci_scadenze_proposte
```

### Troubleshooting

**Problema**: Il workflow fallisce con "Database connection error"
- **Soluzione**: Verifica che `DATABASE_URL` sia configurato correttamente nei secrets

**Problema**: Le notifiche non vengono inviate
- **Soluzione**: Controlla che `SENDGRID_API_KEY` sia configurato (opzionale ma necessario per email reali)

**Problema**: Il workflow non viene eseguito
- **Soluzione**: GitHub Actions gratuito ha limitazioni. Verifica nella tab Actions se ci sono messaggi di errore

### Costi

- GitHub Actions è gratuito per repository pubblici
- Per repository privati: 2000 minuti gratuiti/mese, poi a pagamento
- Questo workflow usa circa 2-3 minuti per esecuzione = ~60-90 minuti/mese

## Cycle Calculator

Il workflow `cycle-calculator.yml` gestisce il calcolo automatico dei cicli di scambio.
(Documentazione da aggiornare se necessario)
