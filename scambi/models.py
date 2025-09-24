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
