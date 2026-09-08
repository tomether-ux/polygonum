import io
from contextlib import redirect_stdout

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from scambio_sito.test_runner import PolygonumTestRunner

from .models import Annuncio, Categoria


class TestDiscoveryConfigurationTests(SimpleTestCase):
    def test_default_runner_is_limited_to_real_application_tests(self):
        self.assertEqual(
            settings.TEST_RUNNER,
            'scambio_sito.test_runner.PolygonumTestRunner',
        )
        runner = PolygonumTestRunner(verbosity=0)
        self.assertEqual(runner.default_test_labels, ('scambi',))


class RuntimeLoggingTests(TestCase):
    def test_announcement_save_does_not_write_to_process_stdout(self):
        user = User.objects.create_user(
            username='runtime_logging_user',
            email='runtime-logging@example.com',
            password='Password-sicura-2026!',
        )
        category = Categoria.objects.create(nome='Runtime logging')
        output = io.StringIO()

        with redirect_stdout(output):
            Annuncio.objects.create(
                utente=user,
                titolo='Oggetto senza rumore nei log',
                descrizione='Descrizione',
                categoria=category,
                tipo='offro',
            )

        self.assertEqual(output.getvalue(), '')
