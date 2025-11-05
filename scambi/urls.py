from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import register, CustomLoginView, verify_email, profilo_utente, modifica_profilo, custom_logout

urlpatterns = [
    path('', views.home, name='home'),
    path('annunci/', views.lista_annunci, name='lista_annunci'),
    path('annuncio/<int:annuncio_id>/', views.dettaglio_annuncio, name='dettaglio_annuncio'),
    path('crea-annuncio/', views.crea_annuncio, name='crea_annuncio'),
    path('modifica-annuncio/<int:annuncio_id>/', views.modifica_annuncio, name='modifica_annuncio'),
    path('elimina-annuncio/<int:annuncio_id>/', views.elimina_annuncio, name='elimina_annuncio'),
    path('attiva-annuncio/<int:annuncio_id>/', views.attiva_annuncio, name='attiva_annuncio'),
    path('disattiva-annuncio/<int:annuncio_id>/', views.disattiva_annuncio, name='disattiva_annuncio'),
    path('catene-scambio/', views.catene_scambio, name='catene_scambio'),
    path('test-matching/', views.test_matching, name='test_matching'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('verify-email/<str:token>/', verify_email, name='verify_email'),

    # Password reset URLs
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    path('profilo/<str:username>/', profilo_utente, name='profilo_utente'),
    path('modifica-profilo/', modifica_profilo, name='modifica_profilo'),

    # Sistema notifiche e preferiti
    path('preferiti/', views.lista_preferiti, name='lista_preferiti'),
    path('preferiti/aggiungi/<int:annuncio_id>/', views.aggiungi_preferito, name='aggiungi_preferito'),
    path('catene/aggiungi-preferita/', views.aggiungi_catena_preferita, name='aggiungi_catena_preferita'),
    path('notifiche/', views.lista_notifiche, name='lista_notifiche'),
    path('notifiche/<int:notifica_id>/letta/', views.segna_notifica_letta, name='segna_notifica_letta'),
    path('notifiche/<int:notifica_id>/click/', views.notifica_click_redirect, name='notifica_click_redirect'),
    path('notifiche/tutte-lette/', views.segna_tutte_notifiche_lette, name='segna_tutte_notifiche_lette'),

    # Sistema proposte di scambio
    path('proposte-scambio/', views.lista_proposte_scambio, name='lista_proposte_scambio'),
    path('proposte-scambio/<int:proposta_id>/', views.dettaglio_proposta_scambio, name='dettaglio_proposta_scambio'),
    path('proposte-scambio/crea/<int:annuncio_offerto_id>/<int:annuncio_richiesto_id>/', views.crea_proposta_scambio, name='crea_proposta_scambio'),
    path('proposte-scambio/<int:proposta_id>/rispondi/', views.rispondi_proposta_scambio, name='rispondi_proposta_scambio'),

    # Sistema di ricerca
    path('cerca/', views.ricerca_annunci, name='ricerca_annunci'),
    path('ricerca-veloce/', views.ricerca_veloce, name='ricerca_veloce'),

    # Sistema messaggistica
    path('messaggi/', views.lista_messaggi, name='lista_messaggi'),
    path('messaggi/<int:conversazione_id>/', views.chat_conversazione, name='chat_conversazione'),
    path('messaggi/verifica-conversazione/<int:user_id>/', views.verifica_conversazione_esistente, name='verifica_conversazione_esistente'),
    path('messaggi/invia-da-annuncio/', views.invia_messaggio_da_annuncio, name='invia_messaggio_da_annuncio'),
    path('inizia-conversazione/<str:username>/', views.inizia_conversazione, name='inizia_conversazione'),

    # Sistema catene di scambio attivabili
    path('catene-attivabili/', views.lista_catene_attivabili, name='lista_catene_attivabili'),
    path('catena/<str:catena_id>/', views.dettaglio_catena, name='dettaglio_catena'),
    path('catena/<str:catena_id>/attiva/', views.attiva_catena, name='attiva_catena'),

    # Le mie catene personali
    path('le-mie-catene/', views.le_mie_catene, name='le_mie_catene'),

    # Sistema proposte catene (MVP)
    path('catene/proponi/<int:ciclo_id>/', views.proponi_catena, name='proponi_catena'),
    path('catene/rispondi/<int:proposta_id>/', views.rispondi_proposta_catena, name='rispondi_proposta_catena'),
    path('catene/stato/<int:ciclo_id>/', views.stato_proposta_catena, name='stato_proposta_catena'),
    path('mie-proposte-catene/', views.mie_proposte_catene, name='mie_proposte_catene'),

    # API Sistema calcolo cicli separato
    path('api/cicli/<int:user_id>/', views.api_cicli_utente, name='api_cicli_utente'),
    path('api/cicli/stats/', views.api_cicli_stats, name='api_cicli_stats'),

    # Webhook per calcolo cicli (alternativa gratuita al cron job)
    path('webhook/calcola-cicli/', views.webhook_calcola_cicli, name='webhook_calcola_cicli'),

    # Debug views (TEMPORANEE - RIMUOVERE)
    path('debug/basso/', views.debug_basso, name='debug_basso'),
    path('debug/view-catene/', views.debug_view_catene, name='debug_view_catene'),
    path('debug/cyclefinder-basso/', views.debug_cyclefinder_basso, name='debug_cyclefinder_basso'),

    # Sistema Premium
    path('pricing/', views.pricing, name='pricing'),
    path('premium/checkout/', views.premium_checkout, name='premium_checkout'),
    path('premium/success/', views.premium_success, name='premium_success'),
    path('premium/cancel/', views.premium_cancel, name='premium_cancel'),
]
