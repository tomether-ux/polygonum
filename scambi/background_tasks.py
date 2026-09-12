"""Attività brevi e persistenti eseguite dal cron di Polygonum."""

import logging
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .models import Annuncio, CalcoloMetadata, ModerationEmailJob, Notifica


logger = logging.getLogger(__name__)


def expire_announcements(*, max_announcements=500, now=None):
    """Sospende in modo idempotente un lotto di annunci vecchi di 60 giorni."""
    now = now or timezone.now()
    cutoff = Annuncio.cutoff_scadenza(now)
    with transaction.atomic():
        candidates = list(
            Annuncio.objects.filter(
                pubblicato_at__lte=cutoff,
                scaduto_at__isnull=True,
            )
            .order_by('pubblicato_at', 'pk')
            .values('pk', 'utente_id', 'titolo', 'attivo')[:max_announcements]
        )
        if not candidates:
            return {'expired_active': 0, 'marked_inactive': 0, 'notified': 0}

        candidate_ids = [candidate['pk'] for candidate in candidates]
        still_expired = Annuncio.objects.filter(
            pk__in=candidate_ids,
            pubblicato_at__lte=cutoff,
            scaduto_at__isnull=True,
        )
        expired_active = still_expired.filter(attivo=True).update(
            attivo=False,
            scaduto_at=now,
            disattivato_at=now,
        )
        marked_inactive = still_expired.filter(attivo=False).update(
            scaduto_at=now,
        )

        expired_ids = set(
            Annuncio.objects.filter(
                pk__in=candidate_ids,
                scaduto_at=now,
            ).values_list('pk', flat=True)
        )
        notifications = [
            Notifica(
                utente_id=candidate['utente_id'],
                tipo='sistema',
                titolo='Annuncio scaduto',
                messaggio=(
                    f'L\'annuncio "{candidate["titolo"]}" ha raggiunto i 60 '
                    'giorni ed è stato sospeso. Puoi ripubblicarlo per altri '
                    '60 giorni.'
                ),
                annuncio_collegato_id=candidate['pk'],
                url_azione='/miei-annunci/?stato=disattivati',
            )
            for candidate in candidates
            if candidate['pk'] in expired_ids
        ]
        Notifica.objects.bulk_create(notifications)

        if expired_active:
            CalcoloMetadata.richiedi_ricalcolo()

    return {
        'expired_active': expired_active,
        'marked_inactive': marked_inactive,
        'notified': len(notifications),
    }


def enqueue_moderation_email(annuncio_id, *, image_reference, image_url):
    """Crea o aggiorna un solo lavoro per l'immagine corrente dell'annuncio."""
    now = timezone.now()
    job, _ = ModerationEmailJob.objects.update_or_create(
        annuncio_id=annuncio_id,
        defaults={
            'image_reference': image_reference,
            'image_url': image_url,
            'status': ModerationEmailJob.STATUS_PENDING,
            'attempts': 0,
            'next_attempt_at': now,
            'locked_at': None,
            'sent_at': None,
            'last_error_type': '',
        },
    )
    return job


def _claim_next_moderation_job(*, max_attempts, stale_after_minutes):
    """Prenota atomicamente un lavoro pronto, recuperando lock abbandonati."""
    now = timezone.now()
    stale_before = now - timedelta(minutes=stale_after_minutes)
    eligible = (
        Q(
            status=ModerationEmailJob.STATUS_PENDING,
            next_attempt_at__lte=now,
        )
        | Q(
            status=ModerationEmailJob.STATUS_PROCESSING,
            locked_at__lt=stale_before,
        )
    )

    with transaction.atomic():
        queryset = ModerationEmailJob.objects.filter(eligible).select_related(
            'annuncio'
        )
        if connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        else:
            queryset = queryset.select_for_update()

        job = queryset.order_by('next_attempt_at', 'created_at').first()
        if job is None:
            return None

        annuncio = job.annuncio
        current_image = str(annuncio.immagine or '')
        if (
            annuncio.moderation_status != 'pending'
            or not current_image
            or current_image != job.image_reference
        ):
            job.status = ModerationEmailJob.STATUS_CANCELLED
            job.locked_at = None
            job.last_error_type = ''
            job.save(
                update_fields=[
                    'status',
                    'locked_at',
                    'last_error_type',
                    'updated_at',
                ]
            )
            return {'job': job, 'cancelled': True}

        if job.attempts >= max_attempts:
            job.status = ModerationEmailJob.STATUS_FAILED
            job.locked_at = None
            job.save(update_fields=['status', 'locked_at', 'updated_at'])
            return {'job': job, 'failed': True}

        job.status = ModerationEmailJob.STATUS_PROCESSING
        job.attempts += 1
        job.locked_at = now
        job.save(
            update_fields=['status', 'attempts', 'locked_at', 'updated_at']
        )
        return {
            'job': job,
            'cancelled': False,
            'failed': False,
            'image_reference': job.image_reference,
            'image_url': job.image_url,
        }


def process_moderation_email_jobs(
    *,
    max_jobs=10,
    max_attempts=8,
    stale_after_minutes=15,
):
    """Invia un numero limitato di email e pianifica retry esponenziali."""
    stats = {'sent': 0, 'retried': 0, 'failed': 0, 'cancelled': 0}

    for _ in range(max_jobs):
        claimed = _claim_next_moderation_job(
            max_attempts=max_attempts,
            stale_after_minutes=stale_after_minutes,
        )
        if claimed is None:
            break
        if claimed.get('cancelled'):
            stats['cancelled'] += 1
            continue
        if claimed.get('failed'):
            stats['failed'] += 1
            continue

        job = claimed['job']
        image_reference = claimed['image_reference']

        try:
            sent = Annuncio._perform_moderation_sync(
                job.annuncio_id,
                image_reference,
                delay_seconds=0,
                image_url_override=claimed['image_url'],
                validate_image=True,
                raise_on_error=True,
            )
            if not sent:
                ModerationEmailJob.objects.filter(
                    pk=job.pk,
                    status=ModerationEmailJob.STATUS_PROCESSING,
                    image_reference=image_reference,
                ).update(
                    status=ModerationEmailJob.STATUS_CANCELLED,
                    locked_at=None,
                    updated_at=timezone.now(),
                )
                stats['cancelled'] += 1
                continue

            now = timezone.now()
            updated = ModerationEmailJob.objects.filter(
                pk=job.pk,
                status=ModerationEmailJob.STATUS_PROCESSING,
                image_reference=image_reference,
            ).update(
                status=ModerationEmailJob.STATUS_SENT,
                sent_at=now,
                locked_at=None,
                last_error_type='',
                updated_at=now,
            )
            if updated:
                stats['sent'] += 1
        except Exception as exc:
            # Conserva soltanto il tipo di errore: messaggi SMTP possono
            # contenere dettagli infrastrutturali che non servono in tabella.
            error_type = type(exc).__name__[:100]
            terminal_failure = job.attempts >= max_attempts
            retry_minutes = min(5 * (2 ** max(job.attempts - 1, 0)), 1440)
            now = timezone.now()
            updated = ModerationEmailJob.objects.filter(
                pk=job.pk,
                status=ModerationEmailJob.STATUS_PROCESSING,
                image_reference=image_reference,
            ).update(
                status=(
                    ModerationEmailJob.STATUS_FAILED
                    if terminal_failure
                    else ModerationEmailJob.STATUS_PENDING
                ),
                next_attempt_at=now + timedelta(minutes=retry_minutes),
                locked_at=None,
                last_error_type=error_type,
                updated_at=now,
            )
            if updated:
                key = 'failed' if terminal_failure else 'retried'
                stats[key] += 1
            logger.error(
                "Queued moderation email failed annuncio_id=%s "
                "attempt=%s error_type=%s",
                job.annuncio_id,
                job.attempts,
                error_type,
            )

    return stats
