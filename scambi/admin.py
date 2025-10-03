from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Categoria, Annuncio, UserProfile, Notifica, Preferiti, PropostaScambio

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
    list_display = ['user', 'citta', 'provincia', 'email_verified', 'get_location_string']
    list_filter = ['provincia', 'citta', 'email_verified']
    search_fields = ['user__username', 'citta', 'provincia', 'user__email']
    readonly_fields = ['latitudine', 'longitudine']  # Per ora read-only, potremmo aggiungere geocoding in futuro

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Notifica)
class NotificaAdmin(admin.ModelAdmin):
    list_display = ['utente', 'tipo', 'titolo', 'letta', 'data_creazione']
    list_filter = ['tipo', 'letta', 'data_creazione']
    search_fields = ['utente__username', 'titolo', 'messaggio']
    readonly_fields = ['data_creazione']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('utente', 'annuncio_collegato', 'utente_collegato')


@admin.register(Preferiti)
class PreferitiAdmin(admin.ModelAdmin):
    list_display = ['utente', 'annuncio', 'data_aggiunta']
    list_filter = ['data_aggiunta']
    search_fields = ['utente__username', 'annuncio__titolo']
    readonly_fields = ['data_aggiunta']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('utente', 'annuncio')


@admin.register(PropostaScambio)
class PropostaScambioAdmin(admin.ModelAdmin):
    list_display = ['richiedente', 'destinatario', 'annuncio_offerto', 'annuncio_richiesto', 'stato', 'data_creazione']
    list_filter = ['stato', 'data_creazione']
    search_fields = ['richiedente__username', 'destinatario__username', 'annuncio_offerto__titolo', 'annuncio_richiesto__titolo']
    readonly_fields = ['data_creazione', 'data_risposta']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('richiedente', 'destinatario', 'annuncio_offerto', 'annuncio_richiesto')
