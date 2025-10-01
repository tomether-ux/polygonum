from django.urls import path
from . import views
from .views import register, CustomLoginView, verify_email, profilo_utente, modifica_profilo, custom_logout, mie_catene_scambio

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
    path('mie-catene-scambio/', mie_catene_scambio, name='mie_catene_scambio'),
    path('test-matching/', views.test_matching, name='test_matching'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('verify-email/<str:token>/', verify_email, name='verify_email'),
    path('profilo/<str:username>/', profilo_utente, name='profilo_utente'),
    path('modifica-profilo/', modifica_profilo, name='modifica_profilo'),
]
