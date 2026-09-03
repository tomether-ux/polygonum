from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Provincia, UserProfile


class AccountAccessTests(TestCase):
    def setUp(self):
        self.provincia = Provincia.objects.create(
            sigla='MI',
            nome='Milano',
            regione='Lombardia',
            latitudine=45.4642,
            longitudine=9.1900,
        )

    def create_account(self, username, **profile_values):
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='Password-sicura-2026!',
        )
        UserProfile.objects.create(
            user=user,
            provincia_obj=self.provincia,
            citta='Milano',
            **profile_values,
        )
        return user

    def test_only_restriction_aware_backend_is_configured(self):
        self.assertEqual(
            settings.AUTHENTICATION_BACKENDS,
            ['scambi.backends.EmailOrUsernameModelBackend'],
        )

    def test_login_accepts_email_without_case_sensitivity(self):
        user = self.create_account('utente_email')

        authenticated = authenticate(
            username='UTENTE_EMAIL@EXAMPLE.COM',
            password='Password-sicura-2026!',
        )

        self.assertEqual(authenticated, user)

    def test_inactive_user_cannot_authenticate(self):
        user = self.create_account('inattivo')
        user.is_active = False
        user.save(update_fields=['is_active'])

        self.assertIsNone(
            authenticate(username=user.username, password='Password-sicura-2026!')
        )

    def test_banned_user_cannot_authenticate(self):
        user = self.create_account('bannato', is_banned=True)

        self.assertIsNone(
            authenticate(username=user.username, password='Password-sicura-2026!')
        )

    def test_active_suspension_blocks_authentication(self):
        user = self.create_account(
            'sospeso',
            suspension_until=timezone.now() + timedelta(days=1),
        )

        self.assertIsNone(
            authenticate(username=user.username, password='Password-sicura-2026!')
        )

    def test_expired_suspension_does_not_block_authentication(self):
        user = self.create_account(
            'sospensione_scaduta',
            suspension_until=timezone.now() - timedelta(minutes=1),
        )

        authenticated = authenticate(
            username=user.username,
            password='Password-sicura-2026!',
        )

        self.assertEqual(authenticated, user)

    def test_legacy_user_without_profile_can_login_to_complete_it(self):
        user = User.objects.create_user(
            username='profilo_mancante',
            password='Password-sicura-2026!',
        )

        authenticated = authenticate(
            username=user.username,
            password='Password-sicura-2026!',
        )

        self.assertEqual(authenticated, user)

    def test_existing_session_is_denied_after_ban(self):
        user = self.create_account('sessione_bannata')
        self.client.force_login(
            user,
            backend='scambi.backends.EmailOrUsernameModelBackend',
        )
        profile = user.userprofile
        profile.is_banned = True
        profile.save(update_fields=['is_banned'])

        response = self.client.get(reverse('crea_annuncio'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))


class EmailDatabaseConstraintTests(TestCase):
    def test_database_rejects_case_insensitive_duplicate_email(self):
        User.objects.create_user(
            username='primo',
            email='utente@example.com',
            password='test',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username='secondo',
                    email='UTENTE@EXAMPLE.COM',
                    password='test',
                )

    def test_database_allows_multiple_empty_emails_for_legacy_accounts(self):
        User.objects.create_user(username='senza_email_1', email='', password='test')
        User.objects.create_user(username='senza_email_2', email='', password='test')

        self.assertEqual(User.objects.filter(email='').count(), 2)
