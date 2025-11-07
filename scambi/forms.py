from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Annuncio, Categoria, UserProfile

class CustomUserCreationForm(UserCreationForm):
    citta = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Es: Roma, Milano, Torino...'
        }),
        label='Città *'
    )
    provincia = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Es: RM, MI, TO...'
        }),
        label='Provincia (opzionale)'
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "citta", "provincia")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].required = True  # Rendi l'email obbligatoria
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        import logging
        logger = logging.getLogger(__name__)

        user = super().save(commit=commit)
        if commit:
            # Disabilita l'utente fino alla verifica email
            user.is_active = False
            user.save()

            # Debug: Log data before creating profile
            citta_data = self.cleaned_data.get('citta', '')
            provincia_data = self.cleaned_data.get('provincia', '')
            logger.info(f"Creating UserProfile for {user.username}")
            logger.info(f"City data: '{citta_data}'")
            logger.info(f"Province data: '{provincia_data}'")

            try:
                # Get or create profile (signal might have already created it)
                user_profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'citta': citta_data,
                        'provincia': provincia_data,
                        'email_verified': False
                    }
                )

                # If profile already existed (created by signal), update it with form data
                if not created:
                    user_profile.citta = citta_data
                    user_profile.provincia = provincia_data
                    user_profile.email_verified = False
                    user_profile.save()
                    logger.info(f"UserProfile updated with form data - ID: {user_profile.id}")
                else:
                    logger.info(f"UserProfile created successfully - ID: {user_profile.id}")

                logger.info(f"Saved City: '{user_profile.citta}'")
                logger.info(f"Saved Province: '{user_profile.provincia}'")

            except Exception as e:
                logger.error(f"Error creating/updating UserProfile: {e}")
                raise

        return user

class AnnuncioForm(forms.ModelForm):
    class Meta:
        model = Annuncio
        fields = ['titolo', 'descrizione', 'categoria', 'tipo', 'cerca_per_categoria', 'immagine',
                 'prezzo_stimato', 'metodo_scambio', 'distanza_massima_km']
        widgets = {
            'titolo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es: Chitarra elettrica Fender'}),
            'descrizione': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descrivi il tuo annuncio...'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'cerca_per_categoria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'immagine': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'onchange': 'previewImage(this);'
            }),
            'prezzo_stimato': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
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
            'immagine': 'Foto dell\'oggetto (opzionale)',
            'prezzo_stimato': 'Valore stimato (€)',
            'metodo_scambio': 'Come preferisci scambiare?',
            'distanza_massima_km': 'Distanza massima per incontro (km)'
        }

    def clean(self):
        """Validazione personalizzata del form"""
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        cerca_per_categoria = cleaned_data.get('cerca_per_categoria')
        titolo = cleaned_data.get('titolo')

        # Il flag cerca_per_categoria può essere usato SOLO su annunci "cerco"
        if cerca_per_categoria and tipo != 'cerco':
            raise forms.ValidationError(
                "L'opzione 'Cerca per categoria' è disponibile solo per annunci di tipo 'Cerco'."
            )

        # Se cerca_per_categoria è attivo, il titolo è opzionale
        # Altrimenti, il titolo è obbligatorio
        if not cerca_per_categoria and not titolo:
            self.add_error('titolo', 'Il titolo è obbligatorio.')

        return cleaned_data

class UserProfileForm(forms.ModelForm):
    # Definisci esplicitamente il campo citta_obj con queryset
    from .models import Citta
    citta_obj = forms.ModelChoiceField(
        queryset=Citta.objects.all().order_by('nome'),
        required=False,
        empty_label="Seleziona una città...",
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Città *',
        help_text='Seleziona la tua città. La provincia e regione verranno impostate automaticamente.'
    )

    class Meta:
        model = UserProfile
        fields = ['citta_obj', 'cap']
        widgets = {
            'cap': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: 00100, 20121...'
            }),
        }
        labels = {
            'cap': 'CAP (opzionale)'
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

    # Filtro per prezzo minimo
    prezzo_min = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        label='Prezzo min (€)'
    )

    # Filtro per prezzo massimo
    prezzo_max = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '999999.99',
            'step': '0.01'
        }),
        label='Prezzo max (€)'
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
        ('-data_creazione', 'Più recenti'),
        ('data_creazione', 'Meno recenti'),
        ('prezzo_stimato', 'Prezzo crescente'),
        ('-prezzo_stimato', 'Prezzo decrescente'),
        ('titolo', 'A-Z'),
        ('-titolo', 'Z-A'),
    ]

    ordinamento = forms.ChoiceField(
        choices=ORDINAMENTO_CHOICES,
        required=False,
        initial='-data_creazione',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Ordina per'
    )

    def clean(self):
        """Validazione del form"""
        cleaned_data = super().clean()
        prezzo_min = cleaned_data.get('prezzo_min')
        prezzo_max = cleaned_data.get('prezzo_max')

        # Verifica che il prezzo minimo non sia maggiore del massimo
        if prezzo_min and prezzo_max and prezzo_min > prezzo_max:
            raise forms.ValidationError(
                "Il prezzo minimo non può essere maggiore del prezzo massimo."
            )

        return cleaned_data


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
