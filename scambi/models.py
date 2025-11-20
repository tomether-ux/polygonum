from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    descrizione = models.TextField(blank=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name_plural = "Categorie"

class Annuncio(models.Model):
    TIPO_CHOICES = [
        ('offro', 'Offro'),
        ('cerco', 'Cerco'),
    ]

    METODO_SCAMBIO_CHOICES = [
        ('entrambi', 'Scambio a mano o spedizione'),
        ('mano', 'Solo scambio a mano'),
        ('spedizione', 'Solo spedizione'),
    ]

    utente = models.ForeignKey(User, on_delete=models.CASCADE)
    titolo = models.CharField(max_length=200, blank=True)
    descrizione = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cerca_per_categoria = models.BooleanField(
        default=False,
        verbose_name="Cerco qualsiasi cosa in questa categoria",
        help_text="Se attivato, cerca qualsiasi oggetto nella categoria selezionata (solo per annunci 'cerco')"
    )
    # Usa CloudinaryField per storage automatico su Cloudinary
    immagine = CloudinaryField('image', blank=True, null=True, folder='annunci')

    # Nuovi campi per prezzo e modalità di scambio
    prezzo_stimato = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Prezzo stimato (€)",
        help_text="Valore indicativo dell'oggetto per facilitare scambi equi"
    )
    metodo_scambio = models.CharField(
        max_length=15,
        choices=METODO_SCAMBIO_CHOICES,
        default='entrambi',
        verbose_name="Metodo di scambio preferito"
    )
    distanza_massima_km = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Distanza massima per scambio a mano (km)",
        help_text="Solo per scambi a mano. Lascia vuoto se disponibile per spedizione"
    )

    attivo = models.BooleanField(default=True)
    disattivato_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data disattivazione",
        help_text="Timestamp di quando l'annuncio è stato disattivato (per calcolo catene)"
    )

    # Campi moderazione contenuto
    MODERATION_STATUS_CHOICES = [
        ('pending', 'In revisione'),
        ('approved', 'Approvato'),
        ('rejected', 'Rifiutato'),
    ]
    moderation_status = models.CharField(
        max_length=20,
        choices=MODERATION_STATUS_CHOICES,
        default='pending',
        verbose_name="Stato moderazione",
        help_text="Stato della revisione automatica del contenuto"
    )
    moderation_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Risultati moderazione",
        help_text="Dati completi dalla moderazione Cloudinary"
    )
    moderation_labels = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Etichette rilevate",
        help_text="Categorie problematiche rilevate (nudity, violence, etc)"
    )
    moderated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data moderazione",
        help_text="Quando è stata completata la moderazione automatica"
    )

    data_creazione = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True, verbose_name="Ultima modifica")

    def __str__(self):
        return f"{self.utente.username} - {self.tipo}: {self.titolo}"

    def clean(self):
        """
        Validazione del contenuto testuale dell'annuncio.
        Blocca parole vietate e pattern inappropriati.
        """
        from .validators import valida_annuncio_contenuto

        super().clean()

        # Valida titolo e descrizione
        try:
            valida_annuncio_contenuto(self.titolo, self.descrizione)
        except ValidationError as e:
            # Rilancia l'errore per il form
            raise e

    def save(self, *args, **kwargs):
        """Override save - ottimizzazione immagini disabilitata per compatibilità Cloudinary"""
        # NOTA: Ottimizzazione immagini temporaneamente disabilitata
        # L'ottimizzazione causava problemi con l'upload su Cloudinary
        # TODO: Implementare ottimizzazione compatibile con Cloudinary

        # if self.immagine:
        #     from .image_utils import optimize_image
        #     try:
        #         self.immagine = optimize_image(
        #             self.immagine,
        #             max_width=1200,
        #             max_height=1200,
        #             quality=85
        #         )
        #     except Exception as e:
        #         print(f"Errore nell'ottimizzazione immagine: {e}")

        # Genera titolo automatico per annunci "cerco per categoria"
        if self.tipo == 'cerco' and self.cerca_per_categoria and self.categoria:
            self.titolo = f"Cerco {self.categoria.nome}"
            print(f"📝 Titolo auto-generato: '{self.titolo}'")

        # Verifica se è un'approvazione/rifiuto manuale dall'admin
        # L'admin usa save(update_fields=['moderation_status']), l'utente no
        update_fields = kwargs.get('update_fields')
        is_admin_moderation = update_fields and 'moderation_status' in update_fields

        # Verifica se è un nuovo annuncio o se l'immagine è cambiata
        is_new = self.pk is None
        old_annuncio = None if is_new else Annuncio.objects.filter(pk=self.pk).first() if Annuncio.objects.filter(pk=self.pk).exists() else None

        # Confronta gli URL delle immagini invece degli oggetti FieldFile per evitare false positives
        old_image_url = str(old_annuncio.immagine) if (old_annuncio and old_annuncio.immagine) else None
        new_image_url = str(self.immagine) if self.immagine else None
        image_changed = is_new or (old_image_url != new_image_url)

        # Se c'è un'immagine nuova/modificata, metti in moderazione
        # ECCETTO se è l'admin che sta approvando/rifiutando manualmente
        if image_changed and self.immagine and not is_admin_moderation:
            self.moderation_status = 'pending'
            # NOTA: attivo=True (annuncio VISIBILE), solo l'IMMAGINE è nascosta finché approvata
            print(f"📋 Annuncio #{self.pk or 'NEW'} - nuova immagine in moderazione (annuncio visibile)")
        elif is_admin_moderation:
            # L'admin ha appena approvato/rifiutato, preserva lo status
            print(f"✓ Annuncio #{self.pk} - status '{self.moderation_status}' preservato (moderazione admin)")

        super().save(*args, **kwargs)

        # Triggera moderazione contenuto se c'è un'immagine nuova/modificata
        # MA SOLO se lo status è 'pending' (non se è già stata approvata/rifiutata)
        if image_changed and self.immagine and self.moderation_status == 'pending':
            self.trigger_moderation()

    def _get_optimized_url(self, width=800, quality='auto'):
        """
        Helper interno per ottenere URL ottimizzato

        Args:
            width: Larghezza massima in pixel
            quality: Qualità immagine
        """
        if self.immagine:
            try:
                url = str(self.immagine.url) if hasattr(self.immagine, 'url') else str(self.immagine)
                if url and url.strip():
                    # Aggiungi trasformazioni Cloudinary
                    upload_pos = url.find('/upload/')
                    if upload_pos != -1:
                        # f_auto: formato automatico (webp se supportato)
                        # q_auto: qualità automatica ottimizzata
                        # w_XXX: larghezza massima
                        # c_limit: non ingrandisce se l'immagine è già più piccola
                        # dpr_auto: supporto display retina
                        transformations = f"f_auto,q_{quality},w_{width},c_limit,dpr_auto"
                        optimized_url = url[:upload_pos + 8] + transformations + '/' + url[upload_pos + 8:]
                        return optimized_url
                    return url
            except (ValueError, AttributeError):
                pass
        return None

    def get_image_url(self):
        """Restituisce URL ottimizzato per visualizzazione normale (800px)"""
        url = self._get_optimized_url(width=800, quality='auto')
        if url:
            return url
        # Placeholder SVG inline (sfondo bianco, testo blu)
        return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%23ffffff" stroke="%23667eea" stroke-width="2"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" fill="%23667eea"%3ENessuna Immagine%3C/text%3E%3C/svg%3E'

    def get_thumbnail_url(self):
        """Restituisce URL ottimizzato per thumbnail/card (400px, qualità eco)"""
        url = self._get_optimized_url(width=400, quality='auto')
        if url:
            return url
        return self.get_image_url()  # Fallback al placeholder

    def get_large_image_url(self):
        """Restituisce URL ottimizzato per visualizzazione grande (1200px, alta qualità)"""
        url = self._get_optimized_url(width=1200, quality='auto')
        if url:
            return url
        return self.get_image_url()  # Fallback al placeholder

    def trigger_moderation(self):
        """
        Richiede moderazione contenuto dell'immagine tramite Cloudinary.
        Esegue in background per non bloccare la pubblicazione.
        """
        from django.conf import settings
        import threading

        if not self.immagine or not settings.CLOUDINARY_MODERATION_ENABLED:
            # Nessuna immagine o moderazione disabilitata, approva automaticamente
            self.moderation_status = 'approved'
            self.save(update_fields=['moderation_status'])
            return

        # Avvia moderazione in thread separato per non bloccare la pubblicazione
        thread = threading.Thread(
            target=self._perform_moderation_sync,
            args=(self.id, str(self.immagine)),
            daemon=True
        )
        thread.start()
        print(f"🔄 Moderazione avviata in background per annuncio #{self.id}")

    @staticmethod
    def _perform_moderation_sync(annuncio_id, public_id):
        """
        MODERAZIONE MANUALE VIA EMAIL

        Il piano FREE di Cloudinary ha un limite di 500 Admin API calls/mese esaurito.
        Invece di API automatica, invia email all'admin per moderazione manuale.

        Processo:
        1. Annuncio entra in status 'pending'
        2. Email con immagine inviata all'admin
        3. Admin clicca link Approva/Rifiuta dall'email (anche da telefono)
        """
        from django.db import close_old_connections
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        from django.urls import reverse
        from django.core.signing import Signer
        import time
        import os

        try:
            print(f"📧 Invio email moderazione per annuncio #{annuncio_id}")

            # Attendi 2 secondi per evitare race conditions
            time.sleep(2)

            # Recupera annuncio
            annuncio = Annuncio.objects.get(id=annuncio_id)

            # Crea token firmato per link sicuri
            signer = Signer()
            approve_token = signer.sign(f'approve_{annuncio_id}')
            reject_token = signer.sign(f'reject_{annuncio_id}')

            # URL base (usa RENDER_EXTERNAL_URL in produzione, localhost in dev)
            base_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8000')

            # Link per approve/reject
            approve_url = f"{base_url}/moderazione/approve/{approve_token}/"
            reject_url = f"{base_url}/moderazione/reject/{reject_token}/"

            # Componi email
            subject = f'🔍 Moderazione richiesta - Annuncio #{annuncio.id}'

            # Testo semplice (fallback)
            text_content = f"""
Nuovo annuncio da moderare

Annuncio: {annuncio.titolo}
Utente: {annuncio.utente.username}
Categoria: {annuncio.categoria.nome}
Tipo: {annuncio.get_tipo_display()}

Descrizione:
{annuncio.descrizione}

Immagine: {annuncio.get_image_url()}

---
Per approvare: {approve_url}
Per rifiutare: {reject_url}
            """

            # HTML ricco con immagine
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="margin: 0; font-size: 24px;">🔍 Moderazione Richiesta</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Annuncio #{annuncio.id}</p>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
        <h2 style="color: #667eea; margin-top: 0;">{annuncio.titolo}</h2>

        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <p style="margin: 5px 0;"><strong>👤 Utente:</strong> {annuncio.utente.username}</p>
            <p style="margin: 5px 0;"><strong>📁 Categoria:</strong> {annuncio.categoria.nome}</p>
            <p style="margin: 5px 0;"><strong>🏷️ Tipo:</strong> {annuncio.get_tipo_display()}</p>
            <p style="margin: 5px 0;"><strong>📅 Data:</strong> {annuncio.data_creazione.strftime('%d/%m/%Y %H:%M')}</p>
        </div>

        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: #667eea;">📝 Descrizione</h3>
            <p style="margin: 0;">{annuncio.descrizione}</p>
        </div>

        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 30px; text-align: center;">
            <h3 style="margin-top: 0; color: #667eea;">🖼️ Immagine</h3>
            <img src="{annuncio.get_image_url()}" alt="{annuncio.titolo}"
                 style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        </div>

        <div style="text-align: center; margin-top: 30px;">
            <a href="{approve_url}"
               style="display: inline-block; background: #10b981; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 0 10px 10px 0; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);">
                ✅ Approva
            </a>
            <a href="{reject_url}"
               style="display: inline-block; background: #ef4444; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 0 0 10px 0; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);">
                ❌ Rifiuta
            </a>
        </div>

        <p style="text-align: center; color: #666; font-size: 12px; margin-top: 30px;">
            Questa email è stata inviata automaticamente dal sistema di moderazione Polygonum
        </p>
    </div>
</body>
</html>
            """

            # Invia email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.ADMIN_MODERATION_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

            print(f"✓ Email moderazione inviata a {settings.ADMIN_MODERATION_EMAIL}")

        except Exception as e:
            print(f"✗ Errore invio email moderazione per annuncio #{annuncio_id}: {e}")
            import traceback
            traceback.print_exc()

            # In caso di errore, approva automaticamente per non bloccare l'utente
            try:
                annuncio = Annuncio.objects.get(id=annuncio_id)
                annuncio.moderation_status = 'approved'
                annuncio.save(update_fields=['moderation_status'])
                print(f"⚠️ Fallback: Annuncio #{annuncio_id} approvato automaticamente")
            except Exception:
                pass

        finally:
            # CRITICO: Chiudi connessioni DB aperte dal thread per evitare esaurimento pool
            close_old_connections()

    def handle_moderation_result(self, moderation_data):
        """
        Gestisce il risultato della moderazione (da API o webhook)

        Args:
            moderation_data: Dati JSON dalla risposta Cloudinary
                             Formato: {'moderation': [...], 'status': 'approved/rejected'}
        """
        from django.utils import timezone

        self.moderation_response = moderation_data
        self.moderated_at = timezone.now()

        # Analizza i risultati
        # AWS Rekognition restituisce: Explicit Nudity, Suggestive, Violence, Visually Disturbing, etc.
        try:
            status = moderation_data.get('status', '')
            moderation_labels = moderation_data.get('moderation', [])

            # Estrai labels problematiche
            problematic_labels = []
            for item in moderation_labels:
                if isinstance(item, dict):
                    label = item.get('label', item.get('name', ''))
                    confidence = item.get('confidence', item.get('value', 0))

                    # Soglie di confidenza
                    if confidence > 0.7:  # 70% confidenza
                        if label.lower() in ['explicit nudity', 'nudity', 'violence', 'graphic violence', 'drugs', 'weapons']:
                            problematic_labels.append({
                                'label': label,
                                'confidence': confidence
                            })

            self.moderation_labels = problematic_labels

            # Decidi: approved o rejected
            # Priorità allo status se disponibile, altrimenti usa i labels
            if status == 'rejected' or problematic_labels:
                self.moderation_status = 'rejected'
                self.attivo = False  # Disattiva annuncio automaticamente

                # Applica strike all'utente
                profile = self.utente.userprofile
                profile.content_strikes += 1

                # Sistema strike progressivo
                if profile.content_strikes == 1:
                    # Prima violazione: warning
                    ban_reason = "Prima violazione: contenuto inappropriato rilevato"
                    notifica_messaggio = (
                        f"⚠️ Il tuo annuncio '{self.titolo}' è stato rimosso perché contiene contenuto inappropriato.\n\n"
                        f"Hai ricevuto il tuo PRIMO strike. "
                        f"Ti preghiamo di rispettare le linee guida della community.\n\n"
                        f"⚠️ Attenzione: Al terzo strike riceverai un ban permanente."
                    )
                elif profile.content_strikes == 2:
                    # Seconda violazione: sospensione 7 giorni
                    from datetime import timedelta
                    profile.suspension_until = timezone.now() + timedelta(days=7)
                    ban_reason = "Seconda violazione: sospensione 7 giorni"
                    notifica_messaggio = (
                        f"🚫 Il tuo annuncio '{self.titolo}' è stato rimosso per contenuto inappropriato.\n\n"
                        f"Hai ricevuto il SECONDO strike. Il tuo account è stato SOSPESO per 7 giorni.\n\n"
                        f"⚠️ ULTIMO AVVISO: Al prossimo strike riceverai un ban permanente!"
                    )
                else:
                    # Terza violazione: ban permanente
                    profile.is_banned = True
                    profile.banned_at = timezone.now()
                    ban_reason = "Terza violazione: ban permanente"
                    notifica_messaggio = (
                        f"❌ Il tuo annuncio '{self.titolo}' è stato rimosso per contenuto inappropriato.\n\n"
                        f"Hai ricevuto il TERZO strike. Il tuo account è stato BANNATO PERMANENTEMENTE.\n\n"
                        f"Non potrai più pubblicare annunci o partecipare alla piattaforma."
                    )

                profile.ban_reason = ban_reason
                profile.save()

                # Crea notifica per informare l'utente
                # Import lazy per evitare circular import
                try:
                    Notifica.objects.create(
                        utente=self.utente,
                        tipo='sistema',
                        titolo=f'⚠️ Annuncio rimosso - Strike {profile.content_strikes}/3',
                        messaggio=notifica_messaggio,
                        letta=False
                    )
                    print(f"📬 Notifica inviata a {self.utente.username}")
                except Exception as e:
                    print(f"✗ Errore creazione notifica: {e}")

                print(f"✗ Annuncio #{self.id} REJECTED - Strike {profile.content_strikes} per {self.utente.username}")
            else:
                self.moderation_status = 'approved'
                print(f"✓ Annuncio #{self.id} APPROVED")

            self.save()

        except Exception as e:
            print(f"✗ Errore nell'analisi risultati moderazione per annuncio #{self.id}: {e}")
            # In caso di errore nell'analisi, approva per sicurezza
            self.moderation_status = 'approved'
            self.save()

    class Meta:
        verbose_name_plural = "Annunci"
        ordering = ['-data_creazione']


class Provincia(models.Model):
    """Modello per le province italiane (107 province)"""
    sigla = models.CharField(max_length=2, unique=True, verbose_name="Sigla", help_text="Es: MI, RM, TO")
    nome = models.CharField(max_length=100, verbose_name="Nome", help_text="Es: Milano, Roma, Torino")
    regione = models.CharField(max_length=50, verbose_name="Regione")

    # Coordinate del capoluogo per calcolo distanze
    latitudine = models.FloatField(verbose_name="Latitudine")
    longitudine = models.FloatField(verbose_name="Longitudine")

    class Meta:
        verbose_name = "Provincia"
        verbose_name_plural = "Province"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.sigla})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Sistema località: provincia obbligatoria + città campo libero
    provincia_obj = models.ForeignKey(
        Provincia,
        on_delete=models.PROTECT,
        verbose_name="Provincia",
        help_text="Seleziona la tua provincia"
    )
    citta = models.CharField(
        max_length=100,
        verbose_name="Città/Comune",
        help_text="Nome della tua città o comune"
    )
    cap = models.CharField(max_length=10, blank=True, verbose_name="CAP")

    # Email verification
    email_verified = models.BooleanField(default=False, verbose_name="Email Verificata")
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)

    # Premium membership
    is_premium = models.BooleanField(default=False, verbose_name="Utente Premium")
    premium_scadenza = models.DateTimeField(null=True, blank=True, verbose_name="Scadenza Premium")

    # Sistema strike e ban per violazioni
    content_strikes = models.IntegerField(
        default=0,
        verbose_name="Strike contenuto",
        help_text="Numero di violazioni per contenuto inappropriato"
    )
    is_banned = models.BooleanField(
        default=False,
        verbose_name="Utente bannato"
    )
    banned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data ban"
    )
    ban_reason = models.TextField(
        blank=True,
        verbose_name="Motivo ban",
        help_text="Descrizione del motivo del ban"
    )
    suspension_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Sospeso fino a",
        help_text="Data di fine sospensione temporanea"
    )

    def __str__(self):
        return f"{self.user.username} - {self.citta}, {self.provincia_obj.sigla}"

    def get_location_string(self):
        """Restituisce una stringa rappresentativa della posizione dell'utente"""
        return f"{self.citta}, {self.provincia_obj.nome} ({self.provincia_obj.sigla})"

    def get_distanza_km(self, altro_profilo):
        """Calcola la distanza tra due province usando le coordinate GPS (formula di Haversine)"""
        from math import radians, sin, cos, sqrt, atan2

        if not self.provincia_obj or not altro_profilo.provincia_obj:
            return 9999  # Distanza default se manca la provincia

        if self.provincia_obj == altro_profilo.provincia_obj:
            return 0  # Stessa provincia

        # Coordinate del capoluogo provincia 1
        lat1 = radians(self.provincia_obj.latitudine)
        lon1 = radians(self.provincia_obj.longitudine)

        # Coordinate del capoluogo provincia 2
        lat2 = radians(altro_profilo.provincia_obj.latitudine)
        lon2 = radians(altro_profilo.provincia_obj.longitudine)

        # Formula di Haversine
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        # Raggio della Terra in km
        r = 6371

        return int(r * c)  # Distanza in km (arrotondata)

    # === SISTEMA LIMITI ANNUNCI ===

    def get_limite_annunci(self, tipo):
        """
        Restituisce il limite di annunci per tipo (offro/cerco)
        - Free: 5 annunci per tipo
        - Premium: illimitato
        """
        if self.is_premium:
            return None  # Nessun limite
        return 5  # Limite per utenti free

    def get_count_annunci(self, tipo):
        """Conta gli annunci attivi dell'utente per tipo"""
        return Annuncio.objects.filter(
            utente=self.user,
            tipo=tipo,
            attivo=True
        ).count()

    def puo_creare_annuncio(self, tipo):
        """
        Verifica se l'utente può creare un nuovo annuncio del tipo specificato
        Returns: (bool, str) - (può_creare, messaggio_errore)
        """
        if self.is_premium:
            return True, ""

        limite = self.get_limite_annunci(tipo)
        count_attuale = self.get_count_annunci(tipo)

        if count_attuale >= limite:
            tipo_display = "offro" if tipo == "offro" else "cerco"
            return False, f"Hai raggiunto il limite di {limite} annunci '{tipo_display}'. Passa a Premium per annunci illimitati!"

        return True, ""

    def get_annunci_rimanenti(self, tipo):
        """Calcola quanti annunci può ancora creare l'utente per tipo"""
        if self.is_premium:
            return None  # Illimitati

        limite = self.get_limite_annunci(tipo)
        count_attuale = self.get_count_annunci(tipo)
        return max(0, limite - count_attuale)

    class Meta:
        verbose_name = "Profilo Utente"
        verbose_name_plural = "Profili Utenti"


class Preferiti(models.Model):
    """Modello per gestire gli annunci preferiti degli utenti"""
    utente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferiti')
    annuncio = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='preferito_da')
    data_aggiunta = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('utente', 'annuncio')
        verbose_name = "Preferito"
        verbose_name_plural = "Preferiti"
        ordering = ['-data_aggiunta']

    def __str__(self):
        return f"{self.utente.username} - {self.annuncio.titolo}"


class Notifica(models.Model):
    """Modello per gestire le notifiche utente"""
    TIPO_CHOICES = [
        ('nuova_catena', 'Nuova catena di scambio disponibile'),
        ('preferito_aggiunto', 'Il tuo annuncio è stato aggiunto ai preferiti'),
        ('proposta_scambio', 'Nuova proposta di scambio'),
        ('proposta_catena', 'Qualcuno è interessato a una catena'),
        ('risposta_proposta_catena', 'Qualcuno ha risposto alla tua proposta'),
        ('tutti_interessati', 'Tutti sono interessati alla catena'),
        ('proposta_rifiutata', 'Qualcuno ha rifiutato la proposta'),
        ('benvenuto', 'Messaggio di benvenuto'),
        ('sistema', 'Notifica di sistema'),
    ]

    utente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifiche')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    titolo = models.CharField(max_length=200)
    messaggio = models.TextField()
    letta = models.BooleanField(default=False)
    data_creazione = models.DateTimeField(auto_now_add=True)

    # Collegamenti opzionali ad altri oggetti
    annuncio_collegato = models.ForeignKey(Annuncio, on_delete=models.CASCADE, null=True, blank=True)
    utente_collegato = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifiche_generate')
    url_azione = models.CharField(max_length=500, blank=True, null=True, help_text="URL o path relativo per azione della notifica")

    class Meta:
        verbose_name = "Notifica"
        verbose_name_plural = "Notifiche"
        ordering = ['-data_creazione']

    def __str__(self):
        return f"{self.utente.username} - {self.get_tipo_display()}"

    def mark_as_read(self):
        """Segna la notifica come letta"""
        self.letta = True
        self.save()


class PropostaScambio(models.Model):
    """Modello per gestire le proposte di scambio tra utenti"""
    STATO_CHOICES = [
        ('in_attesa', 'In attesa di risposta'),
        ('accettata', 'Accettata'),
        ('rifiutata', 'Rifiutata'),
        ('completata', 'Scambio completato'),
    ]

    richiedente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposte_inviate')
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposte_ricevute')

    # Annunci coinvolti nello scambio
    annuncio_offerto = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='proposte_come_offerto')
    annuncio_richiesto = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='proposte_come_richiesto')

    messaggio = models.TextField(blank=True, help_text="Messaggio opzionale dal richiedente")
    stato = models.CharField(max_length=15, choices=STATO_CHOICES, default='in_attesa')

    data_creazione = models.DateTimeField(auto_now_add=True)
    data_risposta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Proposta di Scambio"
        verbose_name_plural = "Proposte di Scambio"
        ordering = ['-data_creazione']

    def __str__(self):
        return f"{self.richiedente.username} → {self.destinatario.username}: {self.annuncio_offerto.titolo} ↔ {self.annuncio_richiesto.titolo}"


# === SISTEMA MESSAGGISTICA ===

class Conversazione(models.Model):
    """Conversazione tra due utenti"""
    TIPO_CHOICES = [
        ('privata', 'Conversazione Privata'),
        ('gruppo', 'Chat di Gruppo'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='privata')
    utenti = models.ManyToManyField(User, related_name='conversazioni')
    nome = models.CharField(max_length=200, blank=True, help_text="Nome della chat di gruppo")

    # Per chat di gruppo legate a catene di scambio
    catena_scambio_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID della catena di scambio")
    attiva = models.BooleanField(default=True)

    data_creazione = models.DateTimeField(auto_now_add=True)
    ultimo_messaggio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conversazione"
        verbose_name_plural = "Conversazioni"
        ordering = ['-ultimo_messaggio']

    def __str__(self):
        if self.tipo == 'gruppo':
            return f"Gruppo: {self.nome or f'Catena {self.catena_scambio_id}'}"
        else:
            utenti = list(self.utenti.all()[:2])
            if len(utenti) == 2:
                return f"{utenti[0].username} ↔ {utenti[1].username}"
            return f"Conversazione {self.id}"

    def get_altri_utenti(self, utente_corrente):
        """Restituisce gli altri utenti nella conversazione"""
        return self.utenti.exclude(id=utente_corrente.id)

    def get_nome_display(self, utente_corrente):
        """Nome da mostrare per la conversazione"""
        if self.tipo == 'gruppo':
            return self.nome or f"Catena di Scambio #{self.catena_scambio_id}"
        else:
            altri = self.get_altri_utenti(utente_corrente)
            if altri.exists():
                return altri.first().username
            return "Conversazione"


class Messaggio(models.Model):
    """Singolo messaggio in una conversazione"""
    conversazione = models.ForeignKey(Conversazione, on_delete=models.CASCADE, related_name='messaggi')
    mittente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messaggi_inviati')
    contenuto = models.TextField()

    # Per messaggi di sistema (es. "Mario ha attivato la catena")
    is_sistema = models.BooleanField(default=False)

    data_invio = models.DateTimeField(auto_now_add=True)
    letto_da = models.ManyToManyField(User, through='LetturaMessaggio', related_name='messaggi_letti')

    class Meta:
        verbose_name = "Messaggio"
        verbose_name_plural = "Messaggi"
        ordering = ['data_invio']

    def __str__(self):
        return f"{self.mittente.username}: {self.contenuto[:50]}..."

    def mark_as_read(self, utente):
        """Segna il messaggio come letto da un utente"""
        LetturaMessaggio.objects.get_or_create(messaggio=self, utente=utente)


class LetturaMessaggio(models.Model):
    """Traccia quando un utente ha letto un messaggio"""
    messaggio = models.ForeignKey(Messaggio, on_delete=models.CASCADE)
    utente = models.ForeignKey(User, on_delete=models.CASCADE)
    data_lettura = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('messaggio', 'utente')
        verbose_name = "Lettura Messaggio"
        verbose_name_plural = "Letture Messaggi"


class CatenaScambio(models.Model):
    """Rappresenta una catena di scambio attivabile"""
    STATO_CHOICES = [
        ('proposta', 'Proposta'),
        ('attiva', 'Attiva'),
        ('completata', 'Completata'),
        ('annullata', 'Annullata'),
    ]

    catena_id = models.CharField(max_length=100, unique=True, help_text="ID univoco della catena")
    nome = models.CharField(max_length=200, help_text="Nome descrittivo della catena")
    descrizione = models.TextField(blank=True, help_text="Descrizione degli scambi nella catena")

    # Dati della catena (JSON)
    dati_catena = models.JSONField(help_text="Dati completi della catena dal sistema di matching")

    stato = models.CharField(max_length=15, choices=STATO_CHOICES, default='proposta')
    utente_attivatore = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='catene_attivate')

    # Partecipanti
    partecipanti = models.ManyToManyField(User, through='PartecipazioneScambio', related_name='catene_partecipate')

    data_creazione = models.DateTimeField(auto_now_add=True)
    data_attivazione = models.DateTimeField(null=True, blank=True)
    data_completamento = models.DateTimeField(null=True, blank=True)

    # Chat di gruppo collegata
    conversazione = models.OneToOneField(Conversazione, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Catena di Scambio"
        verbose_name_plural = "Catene di Scambio"
        ordering = ['-data_creazione']

    def __str__(self):
        return f"{self.nome} ({self.get_stato_display()})"

    def attiva_catena(self, utente_attivatore):
        """Attiva la catena e crea la chat di gruppo"""
        from .notifications import notifica_catena_attivata

        self.stato = 'attiva'
        self.utente_attivatore = utente_attivatore
        self.data_attivazione = timezone.now()

        # Crea chat di gruppo
        if not self.conversazione:
            conv = Conversazione.objects.create(
                tipo='gruppo',
                nome=self.nome,
                catena_scambio_id=self.catena_id
            )
            conv.utenti.set(self.partecipanti.all())
            self.conversazione = conv

        self.save()

        # Invia notifiche a tutti i partecipanti
        for partecipante in self.partecipanti.exclude(id=utente_attivatore.id):
            notifica_catena_attivata(partecipante, self, utente_attivatore)

        # Messaggio di sistema nella chat
        if self.conversazione:
            Messaggio.objects.create(
                conversazione=self.conversazione,
                mittente=utente_attivatore,
                contenuto=f"🎉 {utente_attivatore.username} ha attivato la catena di scambio! Potete ora coordinarvi per completare gli scambi.",
                is_sistema=True
            )


class PartecipazioneScambio(models.Model):
    """Partecipazione di un utente a una catena di scambio"""
    STATO_CHOICES = [
        ('invitato', 'Invitato'),
        ('accettato', 'Accettato'),
        ('completato', 'Completato'),
        ('rifiutato', 'Rifiutato'),
    ]

    catena = models.ForeignKey(CatenaScambio, on_delete=models.CASCADE)
    utente = models.ForeignKey(User, on_delete=models.CASCADE)
    stato = models.CharField(max_length=15, choices=STATO_CHOICES, default='invitato')

    # Dettagli dello scambio per questo utente
    annuncio_da_dare = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='scambi_dare')
    annuncio_da_ricevere = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='scambi_ricevere')

    data_partecipazione = models.DateTimeField(auto_now_add=True)
    data_completamento = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('catena', 'utente')
        verbose_name = "Partecipazione Scambio"
        verbose_name_plural = "Partecipazioni Scambi"

    def __str__(self):
        return f"{self.utente.username} in {self.catena.nome}"


class CatenaPreferita(models.Model):
    """Modello per gestire le catene di scambio preferite degli utenti"""
    utente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='catene_preferite')

    # ID univoco della catena basato sui partecipanti e annunci
    catena_hash = models.CharField(max_length=64, help_text="Hash unico della catena basato sui partecipanti")

    # Dati della catena salvati per visualizzazione futura
    catena_data = models.JSONField(help_text="Dati completi della catena per visualizzazione")

    # Metadati
    data_aggiunta = models.DateTimeField(auto_now_add=True)
    tipo_catena = models.CharField(max_length=20, choices=[
        ('scambio_diretto', 'Scambio Diretto'),
        ('catena_lunga', 'Catena Lunga'),
    ])
    categoria_qualita = models.CharField(max_length=20, choices=[
        ('alta', 'Alta Qualità'),
        ('generica', 'Generica'),
    ])

    class Meta:
        unique_together = ('utente', 'catena_hash')
        verbose_name = "Catena Preferita"
        verbose_name_plural = "Catene Preferite"
        ordering = ['-data_aggiunta']

    def __str__(self):
        return f"Catena preferita di {self.utente.username} ({self.tipo_catena})"


# === SISTEMA CALCOLO CICLI SEPARATO ===

class CicloScambio(models.Model):
    """
    Modello per memorizzare i cicli di scambio precalcolati
    Utilizzato dal sistema di calcolo separato per performance ottimali
    """

    # Array di user_id che formano il ciclo (ordinato e normalizzato)
    # Es: [1, 3, 7] significa User(1) -> User(3) -> User(7) -> User(1)
    users = models.JSONField(
        help_text="Array ordinato di user_id che formano il ciclo"
    )

    # Lunghezza del ciclo (2-6 utenti)
    lunghezza = models.IntegerField(
        help_text="Numero di utenti nel ciclo"
    )

    # Dettagli completi del ciclo (annunci coinvolti, oggetti scambiati, etc.)
    dettagli = models.JSONField(
        help_text="Dettagli completi del ciclo: annunci, oggetti, compatibilità"
    )

    # Metadati di calcolo
    calcolato_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp dell'ultimo calcolo"
    )

    # Flag per invalidare cicli vecchi/non più validi
    valido = models.BooleanField(
        default=True,
        help_text="Indica se il ciclo è ancora valido (annunci attivi)"
    )

    # Hash unico del ciclo per evitare duplicati
    hash_ciclo = models.CharField(
        max_length=64,
        unique=True,
        help_text="Hash MD5 del ciclo per rilevare duplicati"
    )

    class Meta:
        verbose_name = "Ciclo di Scambio"
        verbose_name_plural = "Cicli di Scambio"
        ordering = ['lunghezza', '-calcolato_at']

        # Indici per query veloci
        indexes = [
            models.Index(fields=['valido', 'lunghezza']),
            models.Index(fields=['calcolato_at']),
            models.Index(fields=['hash_ciclo']),
        ]

    def __str__(self):
        users_str = " → ".join([f"User({uid})" for uid in self.users])
        return f"Ciclo {self.lunghezza} utenti: {users_str}"

    def to_dict(self):
        """
        Serializza il ciclo per l'API JSON
        """
        return {
            'id': self.id,
            'users': self.users,
            'lunghezza': self.lunghezza,
            'dettagli': self.dettagli,
            'calcolato_at': self.calcolato_at.isoformat(),
            'valido': self.valido,
            'hash_ciclo': self.hash_ciclo
        }

    def contains_user(self, user_id):
        """
        Verifica se un utente è presente nel ciclo
        """
        return user_id in self.users

    @classmethod
    def find_for_user(cls, user_id, limit=50):
        """
        Query ottimizzata per trovare cicli contenenti un utente specifico
        """
        from django.db.models import Q

        # Costruisce query JSON per PostgreSQL o fallback per SQLite
        if 'postgresql' in settings.DATABASES['default']['ENGINE']:
            # PostgreSQL: usa operatori JSON nativi
            return cls.objects.filter(
                valido=True,
                users__contains=user_id
            ).order_by('lunghezza', '-calcolato_at')[:limit]
        else:
            # SQLite: usa icontains come fallback (meno efficiente ma funziona)
            return cls.objects.filter(
                valido=True,
                users__icontains=f'"{user_id}"'
            ).order_by('lunghezza', '-calcolato_at')[:limit]

    @classmethod
    def invalidate_all(cls):
        """
        Invalida tutti i cicli esistenti (chiamato prima del ricalcolo)
        """
        return cls.objects.update(valido=False)

    @classmethod
    def cleanup_old(cls, days=7):
        """
        Rimuove i cicli invalidati più vecchi di N giorni
        """
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return cls.objects.filter(
            valido=False,
            calcolato_at__lt=cutoff
        ).delete()


# === SISTEMA PROPOSTE CATENE MVP ===

class PropostaCatena(models.Model):
    """
    Modello per gestire le proposte di catene di scambio
    MVP: tracking di chi è interessato a una catena
    """
    STATO_CHOICES = [
        ('in_attesa', 'In attesa'),
        ('tutti_interessati', 'Tutti interessati'),
        ('rifiutata', 'Rifiutata'),
        ('annullata', 'Annullata'),
    ]

    # Il ciclo di scambio proposto
    ciclo = models.ForeignKey(CicloScambio, on_delete=models.CASCADE, related_name='proposte')

    # Chi ha iniziato la proposta
    iniziatore = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposte_catena_iniziate')

    # Stato della proposta
    stato = models.CharField(max_length=20, choices=STATO_CHOICES, default='in_attesa')

    # Timestamps
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_ultimo_aggiornamento = models.DateTimeField(auto_now=True)

    # Scadenza proposta (7 giorni dalla creazione)
    data_scadenza = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data di scadenza della proposta (auto-calcolata: creazione + 7 giorni)"
    )

    # Flag per reminder
    reminder_inviato = models.BooleanField(
        default=False,
        help_text="Indica se il reminder di scadenza è stato inviato"
    )

    class Meta:
        verbose_name = "Proposta Catena"
        verbose_name_plural = "Proposte Catene"
        ordering = ['-data_creazione']
        # Una catena può avere una sola proposta attiva
        unique_together = ('ciclo', 'iniziatore')

    def __str__(self):
        return f"Proposta di {self.iniziatore.username} per ciclo {self.ciclo.id} ({self.get_stato_display()})"

    def get_utenti_coinvolti(self):
        """Restituisce tutti gli utenti coinvolti nel ciclo"""
        from django.contrib.auth.models import User
        return User.objects.filter(id__in=self.ciclo.users)

    def get_count_interessati(self):
        """Conta quanti utenti sono interessati"""
        return self.risposte.filter(risposta='interessato').count()

    def get_count_totale(self):
        """Conta quanti utenti totali sono coinvolti"""
        return len(self.ciclo.users)

    def check_tutti_interessati(self):
        """Verifica se tutti sono interessati e aggiorna lo stato"""
        if self.get_count_interessati() == self.get_count_totale():
            self.stato = 'tutti_interessati'
            self.save()
            return True
        return False

    def annulla(self):
        """Annulla la proposta"""
        self.stato = 'annullata'
        self.save()

    def save(self, *args, **kwargs):
        """Override save per calcolare la data_scadenza automaticamente"""
        if not self.data_scadenza:
            from datetime import timedelta
            self.data_scadenza = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_scaduta(self):
        """Verifica se la proposta è scaduta"""
        return timezone.now() > self.data_scadenza

    def giorni_alla_scadenza(self):
        """Calcola quanti giorni mancano alla scadenza"""
        if self.is_scaduta():
            return 0
        delta = self.data_scadenza - timezone.now()
        return delta.days

    def necessita_reminder(self):
        """Verifica se è il momento di inviare il reminder (1 giorno prima della scadenza)"""
        if self.reminder_inviato or self.is_scaduta():
            return False
        giorni_rimasti = self.giorni_alla_scadenza()
        return giorni_rimasti <= 1


class RispostaProposta(models.Model):
    """
    Modello per le risposte degli utenti a una proposta di catena
    """
    RISPOSTA_CHOICES = [
        ('in_attesa', 'In attesa'),
        ('interessato', 'Interessato'),
        ('non_interessato', 'Non interessato'),
    ]

    proposta = models.ForeignKey(PropostaCatena, on_delete=models.CASCADE, related_name='risposte')
    utente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='risposte_proposte_catena')
    risposta = models.CharField(max_length=20, choices=RISPOSTA_CHOICES, default='in_attesa')

    data_risposta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Risposta Proposta"
        verbose_name_plural = "Risposte Proposte"
        unique_together = ('proposta', 'utente')
        ordering = ['data_risposta']

    def __str__(self):
        return f"{self.utente.username}: {self.get_risposta_display()} per proposta {self.proposta.id}"

    def segna_interessato(self):
        """Segna l'utente come interessato"""
        self.risposta = 'interessato'
        self.data_risposta = timezone.now()
        self.save()

        # Controlla se tutti sono interessati
        self.proposta.check_tutti_interessati()

    def segna_non_interessato(self):
        """Segna l'utente come non interessato"""
        self.risposta = 'non_interessato'
        self.data_risposta = timezone.now()
        self.save()

        # Annulla la proposta se qualcuno non è interessato
        self.proposta.stato = 'rifiutata'
        self.proposta.save()


# === SISTEMA CALCOLO INCREMENTALE ===

class CalcoloMetadata(models.Model):
    """
    Modello per tracciare i metadati dell'ultimo calcolo cicli
    Utilizzato per il calcolo incrementale
    """
    # Singleton pattern: solo 1 record nel DB
    singleton_id = models.IntegerField(default=1, unique=True)

    # Timestamp dell'ultimo calcolo completo
    ultimo_calcolo_completo = models.DateTimeField(
        help_text="Timestamp dell'ultimo calcolo completo di tutti i cicli"
    )

    # Statistiche dell'ultimo calcolo
    cicli_calcolati = models.IntegerField(default=0)
    durata_calcolo_secondi = models.FloatField(default=0.0)

    class Meta:
        verbose_name = "Metadata Calcolo"
        verbose_name_plural = "Metadata Calcoli"

    def __str__(self):
        return f"Ultimo calcolo: {self.ultimo_calcolo_completo}"

    @classmethod
    def get_or_create_singleton(cls):
        """Ottiene o crea il record singleton"""
        obj, created = cls.objects.get_or_create(
            singleton_id=1,
            defaults={'ultimo_calcolo_completo': timezone.now()}
        )
        return obj

    @classmethod
    def aggiorna_calcolo(cls, cicli_count, durata):
        """Aggiorna i metadati dopo un calcolo"""
        obj = cls.get_or_create_singleton()
        obj.ultimo_calcolo_completo = timezone.now()
        obj.cicli_calcolati = cicli_count
        obj.durata_calcolo_secondi = durata
        obj.save()
        return obj
