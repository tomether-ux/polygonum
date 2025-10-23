# Configurazione Cloudinary per Polygonum

## Perché Cloudinary?

Render ha un filesystem **effimero** - tutti i file caricati vengono persi ad ogni deploy o riavvio.
Cloudinary risolve questo problema offrendo storage cloud persistente per le immagini.

## Vantaggi Cloudinary:
- ✅ **Free tier generoso**: 25GB storage, 25GB bandwidth/mese
- ✅ **Persistente**: le immagini non vengono mai perse
- ✅ **CDN incluso**: caricamento veloce in tutto il mondo
- ✅ **Ottimizzazione automatica**: riduce le dimensioni delle immagini
- ✅ **Facile integrazione**: già configurato nel codice

## Setup (5 minuti)

### 1. Crea account Cloudinary (GRATUITO)
1. Vai su https://cloudinary.com/users/register_free
2. Registrati con email (o Google/GitHub)
3. Verifica l'email

### 2. Ottieni le credenziali
Dopo il login, nella dashboard vedrai:
- **Cloud Name**: (es. `dxxxxxxxx`)
- **API Key**: (es. `123456789012345`)
- **API Secret**: (clicca su "reveal" per vedere)

### 3. Configura le variabili d'ambiente su Render

Vai su Render Dashboard → tuo servizio → Environment:

Aggiungi queste 3 variabili:

```
CLOUDINARY_CLOUD_NAME=il_tuo_cloud_name
CLOUDINARY_API_KEY=la_tua_api_key
CLOUDINARY_API_SECRET=il_tuo_api_secret
```

**IMPORTANTE**: Sostituisci i valori con quelli reali dalla dashboard Cloudinary!

### 4. Redeploy

Dopo aver aggiunto le variabili, Render farà il redeploy automaticamente.

### 5. Verifica

Dopo il deploy:
1. Vai sul sito
2. Crea un nuovo annuncio con immagine
3. L'immagine verrà caricata su Cloudinary
4. Ricarica la pagina - l'immagine sarà ancora lì! ✅

## Come funziona?

- **Sviluppo locale** (senza variabili): usa `/media/` locale
- **Produzione** (con variabili Cloudinary): usa cloud storage automaticamente

Il codice rileva automaticamente l'ambiente e usa lo storage giusto.

## Monitoring

Puoi monitorare l'utilizzo su: https://console.cloudinary.com/console/lui/usage

Free tier include:
- 25GB storage
- 25GB bandwidth/mese
- 25,000 trasformazioni/mese

Per un sito come Polygonum questo è più che sufficiente!

## Troubleshooting

**Errore: "Missing required configuration"**
- Verifica di aver aggiunto tutte e 3 le variabili su Render
- Controlla che non ci siano spazi prima/dopo i valori

**Le immagini vecchie non si vedono**
- Normale! Le immagini caricate prima erano sul filesystem effimero
- Le nuove immagini caricate dopo la configurazione funzioneranno

**Vuoi migrare le immagini esistenti?**
- Le immagini sono nel database PostgreSQL
- Possiamo creare uno script per migrare le vecchie immagini su Cloudinary
- Chiedimi se serve!
