from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import register, CustomLoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('annunci/', views.lista_annunci, name='lista_annunci'),
    path('crea-annuncio/', views.crea_annuncio, name='crea_annuncio'),
    path('i-miei-annunci/', views.i_miei_annunci, name='i_miei_annunci'),
    path('catene-scambio/', views.catene_scambio, name='catene_scambio'),
    path('test-matching/', views.test_matching, name='test_matching'),
    path('register/', register, name='register'),  # aggiungi questi
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
]
