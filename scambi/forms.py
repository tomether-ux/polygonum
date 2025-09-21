from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Annuncio, Categoria

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

class AnnuncioForm(forms.ModelForm):
    class Meta:
        model = Annuncio
        fields = ['titolo', 'descrizione', 'categoria', 'tipo', 'immagine']
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
        }
        labels = {
            'titolo': 'Titolo annuncio',
            'descrizione': 'Descrizione',
            'categoria': 'Categoria',
            'tipo': 'Tipo annuncio',
            'immagine': 'Foto dell\'oggetto (opzionale)'
        }
