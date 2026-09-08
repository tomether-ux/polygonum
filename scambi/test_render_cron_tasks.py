from contextlib import contextmanager
from datetime import timedelta
from io import StringIO
import subprocess
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from .background_tasks import (
    enqueue_moderation_email,
    process_moderation_email_jobs,
)
from .management.commands.calcola_cicli import Command as CycleCommand
from .management.commands.run_scheduled_tasks import Command as ScheduledCommand
from .management.commands.run_scheduled_tasks_guarded import (
    Command as GuardedScheduledCommand,
)
from .models import (
    Annuncio,
    CalcoloMetadata,
    Categoria,
    CicloScambio,
    ModerationEmailJob,
)


class ModerationQueueTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='utente-coda',
            email='utente-coda@example.invalid',
        )
        self.category = Categoria.objects.create(nome='Coda moderazione')
        self.announcement = Annuncio.objects.create(
            utente=self.user,
            titolo='Oggetto da controllare',
            descrizione='Descrizione valida',
            categoria=self.category,
            tipo='offro',
        )
        Annuncio.objects.filter(pk=self.announcement.pk).update(
            immagine='annunci/current-image.jpg',
            moderation_status='pending',
        )
        self.announcement.refresh_from_db()
        self.image_reference = str(self.announcement.immagine)

    def enqueue(self, *, image_reference=None, image_url='https://img.invalid/current.jpg'):
        return enqueue_moderation_email(
            self.announcement.pk,
            image_reference=image_reference or self.image_reference,
            image_url=image_url,
        )

    def test_enqueue_coalesces_repeated_requests_for_same_announcement(self):
        first = self.enqueue()
        first.status = ModerationEmailJob.STATUS_FAILED
        first.attempts = 5
        first.save(update_fields=['status', 'attempts', 'updated_at'])

        second = self.enqueue(image_url='https://img.invalid/new.jpg')

        self.assertEqual(ModerationEmailJob.objects.count(), 1)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.status, ModerationEmailJob.STATUS_PENDING)
        self.assertEqual(second.attempts, 0)
        self.assertEqual(second.image_url, 'https://img.invalid/new.jpg')

    def test_successful_processing_marks_job_as_sent(self):
        job = self.enqueue()

        with patch.object(
            Annuncio,
            '_perform_moderation_sync',
            return_value=True,
        ) as send_email:
            stats = process_moderation_email_jobs(max_jobs=10)

        job.refresh_from_db()
        self.assertEqual(stats['sent'], 1)
        self.assertEqual(job.status, ModerationEmailJob.STATUS_SENT)
        self.assertEqual(job.attempts, 1)
        self.assertIsNotNone(job.sent_at)
        send_email.assert_called_once_with(
            self.announcement.pk,
            self.image_reference,
            delay_seconds=0,
            image_url_override='https://img.invalid/current.jpg',
            validate_image=True,
            raise_on_error=True,
        )

    def test_failed_processing_retries_then_stops_at_limit(self):
        job = self.enqueue()

        with patch.object(
            Annuncio,
            '_perform_moderation_sync',
            side_effect=RuntimeError('smtp private detail'),
        ):
            first_stats = process_moderation_email_jobs(
                max_jobs=1,
                max_attempts=2,
            )

        job.refresh_from_db()
        self.assertEqual(first_stats['retried'], 1)
        self.assertEqual(job.status, ModerationEmailJob.STATUS_PENDING)
        self.assertEqual(job.last_error_type, 'RuntimeError')
        self.assertGreater(job.next_attempt_at, timezone.now())

        ModerationEmailJob.objects.filter(pk=job.pk).update(
            next_attempt_at=timezone.now() - timedelta(seconds=1)
        )
        with patch.object(
            Annuncio,
            '_perform_moderation_sync',
            side_effect=RuntimeError('smtp private detail'),
        ):
            second_stats = process_moderation_email_jobs(
                max_jobs=1,
                max_attempts=2,
            )

        job.refresh_from_db()
        self.assertEqual(second_stats['failed'], 1)
        self.assertEqual(job.status, ModerationEmailJob.STATUS_FAILED)
        self.assertEqual(job.attempts, 2)

    def test_replaced_image_cancels_stale_job_without_sending(self):
        job = self.enqueue(image_reference='annunci/replaced-image.jpg')

        with patch.object(Annuncio, '_perform_moderation_sync') as send_email:
            stats = process_moderation_email_jobs(max_jobs=10)

        job.refresh_from_db()
        self.assertEqual(stats['cancelled'], 1)
        self.assertEqual(job.status, ModerationEmailJob.STATUS_CANCELLED)
        send_email.assert_not_called()

    @override_settings(MODERATION_QUEUE_ENABLED=True)
    def test_model_queues_only_after_transaction_commit(self):
        with (
            patch.object(
                self.announcement,
                'get_image_url',
                return_value='https://img.invalid/current.jpg',
            ),
            patch(
                'scambi.background_tasks.enqueue_moderation_email'
            ) as enqueue,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.announcement.trigger_moderation()

        enqueue.assert_called_once_with(
            self.announcement.pk,
            image_reference=self.image_reference,
            image_url='https://img.invalid/current.jpg',
        )


class ScheduledCommandTests(TestCase):
    @staticmethod
    @contextmanager
    def lock_result(acquired):
        yield acquired

    def command_options(self, **overrides):
        options = {
            'email_limit': 10,
            'email_max_attempts': 8,
            'cycle_interval_minutes': 30,
            'time_budget_seconds': 210,
            'skip_email': False,
            'skip_cycles': False,
            'force_cycles': False,
        }
        options.update(overrides)
        return options

    def test_recent_cycle_calculation_is_not_repeated(self):
        CalcoloMetadata.objects.create(
            singleton_id=1,
            ultimo_calcolo_completo=timezone.now(),
        )
        command = ScheduledCommand(stdout=StringIO(), stderr=StringIO())

        with (
            patch(
                'scambi.management.commands.run_scheduled_tasks.'
                'process_moderation_email_jobs',
                return_value={
                    'sent': 0,
                    'retried': 0,
                    'failed': 0,
                    'cancelled': 0,
                },
            ),
            patch(
                'scambi.management.commands.run_scheduled_tasks.call_command'
            ) as calculate,
        ):
            command.handle(**self.command_options())

        calculate.assert_not_called()

    def test_due_cycle_calculation_runs_under_existing_lock(self):
        CalcoloMetadata.objects.create(
            singleton_id=1,
            ultimo_calcolo_completo=timezone.now() - timedelta(hours=1),
        )
        command = ScheduledCommand(stdout=StringIO(), stderr=StringIO())

        with (
            patch(
                'scambi.management.commands.run_scheduled_tasks.'
                'process_moderation_email_jobs',
                return_value={
                    'sent': 0,
                    'retried': 0,
                    'failed': 0,
                    'cancelled': 0,
                },
            ),
            patch(
                'scambi.management.commands.run_scheduled_tasks.'
                'cycle_calculation_lock',
                return_value=self.lock_result(True),
            ),
            patch(
                'scambi.management.commands.run_scheduled_tasks.call_command'
            ) as calculate,
        ):
            command.handle(**self.command_options())

        self.assertEqual(calculate.call_args.args[0], 'calcola_cicli')
        self.assertFalse(calculate.call_args.kwargs['cleanup_old'])

    def test_invalid_limits_fail_before_any_work(self):
        command = ScheduledCommand(stdout=StringIO(), stderr=StringIO())
        with self.assertRaises(CommandError):
            command.handle(**self.command_options(email_limit=1000))


class SafeCycleReplacementTests(TestCase):
    def setUp(self):
        self.old_cycle = CicloScambio.objects.create(
            users=[1, 2],
            lunghezza=2,
            dettagli={'version': 'old'},
            valido=True,
            hash_ciclo='old-cycle',
        )
        self.command = CycleCommand(stdout=StringIO(), stderr=StringIO())

    def test_incomplete_save_keeps_previous_cycles_valid(self):
        malformed_cycle = {
            'hash_ciclo': 'broken-cycle',
            'lunghezza': 2,
            'dettagli': {},
        }

        with self.assertRaises(CommandError):
            self.command._salva_cicli_batch(
                [malformed_cycle],
                50,
                finalize_full=True,
            )

        self.old_cycle.refresh_from_db()
        self.assertTrue(self.old_cycle.valido)

    def test_successful_full_save_replaces_stale_generated_cycle(self):
        new_cycle = {
            'hash_ciclo': 'new-cycle',
            'users': [2, 3],
            'lunghezza': 2,
            'dettagli': {'version': 'new'},
        }

        self.command._salva_cicli_batch(
            [new_cycle],
            50,
            finalize_full=True,
        )

        self.assertFalse(
            CicloScambio.objects.filter(pk=self.old_cycle.pk).exists()
        )
        self.assertTrue(
            CicloScambio.objects.filter(
                hash_ciclo='new-cycle',
                valido=True,
            ).exists()
        )


class GuardedScheduledCommandTests(TestCase):
    def test_timeout_is_bounded_before_starting_child(self):
        command = GuardedScheduledCommand(stdout=StringIO(), stderr=StringIO())

        with (
            patch.dict(
                'os.environ',
                {'BACKGROUND_HARD_TIMEOUT_SECONDS': '9999'},
            ),
            patch('subprocess.run') as run,
            self.assertRaises(CommandError),
        ):
            command.handle()

        run.assert_not_called()

    def test_expired_child_is_reported_as_command_failure(self):
        command = GuardedScheduledCommand(stdout=StringIO(), stderr=StringIO())

        with (
            patch.dict(
                'os.environ',
                {'BACKGROUND_HARD_TIMEOUT_SECONDS': '120'},
            ),
            patch(
                'subprocess.run',
                side_effect=subprocess.TimeoutExpired('scheduled', 120),
            ),
            self.assertRaises(CommandError),
        ):
            command.handle()
