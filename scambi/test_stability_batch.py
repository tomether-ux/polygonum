import sys
from contextlib import contextmanager
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import RequestFactory, SimpleTestCase, override_settings

from . import email_utils
from .locks import cycle_calculation_lock
from .management.commands.calcola_cicli import Command as CalculateCyclesCommand
from .views import webhook_calcola_cicli


class EmailTimeoutTests(SimpleTestCase):
    def test_smtp_connection_receives_requested_timeout(self):
        connection = MagicMock()

        with (
            patch('scambi.email_utils.get_connection', return_value=connection) as get_connection,
            patch('scambi.email_utils.send_mail', return_value=1) as send_mail,
        ):
            result = email_utils._send_mail_task(
                'Oggetto',
                'Corpo',
                'from@example.invalid',
                ['to@example.invalid'],
                17,
            )

        self.assertEqual(result, 1)
        get_connection.assert_called_once_with(timeout=17)
        self.assertIs(send_mail.call_args.kwargs['connection'], connection)

    @override_settings(
        SITE_URL='https://polygonum.io',
        DEFAULT_FROM_EMAIL='noreply@example.invalid',
    )
    def test_socket_timeout_returns_generic_timeout_result(self):
        request = SimpleNamespace(is_secure=lambda: True, get_host=lambda: 'polygonum.io')
        user = SimpleNamespace(id=123, username='utente', email='private@example.invalid')
        profile = SimpleNamespace(email_verification_token=None, save=lambda: None)

        with patch(
            'scambi.email_utils._send_mail_task',
            side_effect=TimeoutError('private network detail'),
        ):
            result = email_utils.send_verification_email_with_timeout(
                request,
                user,
                profile,
                timeout_seconds=5,
            )

        self.assertEqual(result['message'], 'timeout')
        self.assertEqual(result['error'], 'Email delivery timeout')
        self.assertNotIn('private network detail', str(result))


class CycleWebhookConcurrencyTests(SimpleTestCase):
    def request(self):
        return RequestFactory().post(
            '/webhook/calcola-cicli/',
            HTTP_AUTHORIZATION='Bearer expected-token',
        )

    @staticmethod
    @contextmanager
    def lock_result(acquired):
        yield acquired

    def test_second_cycle_calculation_is_rejected_without_running_command(self):
        with (
            patch.dict('os.environ', {'POLYGONUM_WEBHOOK_SECRET': 'expected-token'}),
            patch('scambi.locks.cycle_calculation_lock', return_value=self.lock_result(False)),
            patch('django.core.management.call_command') as call_command,
        ):
            response = webhook_calcola_cicli(self.request())

        self.assertEqual(response.status_code, 409)
        call_command.assert_not_called()

    def test_command_output_is_captured_without_replacing_global_stdout(self):
        original_stdout = sys.stdout

        def fake_call_command(*args, **kwargs):
            kwargs['stdout'].write('calcolo completato')

        with (
            patch.dict('os.environ', {'POLYGONUM_WEBHOOK_SECRET': 'expected-token'}),
            patch('scambi.locks.cycle_calculation_lock', return_value=self.lock_result(True)),
            patch('django.core.management.call_command', side_effect=fake_call_command) as call_command,
            patch('scambi.models.CicloScambio.objects.count', return_value=2),
            patch('scambi.models.CicloScambio.objects.filter') as filter_cycles,
        ):
            filter_cycles.return_value.count.return_value = 2
            response = webhook_calcola_cicli(self.request())

        self.assertEqual(response.status_code, 200)
        self.assertIs(sys.stdout, original_stdout)
        kwargs = call_command.call_args.kwargs
        self.assertIsInstance(kwargs['stdout'], StringIO)
        self.assertIs(kwargs['stdout'], kwargs['stderr'])

    def test_local_lock_is_released_after_use(self):
        with cycle_calculation_lock() as first_acquired:
            with cycle_calculation_lock() as second_acquired:
                self.assertTrue(first_acquired)
                self.assertFalse(second_acquired)

        with cycle_calculation_lock() as acquired_after_release:
            self.assertTrue(acquired_after_release)


class CycleCommandFailureTests(SimpleTestCase):
    def test_command_raises_command_error_instead_of_system_exit(self):
        command = CalculateCyclesCommand(stdout=StringIO(), stderr=StringIO())

        with (
            patch('scambi.models.CicloScambio.cleanup_old', side_effect=RuntimeError('db detail')),
            patch('scambi.management.commands.calcola_cicli.logger.exception'),
            self.assertRaises(CommandError),
        ):
            command.handle(
                max_length=6,
                commit_batch_size=50,
                cleanup_old=True,
                incremental=False,
                force_full=False,
            )
