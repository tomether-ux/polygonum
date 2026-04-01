# Piano Rimozione Cloudinary e Migrazione Storage

## Contesto
Cloudinary è attualmente usato per:
- Storage immagini annunci (CloudinaryField nel modello)
- Moderazione automatica contenuti (webhook)

Va sostituito con storage locale o cloud (Backblaze B2) e moderazione manuale tramite gestionale.

---

## 📋 Checklist Implementazione

### 1. Scelta Storage

#### Opzione A: Storage Locale + MEDIA_ROOT (Render)
**PRO:**
- Semplice da implementare
- Gratuito
- Nessuna dipendenza esterna

**CONTRO:**
- File persi ad ogni redeploy su Render (file system effimero)
- Necessario storage persistente esterno

#### Opzione B: Backblaze B2 + django-storages ⭐ CONSIGLIATO
**PRO:**
- Storage persistente
- Compatibile con Render
- 10GB gratuiti
- S3-compatible API

**CONTRO:**
- Configurazione aggiuntiva
- Richiede account Backblaze

#### Opzione C: Render Disks (Storage Persistente)
**PRO:**
- Nativo su Render
- Facile integrazione

**CONTRO:**
- Costo aggiuntivo ($0.25/GB/mese)
- Minimo 1GB

### Decisione: **Backblaze B2 + django-storages**
È la soluzione più efficace per un progetto in produzione su Render.

---

## 🔧 Step Implementazione

### Step 1: Setup Backblaze B2

1. Crea account su [backblaze.com](https://www.backblaze.com/b2/sign-up.html)
2. Crea un bucket:
   - Nome: `polygonum-media`
   - Files in Bucket: Public
   - Encryption: Disabled (per semplicità)
3. Genera Application Key:
   - Dashboard → App Keys → Add a New Application Key
   - Salva:
     - `keyID` (esempio: `0051234567890abc`)
     - `applicationKey` (esempio: `K0051234567...`)
     - `Endpoint` (esempio: `s3.us-west-004.backblazeb2.com`)

### Step 2: Installazione Dipendenze

Aggiungi a `requirements.txt`:
```txt
boto3==1.35.0
django-storages[b2]==1.14.4
```

Rimuovi:
```txt
cloudinary==1.44.1
django-cloudinary-storage==0.3.0
```

### Step 3: Configurazione Django Settings

In `scambio_sito/settings.py`:

```python
# Rimuovi configurazione Cloudinary
# CLOUDINARY = { ... }
# cloudinary.config(...)
# DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Aggiungi configurazione Backblaze B2
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.b2.B2Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Backblaze B2 Settings
AWS_S3_ENDPOINT_URL = os.environ.get('B2_ENDPOINT_URL')  # https://s3.us-west-004.backblazeb2.com
AWS_ACCESS_KEY_ID = os.environ.get('B2_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('B2_APPLICATION_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('B2_BUCKET_NAME', 'polygonum-media')
AWS_S3_REGION_NAME = 'us-west-004'  # Dipende dalla tua region B2
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False

MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/file/{AWS_STORAGE_BUCKET_NAME}/'
```

Variabili d'ambiente da configurare su Render:
```
B2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
B2_KEY_ID=0051234567890abc
B2_APPLICATION_KEY=K0051234567...
B2_BUCKET_NAME=polygonum-media
```

### Step 4: Migrazione Modello Annuncio

In `scambi/models.py`:

```python
# PRIMA (con Cloudinary):
from cloudinary.models import CloudinaryField

class Annuncio(models.Model):
    immagine = CloudinaryField('image', blank=True, null=True, folder='annunci')
```

```python
# DOPO (con ImageField):
from django.db import models

class Annuncio(models.Model):
    immagine = models.ImageField(
        upload_to='annunci/%Y/%m/',  # Organizza per anno/mese
        blank=True,
        null=True,
        verbose_name="Immagine"
    )
```

### Step 5: Migrazione Database

```bash
cd ~/Desktop/polygonum
source venv/bin/activate

# Genera migration
python manage.py makemigrations scambi

# Controlla la migration generata
python manage.py sqlmigrate scambi <numero_migration>

# Applica migration
python manage.py migrate
```

La migration dovrebbe:
- Cambiare tipo colonna da `VARCHAR` (Cloudinary URL) a `VARCHAR` (path file)
- Mantenere compatibilità con dati esistenti

### Step 6: Gestione Immagini Esistenti

Due opzioni:

#### Opzione A: Download e Re-upload (Consigliato)
Script per scaricare immagini da Cloudinary e ricaricarle su B2:

```python
# scripts/migrate_images.py
import os
import requests
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from scambi.models import Annuncio

def migrate_images():
    annunci = Annuncio.objects.exclude(immagine__isnull=True).exclude(immagine='')

    for annuncio in annunci:
        # URL Cloudinary esistente
        cloudinary_url = str(annuncio.immagine)

        if not cloudinary_url or 'cloudinary.com' not in cloudinary_url:
            continue

        try:
            # Scarica immagine
            response = requests.get(cloudinary_url, stream=True)
            if response.status_code == 200:
                # Salva temporaneamente
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(response.content)
                img_temp.flush()

                # Filename
                filename = f"annuncio_{annuncio.id}.jpg"

                # Salva su B2 tramite ImageField
                annuncio.immagine.save(filename, File(img_temp), save=True)
                print(f"✅ Migrato annuncio {annuncio.id}")
            else:
                print(f"❌ Errore download annuncio {annuncio.id}: {response.status_code}")
        except Exception as e:
            print(f"❌ Errore annuncio {annuncio.id}: {e}")

if __name__ == '__main__':
    migrate_images()
```

Esegui:
```bash
python manage.py shell < scripts/migrate_images.py
```

#### Opzione B: Lasciare URL Cloudinary (Temporaneo)
- Mantieni URL esistenti in database
- Nuovi upload vanno su B2
- Quando immagine viene ricaricata, passa a B2
- Eventualmente elimina da Cloudinary manualmente dopo migrazione completa

### Step 7: Aggiornamento Form Upload

In `scambi/forms.py`, aggiungi validazione dimensioni:

```python
from django import forms
from PIL import Image
from django.core.exceptions import ValidationError

class AnnuncioForm(forms.ModelForm):
    class Meta:
        model = Annuncio
        fields = ['titolo', 'descrizione', 'immagine', ...]

    def clean_immagine(self):
        immagine = self.cleaned_data.get('immagine')

        if immagine:
            # Limite dimensione: 5MB
            if immagine.size > 5 * 1024 * 1024:
                raise ValidationError("L'immagine non può superare 5MB")

            # Verifica formato
            try:
                img = Image.open(immagine)
                if img.format not in ['JPEG', 'PNG', 'WEBP']:
                    raise ValidationError("Formato immagine non supportato. Usa JPG, PNG o WEBP")
            except Exception:
                raise ValidationError("File non valido")

        return immagine
```

### Step 8: Resize Automatico con Pillow

In `scambi/models.py`, aggiungi signal per resize:

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

@receiver(pre_save, sender=Annuncio)
def resize_image(sender, instance, **kwargs):
    if instance.immagine and hasattr(instance.immagine, 'file'):
        img = Image.open(instance.immagine.file)

        # Resize se troppo grande (max 1920px larghezza)
        if img.width > 1920 or img.height > 1920:
            output_size = (1920, 1920)
            img.thumbnail(output_size, Image.Resampling.LANCZOS)

            # Salva in memoria
            output = BytesIO()
            img_format = img.format or 'JPEG'
            img.save(output, format=img_format, quality=85, optimize=True)
            output.seek(0)

            # Sostituisci file
            instance.immagine = InMemoryUploadedFile(
                output,
                'ImageField',
                f"{instance.immagine.name.split('.')[0]}.jpg",
                'image/jpeg',
                sys.getsizeof(output),
                None
            )
```

### Step 9: Rimozione Webhook Cloudinary

In `scambi/urls.py`, rimuovi:
```python
path('webhook/cloudinary-moderation/', views.cloudinary_moderation_webhook, name='cloudinary_moderation_webhook'),
```

In `scambi/views.py`, rimuovi la funzione `cloudinary_moderation_webhook`.

### Step 10: Aggiornamento INSTALLED_APPS

In `scambio_sito/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'storages',  # Aggiungi django-storages
    # 'cloudinary_storage',  # RIMUOVI
    # 'cloudinary',  # RIMUOVI
    'scambi',
]
```

### Step 11: Testing Locale

```bash
# 1. Installa dipendenze aggiornate
pip install -r requirements.txt

# 2. Configura env vars locali
export B2_ENDPOINT_URL="https://s3.us-west-004.backblazeb2.com"
export B2_KEY_ID="your_key_id"
export B2_APPLICATION_KEY="your_app_key"
export B2_BUCKET_NAME="polygonum-media"

# 3. Testa upload
python manage.py shell

>>> from scambi.models import Annuncio
>>> from django.core.files.base import ContentFile
>>> annuncio = Annuncio.objects.first()
>>> annuncio.immagine.save('test.jpg', ContentFile(b'test'), save=True)
>>> print(annuncio.immagine.url)
# Dovrebbe mostrare URL B2
```

### Step 12: Deploy su Render

```bash
cd ~/Desktop/polygonum
git add .
git commit -m "feat: rimuovi Cloudinary, usa Backblaze B2 per storage immagini"
git push origin main
```

Render Dashboard → Environment Variables:
- `B2_ENDPOINT_URL`
- `B2_KEY_ID`
- `B2_APPLICATION_KEY`
- `B2_BUCKET_NAME`

Attendi il deploy automatico.

### Step 13: Migrazione Immagini Produzione

SSH nel server Render:
```bash
ssh srv-d37eabnfte5s73b7hqu0@ssh.oregon.render.com
```

Esegui script migrazione:
```bash
python manage.py shell < scripts/migrate_images.py
```

### Step 14: Verifica e Cleanup

1. Verifica che nuovi upload funzionino
2. Verifica che immagini migrate siano visibili
3. Disabilita account Cloudinary (o rimuovi webhook/moderation)
4. Monitora log per errori

---

## 📊 Checklist Finale

- [ ] Account Backblaze B2 creato
- [ ] Bucket configurato (public)
- [ ] Application Key generata
- [ ] `requirements.txt` aggiornato
- [ ] Settings Django aggiornate (STORAGES, B2 config)
- [ ] Modello Annuncio migrato (CloudinaryField → ImageField)
- [ ] Migration database creata e applicata
- [ ] Script migrazione immagini pronto
- [ ] Form upload con validazione dimensioni
- [ ] Signal resize immagini implementato
- [ ] Webhook Cloudinary rimosso
- [ ] INSTALLED_APPS aggiornato
- [ ] Testing locale completato
- [ ] Deploy su Render
- [ ] Variabili d'ambiente configurate su Render
- [ ] Migrazione immagini produzione completata
- [ ] Verifica funzionamento
- [ ] Account Cloudinary disabilitato

---

## 🚨 Rollback Plan

Se qualcosa va storto:

1. **Rollback Git:**
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Ripristina env vars Cloudinary su Render**

3. **Rollback migration database:**
   ```bash
   python manage.py migrate scambi <numero_migration_precedente>
   ```

4. Le immagini su Cloudinary rimangono intatte durante la migrazione

---

## ⏱️ Stima Tempi

- Setup Backblaze B2: 15 min
- Modifica codice Django: 1h
- Testing locale: 30 min
- Deploy + configurazione Render: 20 min
- Migrazione immagini produzione: variabile (dipende da numero annunci)

**Totale stimato: 2-3 ore**

---

## 📞 Supporto Backblaze

- Docs: https://www.backblaze.com/docs/cloud-storage
- django-storages docs: https://django-storages.readthedocs.io/en/latest/backends/backblaze-B2.html
