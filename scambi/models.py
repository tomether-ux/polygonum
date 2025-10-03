from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
