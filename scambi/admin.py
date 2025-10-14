from django.contrib import admin
from .models import (
    Categoria, Annuncio, UserProfile, Notifica, Preferiti,
    PropostaScambio, CicloScambio, Citta, DistanzaCitta
)


@admin.register(Citta)
class CittaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'provincia', 'regione']
    list_filter = ['regione', 'provincia']
    search_fields = ['nome', 'provincia']
    ordering = ['nome']


@admin.register(DistanzaCitta)
class DistanzaCittaAdmin(admin.ModelAdmin):
    list_display = ['citta_a', 'citta_b', 'distanza_km']
    list_filter = ['citta_a', 'citta_b']
    search_fields = ['citta_a__nome', 'citta_b__nome']


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
    list_display = ['user', 'citta', 'get_location_string', 'email_verified']
    list_filter = ['citta_obj', 'email_verified']
    search_fields = ['user__username', 'citta_obj__nome', 'user__email']
    readonly_fields = ['latitudine', 'longitudine', 'citta_old', 'provincia', 'regione']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'citta_obj')


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


@admin.register(CicloScambio)
class CicloScambioAdmin(admin.ModelAdmin):
    list_display = ['id', 'lunghezza', 'valido', 'calcolato_at', 'get_users_display']
    list_filter = ['lunghezza', 'valido', 'calcolato_at']
    search_fields = ['hash_ciclo']
    readonly_fields = ['hash_ciclo', 'calcolato_at']
    ordering = ['-calcolato_at']

    def get_users_display(self, obj):
        """Mostra gli ID degli utenti nel ciclo"""
        return f"Utenti: {obj.users}"
    get_users_display.short_description = 'Utenti nel ciclo'
