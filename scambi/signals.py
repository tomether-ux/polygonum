"""
Signals per il sistema di notifiche Polygonum
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
from .notifications import notifica_benvenuto


@receiver(post_save, sender=User)
def crea_profilo_utente_e_benvenuto(sender, instance, created, **kwargs):
    """
    Signal che si attiva quando un nuovo utente viene creato.
    Crea automaticamente un UserProfile e invia il messaggio di benvenuto.
    """
    if created:
        # Crea il profilo utente se non esiste
        UserProfile.objects.get_or_create(user=instance)

        # Invia notifica di benvenuto
        notifica_benvenuto(instance)