import os
import time
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from scambi.background_tasks import (
    expire_announcements,
    process_moderation_email_jobs,
)
from scambi.locks import cycle_calculation_lock
from scambi.models import CalcoloMetadata


def _environment_integer(name, default):
    raw_value = os.environ.get(name, str(default))
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise CommandError(f'{name} deve essere un numero intero') from exc


def _bounded(value, *, name, minimum, maximum):
    if not minimum <= value <= maximum:
        raise CommandError(
            f'{name} deve essere compreso tra {minimum} e {maximum}'
        )
    return value


class Command(BaseCommand):
    help = 'Esegue attività periodiche con limiti adatti al cron Render'

    def add_arguments(self, parser):
        parser.add_argument(
            '--expiration-limit',
            type=int,
            default=_environment_integer('BACKGROUND_EXPIRATION_LIMIT', 500),
        )
        parser.add_argument(
            '--email-limit',
            type=int,
            default=_environment_integer('BACKGROUND_EMAIL_LIMIT', 10),
        )
        parser.add_argument(
            '--email-max-attempts',
            type=int,
            default=_environment_integer('BACKGROUND_EMAIL_MAX_ATTEMPTS', 8),
        )
        parser.add_argument(
            '--cycle-interval-minutes',
            type=int,
            default=_environment_integer('BACKGROUND_CYCLE_INTERVAL_MINUTES', 30),
        )
        parser.add_argument(
            '--time-budget-seconds',
            type=int,
            default=_environment_integer('BACKGROUND_TIME_BUDGET_SECONDS', 210),
        )
        parser.add_argument('--skip-email', action='store_true')
        parser.add_argument('--skip-expiration', action='store_true')
        parser.add_argument('--skip-cycles', action='store_true')
        parser.add_argument('--force-cycles', action='store_true')

    @staticmethod
    def _cycles_are_due(interval_minutes):
        metadata = CalcoloMetadata.objects.filter(
            singleton_id=1
        ).values(
            'ultimo_calcolo_completo',
            'ricalcolo_richiesto_at',
        ).first()
        if metadata is None:
            return True

        last_calculation = metadata['ultimo_calcolo_completo']
        recalculation_requested = metadata['ricalcolo_richiesto_at']
        if (
            recalculation_requested is not None
            and recalculation_requested > last_calculation
        ):
            return True

        return last_calculation <= (
            timezone.now() - timedelta(minutes=interval_minutes)
        )

    def handle(self, *args, **options):
        expiration_limit = _bounded(
            options['expiration_limit'],
            name='expiration-limit',
            minimum=1,
            maximum=5000,
        )
        email_limit = _bounded(
            options['email_limit'],
            name='email-limit',
            minimum=1,
            maximum=50,
        )
        email_max_attempts = _bounded(
            options['email_max_attempts'],
            name='email-max-attempts',
            minimum=1,
            maximum=20,
        )
        cycle_interval = _bounded(
            options['cycle_interval_minutes'],
            name='cycle-interval-minutes',
            minimum=15,
            maximum=1440,
        )
        time_budget = _bounded(
            options['time_budget_seconds'],
            name='time-budget-seconds',
            minimum=30,
            maximum=225,
        )

        started_at = time.monotonic()
        if not options['skip_expiration']:
            expiration_stats = expire_announcements(
                max_announcements=expiration_limit,
            )
            self.stdout.write(
                'Scadenza annunci: '
                f"sospesi={expiration_stats['expired_active']} "
                f"già_inattivi={expiration_stats['marked_inactive']} "
                f"notifiche={expiration_stats['notified']}"
            )

        email_stats = {'sent': 0, 'retried': 0, 'failed': 0, 'cancelled': 0}

        if not options['skip_email']:
            email_stats = process_moderation_email_jobs(
                max_jobs=email_limit,
                max_attempts=email_max_attempts,
            )
            self.stdout.write(
                'Moderazione email: '
                f"inviate={email_stats['sent']} "
                f"retry={email_stats['retried']} "
                f"fallite={email_stats['failed']} "
                f"annullate={email_stats['cancelled']}"
            )

        cycle_executed = False
        if not options['skip_cycles']:
            cycle_due = options['force_cycles'] or self._cycles_are_due(
                cycle_interval
            )
            elapsed = time.monotonic() - started_at
            if cycle_due and elapsed >= time_budget:
                self.stdout.write(
                    self.style.WARNING(
                        'Calcolo cicli rinviato: budget temporale già esaurito'
                    )
                )
            elif cycle_due:
                with cycle_calculation_lock() as lock_acquired:
                    # Ricontrolla dopo il lock: un'altra esecuzione del Cron
                    # potrebbe avere completato il calcolo nel frattempo.
                    still_due = (
                        options['force_cycles']
                        or self._cycles_are_due(cycle_interval)
                    )
                    if lock_acquired and still_due:
                        call_command(
                            'calcola_cicli',
                            max_length=6,
                            commit_batch_size=50,
                            cleanup_old=False,
                            verbosity=1,
                            stdout=self.stdout,
                            stderr=self.stderr,
                        )
                        cycle_executed = True
                    elif not lock_acquired:
                        self.stdout.write(
                            self.style.WARNING(
                                'Calcolo cicli saltato: già in esecuzione'
                            )
                        )

        elapsed = time.monotonic() - started_at
        self.stdout.write(
            self.style.SUCCESS(
                f'Attività pianificate completate in {elapsed:.1f}s; '
                f'calcolo_cicli={"eseguito" if cycle_executed else "non necessario"}'
            )
        )

        if email_stats['retried'] or email_stats['failed']:
            raise CommandError(
                'Una o più email di moderazione richiedono un nuovo tentativo'
            )
