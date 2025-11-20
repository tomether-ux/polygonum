from django.contrib import admin
from .models import (
    Categoria, Annuncio, UserProfile, Notifica, Preferiti,
    PropostaScambio, CicloScambio, Provincia
)


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ['sigla', 'nome', 'regione', 'latitudine', 'longitudine']
    list_filter = ['regione']
    search_fields = ['nome', 'sigla']
    ordering = ['nome']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'descrizione']

@admin.register(Annuncio)
class AnnuncioAdmin(admin.ModelAdmin):
    list_display = ['titolo', 'utente', 'tipo', 'categoria', 'moderation_status', 'attivo', 'data_creazione']
    list_filter = ['tipo', 'categoria', 'attivo', 'moderation_status']
    search_fields = ['titolo', 'descrizione']
    actions = ['approve_annunci', 'reject_annunci', 'resend_moderation_email']

    @admin.action(description='✅ Approva annunci selezionati')
    def approve_annunci(self, request, queryset):
        """Approva manualmente gli annunci selezionati"""
        updated = 0
        for annuncio in queryset:
            if annuncio.moderation_status != 'approved':
                annuncio.moderation_status = 'approved'
                annuncio.attivo = True
                annuncio.save(update_fields=['moderation_status', 'attivo'])
                updated += 1

        self.message_user(
            request,
            f'{updated} annuncio/i approvato/i con successo.',
            level='success'
        )

    @admin.action(description='❌ Rifiuta annunci selezionati')
    def reject_annunci(self, request, queryset):
        """Rifiuta manualmente gli annunci selezionati"""
        updated = 0
        for annuncio in queryset:
            if annuncio.moderation_status != 'rejected':
                annuncio.moderation_status = 'rejected'
                annuncio.attivo = False
                annuncio.save(update_fields=['moderation_status', 'attivo'])
                updated += 1

        self.message_user(
            request,
            f'{updated} annuncio/i rifiutato/i con successo.',
            level='warning'
        )

    @admin.action(description='📧 Reinvia email di moderazione')
    def resend_moderation_email(self, request, queryset):
        """Reinvia le email di moderazione per gli annunci selezionati"""
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        from django.core.signing import Signer
        import os

        sent = 0
        for annuncio in queryset.filter(immagine__isnull=False).exclude(immagine=''):
            try:
                # Crea token firmato per link sicuri
                signer = Signer()
                approve_token = signer.sign(f'approve_{annuncio.id}')
                reject_token = signer.sign(f'reject_{annuncio.id}')

                # URL base
                base_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8000')

                # Link per approve/reject
                approve_url = f"{base_url}/moderazione/approve/{approve_token}/"
                reject_url = f"{base_url}/moderazione/reject/{reject_token}/"

                # Componi email
                subject = f'🔍 Moderazione richiesta - Annuncio #{annuncio.id}'

                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="margin: 0; font-size: 24px;">🔍 Moderazione Richiesta</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Annuncio #{annuncio.id}</p>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
        <h2 style="color: #667eea; margin-top: 0;">{annuncio.titolo}</h2>

        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <p style="margin: 5px 0;"><strong>👤 Utente:</strong> {annuncio.utente.username}</p>
            <p style="margin: 5px 0;"><strong>📁 Categoria:</strong> {annuncio.categoria.nome}</p>
            <p style="margin: 5px 0;"><strong>🏷️ Tipo:</strong> {annuncio.get_tipo_display()}</p>
            <p style="margin: 5px 0;"><strong>📅 Data:</strong> {annuncio.data_creazione.strftime('%d/%m/%Y %H:%M')}</p>
        </div>

        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: #667eea;">📝 Descrizione</h3>
            <p style="margin: 0;">{annuncio.descrizione}</p>
        </div>

        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 30px; text-align: center;">
            <h3 style="margin-top: 0; color: #667eea;">🖼️ Immagine</h3>
            <img src="{annuncio.get_image_url()}" alt="{annuncio.titolo}"
                 style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        </div>

        <div style="text-align: center; margin-top: 30px;">
            <a href="{approve_url}"
               style="display: inline-block; background: #10b981; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 0 10px 10px 0; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);">
                ✅ Approva
            </a>
            <a href="{reject_url}"
               style="display: inline-block; background: #ef4444; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 0 0 10px 0; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);">
                ❌ Rifiuta
            </a>
        </div>

        <p style="text-align: center; color: #666; font-size: 12px; margin-top: 30px;">
            Questa email è stata inviata automaticamente dal sistema di moderazione Polygonum
        </p>
    </div>
</body>
</html>
                """

                text_content = f"""
Nuovo annuncio da moderare

Annuncio: {annuncio.titolo}
Utente: {annuncio.utente.username}
Categoria: {annuncio.categoria.nome}
Tipo: {annuncio.get_tipo_display()}

Descrizione:
{annuncio.descrizione}

Immagine: {annuncio.get_image_url()}

---
Per approvare: {approve_url}
Per rifiutare: {reject_url}
                """

                # Invia email
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.ADMIN_MODERATION_EMAIL]
                )
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=False)
                sent += 1

            except Exception as e:
                self.message_user(
                    request,
                    f'Errore invio email per annuncio #{annuncio.id}: {e}',
                    level='error'
                )

        if sent > 0:
            self.message_user(
                request,
                f'{sent} email di moderazione inviate con successo.',
                level='success'
            )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_location_string', 'email_verified', 'is_premium']
    list_filter = ['provincia_obj', 'email_verified', 'is_premium']
    search_fields = ['user__username', 'citta', 'user__email', 'provincia_obj__nome']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'provincia_obj')


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
