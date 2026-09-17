"""
Signals per il sistema di notifiche Polygonum
"""
import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Annuncio, CalcoloMetadata

logger = logging.getLogger(__name__)


# Solo questi campi possono cambiare il grafo o i dettagli salvati delle
# catene. Modifiche puramente descrittive non devono avviare un calcolo
# costoso al passaggio successivo del cron.
MATCHING_RELEVANT_FIELDS = (
    'utente_id',
    'titolo',
    'categoria_id',
    'tipo',
    'cerca_per_categoria',
    'attivo',
    'disattivato_at',
    'pubblicato_at',
    'scaduto_at',
    'moderation_status',
)


@receiver(pre_save, sender=Annuncio)
def track_disattivazione_annuncio(sender, instance, **kwargs):
    """
    Signal per tracciare quando un annuncio viene disattivato/riattivato.
    Questo permette di includere annunci recentemente disattivati (<3 min)
    nel calcolo delle catene di scambio.
    """
    # Il post_save usa questo flag per evitare ricalcoli su descrizione,
    # immagine, prezzo e altri campi che non partecipano al matching.
    instance._cycle_recalculation_required = instance.pk is None

    if instance.pk:  # Solo se l'annuncio esiste già (non è nuovo)
        try:
            old = Annuncio.objects.only(*MATCHING_RELEVANT_FIELDS).get(
                pk=instance.pk
            )

            # Se sta cambiando da attivo a inattivo
            if old.attivo and not instance.attivo:
                # È stato disattivato ora
                instance.disattivato_at = timezone.now()
                logger.debug(f"📴 Annuncio ID:{instance.id} disattivato alle {instance.disattivato_at}")

            # Se sta cambiando da inattivo ad attivo
            elif not old.attivo and instance.attivo:
                # È stato riattivato, reset del timestamp
                instance.disattivato_at = None
                logger.debug(f"✅ Annuncio ID:{instance.id} riattivato")

            instance._cycle_recalculation_required = any(
                getattr(old, field_name) != getattr(instance, field_name)
                for field_name in MATCHING_RELEVANT_FIELDS
            )

        except Annuncio.DoesNotExist:
            # Caso edge: l'annuncio è stato cancellato nel frattempo
            pass


@receiver(post_save, sender=Annuncio)
def request_cycle_recalculation_after_save(
    sender,
    instance,
    created,
    **kwargs,
):
    """Richiede il ricalcolo solo dopo modifiche rilevanti per le catene."""
    if created or getattr(instance, '_cycle_recalculation_required', True):
        CalcoloMetadata.richiedi_ricalcolo()


@receiver(post_delete, sender=Annuncio)
def request_cycle_recalculation_after_delete(sender, instance, **kwargs):
    """Un annuncio eliminato può invalidare catene già salvate."""
    CalcoloMetadata.richiedi_ricalcolo()
