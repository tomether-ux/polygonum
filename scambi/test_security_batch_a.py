import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.test import RequestFactory, SimpleTestCase, override_settings

from . import email_utils
from .management.commands import create_superuser, setup
from .models import Annuncio
from .validators import valida_contenuto_testuale
from .views import webhook_calcola_cicli


class SuperuserCommandSafetyTests(SimpleTestCase):
    def test_create_superuser_requires_explicit_environment(self):
        command = create_superuser.Command()
        with patch.object(create_superuser.os.environ, 'get', return_value=None):
            with self.assertRaises(CommandError):
                command.handle()

    def test_setup_skips_when_superuser_environment_is_absent(self):
        command = setup.Command()
        with (
            patch.object(setup.os.environ, 'get', return_value=None),
            patch.object(setup.User.objects, 'filter') as filter_users,
        ):
            command.handle()

        filter_users.assert_not_called()

    def test_setup_rejects_partial_superuser_environment(self):
        command = setup.Command()

        def get_environment(name):
            if name == 'DJANGO_SUPERUSER_USERNAME':
                return 'configured-admin'
            return None

        with patch.object(setup.os.environ, 'get', side_effect=get_environment):
            with self.assertRaises(CommandError):
                command.handle()


class SensitiveDataLoggingTests(SimpleTestCase):
    def test_validator_does_not_log_submitted_content(self):
        submitted_content = 'cocaina riferimento-privato-12345'

        with self.assertLogs('scambi.validators', level='INFO') as captured:
            with self.assertRaises(ValidationError):
                valida_contenuto_testuale(submitted_content, campo_nome='descrizione')

        self.assertNotIn(submitted_content, '\n'.join(captured.output))

    @override_settings(
        SITE_URL='https://polygonum.io',
        DEFAULT_FROM_EMAIL='noreply@example.invalid',
    )
    def test_email_error_returned_to_caller_is_generic(self):
        request = SimpleNamespace(is_secure=lambda: True, get_host=lambda: 'polygonum.io')
        user = SimpleNamespace(id=123, username='utente', email='private@example.invalid')
        profile = SimpleNamespace(
            email_verification_token=None,
            save=lambda: None,
        )

        with patch(
            'scambi.email_utils._send_mail_task',
            side_effect=RuntimeError('smtp-internal-detail'),
        ):
            result = email_utils.send_verification_email_with_timeout(
                request,
                user,
                profile,
                timeout_seconds=1,
            )

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Email delivery failed')
        self.assertNotIn('smtp-internal-detail', result['error'])


class ModerationEmailEscapingTests(SimpleTestCase):
    @override_settings(
        ADMIN_MODERATION_EMAIL='moderation@example.invalid',
        DEFAULT_FROM_EMAIL='noreply@example.invalid',
    )
    def test_user_content_is_escaped_in_html_email(self):
        email = MagicMock()
        annuncio = SimpleNamespace(
            id=42,
            titolo='<img src=x onerror=alert(1)>',
            descrizione='</p><a href="https://evil.invalid">click</a>',
            utente=SimpleNamespace(username='<b>admin</b>'),
            categoria=SimpleNamespace(nome='<script>bad</script>'),
            data_creazione=datetime(2026, 1, 1, 12, 0),
            get_tipo_display=lambda: 'Offro',
            get_image_url=lambda: 'https://example.invalid/image.jpg" onerror="alert(1)',
        )

        with (
            patch('scambi.models.Annuncio.objects.get', return_value=annuncio),
            patch('django.core.mail.EmailMultiAlternatives', return_value=email),
            patch('time.sleep'),
            patch.dict(os.environ, {'RENDER_EXTERNAL_URL': 'https://polygonum.io'}),
        ):
            Annuncio._perform_moderation_sync(annuncio.id, 'unused-public-id')

        html_content, mime_type = email.attach_alternative.call_args.args
        self.assertEqual(mime_type, 'text/html')
        self.assertNotIn('<script>bad</script>', html_content)
        self.assertNotIn('<b>admin</b>', html_content)
        self.assertNotIn('<img src=x onerror=alert(1)>', html_content)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;', html_content)
        self.assertIn('&lt;b&gt;admin&lt;/b&gt;', html_content)
        self.assertIn('&quot; onerror=&quot;alert(1)', html_content)


class WebhookSecretComparisonTests(SimpleTestCase):
    def test_cycle_webhook_rejects_invalid_bearer_token(self):
        request = RequestFactory().post(
            '/webhook/calcola-cicli/',
            HTTP_AUTHORIZATION='Bearer wrong-token',
        )

        with patch.dict(os.environ, {'POLYGONUM_WEBHOOK_SECRET': 'expected-token'}):
            response = webhook_calcola_cicli(request)

        self.assertEqual(response.status_code, 401)
