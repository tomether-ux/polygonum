"""
Signals per il sistema di notifiche Polygonum
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile, Annuncio
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


@receiver(pre_save, sender=Annuncio)
def track_disattivazione_annuncio(sender, instance, **kwargs):
    """
    Signal per tracciare quando un annuncio viene disattivato/riattivato.
    Questo permette di includere annunci recentemente disattivati (<3 min)
    nel calcolo delle catene di scambio.
    """
    if instance.pk:  # Solo se l'annuncio esiste già (non è nuovo)
        try:
            old = Annuncio.objects.get(pk=instance.pk)

            # Se sta cambiando da attivo a inattivo
            if old.attivo and not instance.attivo:
                # È stato disattivato ora
                instance.disattivato_at = timezone.now()
                print(f"📴 Annuncio '{instance.titolo}' (ID:{instance.id}) disattivato alle {instance.disattivato_at}")

            # Se sta cambiando da inattivo ad attivo
            elif not old.attivo and instance.attivo:
                # È stato riattivato, reset del timestamp
                instance.disattivato_at = None
                print(f"✅ Annuncio '{instance.titolo}' (ID:{instance.id}) riattivato")

        except Annuncio.DoesNotExist:
            # Caso edge: l'annuncio è stato cancellato nel frattempo
            pass