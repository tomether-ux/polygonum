from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

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
    titolo = models.CharField(max_length=200)
    descrizione = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    immagine = models.ImageField(upload_to='annunci/', blank=True, null=True)

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
    data_creazione = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.utente.username} - {self.tipo}: {self.titolo}"
    
    def get_image_url(self):
        """Restituisce l'URL dell'immagine o un'immagine placeholder"""
        if self.immagine and hasattr(self.immagine, 'url'):
            return self.immagine.url
        return '/static/images/no-image.png'  # Placeholder per annunci senza foto

    class Meta:
        verbose_name_plural = "Annunci"
        ordering = ['-data_creazione']

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    citta = models.CharField(max_length=100, blank=False, verbose_name="Città")
    provincia = models.CharField(max_length=50, blank=True, verbose_name="Provincia")
    regione = models.CharField(max_length=50, blank=True, verbose_name="Regione")
    cap = models.CharField(max_length=10, blank=True, verbose_name="CAP")

    # Coordinate geografiche (per calcoli di distanza più precisi)
    latitudine = models.FloatField(null=True, blank=True)
    longitudine = models.FloatField(null=True, blank=True)

    # Email verification
    email_verified = models.BooleanField(default=False, verbose_name="Email Verificata")
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        if self.citta:
            return f"{self.user.username} - {self.citta}"
        return f"{self.user.username} - No città"

    def get_location_string(self):
        """Restituisce una stringa rappresentativa della posizione"""
        parts = []
        if self.citta:
            parts.append(self.citta)
        if self.provincia:
            parts.append(self.provincia)
        return ", ".join(parts) if parts else "Posizione non specificata"

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
        ('benvenuto', 'Messaggio di benvenuto'),
        ('sistema', 'Notifica di sistema'),
    ]

    utente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifiche')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titolo = models.CharField(max_length=200)
    messaggio = models.TextField()
    letta = models.BooleanField(default=False)
    data_creazione = models.DateTimeField(auto_now_add=True)

    # Collegamenti opzionali ad altri oggetti
    annuncio_collegato = models.ForeignKey(Annuncio, on_delete=models.CASCADE, null=True, blank=True)
    utente_collegato = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifiche_generate')
    url_azione = models.URLField(blank=True, null=True, help_text="URL per azione della notifica")

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
