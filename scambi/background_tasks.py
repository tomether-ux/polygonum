"""Attività brevi e persistenti eseguite dal cron di Polygonum."""

import logging
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .models import Annuncio, ModerationEmailJob


logger = logging.getLogger(__name__)


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
