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
        user = super().save(commit=commit)
        if commit:
            # Disabilita l'utente fino alla verifica email
            user.is_active = False
            user.save()

            # Crea il profilo utente con i dati geografici
            UserProfile.objects.create(
                user=user,
                citta=self.cleaned_data.get('citta', ''),
                provincia=self.cleaned_data.get('provincia', ''),
                email_verified=False
            )
        return user

class AnnuncioForm(forms.ModelForm):
    class Meta:
        model = Annuncio
        fields = ['titolo', 'descrizione', 'categoria', 'tipo', 'immagine',
                 'prezzo_stimato', 'metodo_scambio', 'distanza_massima_km']
        widgets = {
            'titolo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es: Chitarra elettrica Fender'}),
            'descrizione': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descrivi il tuo annuncio...'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
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
            'immagine': 'Foto dell\'oggetto (opzionale)',
            'prezzo_stimato': 'Valore stimato (€)',
            'metodo_scambio': 'Come preferisci scambiare?',
            'distanza_massima_km': 'Distanza massima per incontro (km)'
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['citta', 'provincia', 'regione', 'cap']
        widgets = {
            'citta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: Roma, Milano, Torino...'
            }),
            'provincia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: RM, MI, TO...'
            }),
            'regione': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: Lazio, Lombardia, Piemonte...'
            }),
            'cap': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Es: 00100, 20121...'
            }),
        }
        labels = {
            'citta': 'Città *',
            'provincia': 'Provincia',
            'regione': 'Regione',
            'cap': 'CAP'
        }
