from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from django.db import transaction
from .models import Annuncio, Categoria, UserProfile, Provincia

class CustomUserCreationForm(UserCreationForm):
    citta = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Es: Milano, Trieste, Brescia...'
        }),
        label='Città/Comune (consigliato)',
        help_text='Inserisci il nome della tua città o comune per dare più informazioni agli altri utenti'
    )
    provincia_obj = forms.ModelChoiceField(
        queryset=Provincia.objects.all().order_by('nome'),
        required=True,
        empty_label="Seleziona una provincia...",
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Provincia *',
        help_text='Seleziona la tua provincia dal menu'
    )
    accetta_regolamento = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='',  # Lasciamo vuoto, renderizziamo il label custom nel template
        error_messages={
            'required': 'Devi accettare il regolamento per registrarti.'
        }
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "citta", "provincia_obj", "accetta_regolamento")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].required = True  # Rendi l'email obbligatoria
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        """Valida unicità email (SECURITY: previene account duplicati)"""
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'Questa email è già registrata. Usa un\'altra email o effettua il login.'
            )
        return email

    def save(self, commit=True):
        import logging
        logger = logging.getLogger(__name__)

        user = super().save(commit=False)
        user.is_active = False

        if not commit:
            return user

        citta_data = self.cleaned_data.get('citta', '')
        provincia_obj_data = self.cleaned_data['provincia_obj']

        # Utente, profilo e notifica sono un'unica operazione: se uno dei tre
        # salvataggi fallisce non resta nel database un account a metà.
        try:
            with transaction.atomic():
                user.save()
                user_profile = UserProfile.objects.create(
                    user=user,
                    citta=citta_data,
                    provincia_obj=provincia_obj_data,
                    email_verified=False,
                )

                from .notifications import notifica_benvenuto
                notifica_benvenuto(user)

            logger.info(
                "User and profile created user_id=%s profile_id=%s",
                user.id,
                user_profile.id,
            )
            return user
        except Exception as exc:
            logger.error(
                "Atomic user/profile creation failed error_type=%s",
                type(exc).__name__,
            )
            raise

class AnnuncioForm(forms.ModelForm):
    MAX_TITOLO_CARATTERI = 60
    MAX_TITOLO_PAROLE = 8

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .value_bands import INPUT_CHOICES, LEGACY_CHOICES
        choices = [('', 'Scegli la fascia')] + INPUT_CHOICES
        if self.instance.pk and self.instance.fascia_prezzo in dict(LEGACY_CHOICES):
            choices.append((self.instance.fascia_prezzo,
                            f'{self.instance.get_fascia_prezzo_display()} · fascia precedente'))
        self.fields['fascia_prezzo'].choices = choices
        self.fields['fascia_secondaria'].choices = [('', 'Nessuna seconda fascia')] + INPUT_CHOICES

    class Meta:
        model = Annuncio
        fields = ['titolo', 'descrizione', 'categoria', 'tipo', 'cerca_per_categoria', 'immagine',
                 'fascia_prezzo', 'fascia_secondaria', 'condizione', 'metodo_scambio', 'distanza_massima_km']
        widgets = {
            'titolo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: Chitarra elettrica Fender',
                'maxlength': 60,
            }),
            'descrizione': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descrivi il tuo annuncio...'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'cerca_per_categoria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'immagine': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'onchange': 'previewImage(this);'
            }),
            'fascia_prezzo': forms.Select(attrs={'class': 'form-control fascia-prezzo-select'}),
            'fascia_secondaria': forms.Select(attrs={'class': 'form-select'}),
            'condizione': forms.Select(attrs={'class': 'form-control'}),
            'metodo_scambio': forms.Select(attrs={'class': 'form-control'}),
            'distanza_massima_km': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: 50',
                'min': '1',
                'max': '1000'
            }),
        }
        labels = {
            'titolo': 'Titolo annuncio',
            'descrizione': 'Descrizione',
            'categoria': 'Categoria',
            'tipo': 'Tipo annuncio',
            'cerca_per_categoria': 'Cerco qualsiasi cosa in questa categoria',
            'immagine': 'Foto dell\'oggetto (obbligatoria per Offro)',
            'fascia_secondaria': 'Seconda fascia adiacente (facoltativa)',
            'fascia_prezzo': 'Fascia di valore dell\'oggetto *',
            'condizione': 'Condizioni dell\'oggetto',
            'metodo_scambio': 'Come preferisci scambiare?',
            'distanza_massima_km': 'Distanza massima per incontro (km)'
        }

    def clean_titolo(self):
        """Mantiene il titolo sintetico per evitare match troppo generici."""
        titolo = ' '.join((self.cleaned_data.get('titolo') or '').split())
        if len(titolo) > self.MAX_TITOLO_CARATTERI:
            raise forms.ValidationError(
                f'Il titolo può contenere al massimo {self.MAX_TITOLO_CARATTERI} caratteri.'
            )
        if len(titolo.split()) > self.MAX_TITOLO_PAROLE:
            raise forms.ValidationError(
                f'Il titolo può contenere al massimo {self.MAX_TITOLO_PAROLE} parole. '
                'Usa la descrizione per gli altri dettagli.'
            )
        return titolo

    def clean(self):
        """Validazione personalizzata del form"""
        from .validators import valida_annuncio_contenuto
        from django.core.exceptions import ValidationError
        import logging
        logger = logging.getLogger(__name__)

        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        cerca_per_categoria = cleaned_data.get('cerca_per_categoria')
        titolo = cleaned_data.get('titolo')
        descrizione = cleaned_data.get('descrizione')

        logger.debug("AnnuncioForm validation started")

        # Il flag cerca_per_categoria può essere usato SOLO su annunci "cerco"
        if cerca_per_categoria and tipo != 'cerco':
            raise forms.ValidationError(
                "L'opzione 'Cerca per categoria' è disponibile solo per annunci di tipo 'Cerco'."
            )

        # Se cerca_per_categoria è attivo, il titolo è opzionale (verrà auto-generato)
        # Altrimenti, il titolo è obbligatorio E deve essere almeno 3 caratteri
        if not cerca_per_categoria:
            if not titolo:
                self.add_error('titolo', 'Il titolo è obbligatorio.')
            elif len(titolo.strip()) < 3:
                self.add_error('titolo', 'Il titolo deve contenere almeno 3 caratteri per permettere il matching con altri annunci.')

        # Fascia di valore obbligatoria
        fascia_prezzo = cleaned_data.get('fascia_prezzo')
        if not fascia_prezzo:
            self.add_error('fascia_prezzo', 'Inserisci la fascia di valore dell\'oggetto.')
        from .value_bands import adjacent
        secondary = cleaned_data.get('fascia_secondaria')
        if secondary and not adjacent(fascia_prezzo, secondary):
            self.add_error('fascia_secondaria', 'Scegli una fascia immediatamente vicina alla principale.')
        # Existing offers keep their placeholder until republication.
        if tipo == 'offro' and not cleaned_data.get('immagine') and (
            not self.instance.pk or self.instance.tipo != 'offro'
        ):
            self.add_error('immagine', 'Carica una foto dell’oggetto che offri.')

        # Validazione contenuto testuale (parole vietate e pattern inappropriati)
        if titolo or descrizione:
            logger.debug("Annuncio content validation started")
            valida_annuncio_contenuto(titolo or '', descrizione or '')
            logger.debug("Annuncio content validation passed")

        return cleaned_data

    def save(self, commit=True):
        """Store the selected bands, never invent a monetary value."""
        instance = super().save(commit=False)

        if instance.fascia_prezzo.startswith('v'):
            instance.prezzo_stimato = None

        if commit:
            instance.save()

        return instance


class FotoRipubblicazioneForm(forms.ModelForm):
    class Meta:
        model = Annuncio
        fields = ['immagine']
        widgets = {'immagine': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})}

    def clean_immagine(self):
        image = self.cleaned_data.get('immagine')
        if not image:
            raise forms.ValidationError('Carica una foto per ripubblicare il tuo annuncio Offro.')
        return image

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['citta', 'provincia_obj', 'cap']
        widgets = {
            'citta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: Milano, Trieste, Brescia...'
            }),
            'provincia_obj': forms.Select(attrs={
                'class': 'form-control',
            }),
            'cap': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: 00100, 20121...'
            }),
        }
        labels = {
            'citta': 'Città/Comune (opzionale)',
            'provincia_obj': 'Provincia *',
            'cap': 'CAP (opzionale)'
        }
        help_texts = {
            'citta': 'Inserisci il nome della tua città o comune',
            'provincia_obj': 'Seleziona la tua provincia dal menu'
        }


class RicercaAvanzataForm(forms.Form):
    """Form per la ricerca avanzata degli annunci"""

    # Campo di ricerca principale
    q = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cerca prodotti, marchi, descrizioni...',
            'aria-label': 'Cerca annunci'
        }),
        label='Ricerca'
    )

    # Filtro per tipo (offro/cerco)
    tipo = forms.ChoiceField(
        choices=[('', 'Tutti')] + Annuncio.TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo'
    )

    # Filtro per categoria
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        empty_label="Tutte le categorie",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Categoria'
    )

    # Filtro per condizione
    condizione = forms.ChoiceField(
        choices=[('', 'Tutte le condizioni')] + Annuncio.CONDIZIONE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Condizione'
    )

    # Filtro per città
    citta = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Es: Milano, Roma, Napoli...'
        }),
        label='Città'
    )

    # Filtro per regione
    regione = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Es: Lombardia, Lazio...'
        }),
        label='Regione'
    )

    # La ricerca pubblica usa la fascia scelta dall'utente, non il valore
    # numerico interno impiegato dal matching.
    fascia_prezzo = forms.ChoiceField(
        choices=[('', 'Tutte le fasce')] + Annuncio.FASCIA_PREZZO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Fascia di prezzo'
    )

    # Filtro per spedizione
    spedizione = forms.ChoiceField(
        choices=[
            ('', 'Qualsiasi modalità'),
            ('si', 'Con spedizione'),
            ('no', 'Solo scambio a mano'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Spedizione'
    )

    # Filtro per distanza massima (km)
    distanza_max = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Es: 50',
            'step': '10'
        }),
        label='Distanza max (km)',
        help_text='Mostra solo annunci entro questa distanza dalla tua città'
    )

    # Ordinamento
    ORDINAMENTO_CHOICES = [
        ('-pubblicato_at', 'Più recenti'),
        ('pubblicato_at', 'Meno recenti'),
        ('titolo', 'A-Z'),
        ('-titolo', 'Z-A'),
    ]

    ordinamento = forms.ChoiceField(
        choices=ORDINAMENTO_CHOICES,
        required=False,
        initial='-pubblicato_at',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Ordina per'
    )

class RicercaVeloceForm(forms.Form):
    """Form semplificato per la ricerca veloce nella navbar"""

    q = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cerca annunci...',
            'aria-label': 'Ricerca veloce'
        })
    )
