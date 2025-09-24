from django.urls import path
from . import views
from .views import register, CustomLoginView, verify_email, profilo_utente, modifica_profilo, custom_logout

urlpatterns = [
    path('', views.home, name='home'),
    path('annunci/', views.lista_annunci, name='lista_annunci'),
    path('crea-annuncio/', views.crea_annuncio, name='crea_annuncio'),
    path('i-miei-annunci/', views.i_miei_annunci, name='i_miei_annunci'),
    path('catene-scambio/', views.catene_scambio, name='catene_scambio'),
    path('test-matching/', views.test_matching, name='test_matching'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('verify-email/<str:token>/', verify_email, name='verify_email'),
    path('profilo/<str:username>/', profilo_utente, name='profilo_utente'),
    path('modifica-profilo/', modifica_profilo, name='modifica_profilo'),
]
