from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Categoria, Annuncio, UserProfile

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'descrizione']

@admin.register(Annuncio)
class AnnuncioAdmin(admin.ModelAdmin):
    list_display = ['titolo', 'utente', 'tipo', 'categoria', 'attivo', 'data_creazione']
    list_filter = ['tipo', 'categoria', 'attivo']
    search_fields = ['titolo', 'descrizione']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'citta', 'provincia', 'get_location_string']
    list_filter = ['provincia', 'citta']
    search_fields = ['user__username', 'citta', 'provincia']
    readonly_fields = ['latitudine', 'longitudine']  # Per ora read-only, potremmo aggiungere geocoding in futuro
