from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .forms import CustomUserCreationForm
from .models import Annuncio, Categoria, Notifica, Provincia, UserProfile
from .views import attiva_annuncio, crea_annuncio


class AccountIntegrityTests(TestCase):
    def setUp(self):
        self.provincia = Provincia.objects.create(
            sigla='TS',
            nome='Trieste',
            regione='Friuli-Venezia Giulia',
            latitudine=45.6495,
            longitudine=13.7768,
        )

    def registration_data(self, **overrides):
        data = {
            'username': 'nuovo_utente',
            'email': 'Nuovo.Utente@Example.com',
            'password1': 'Password-sicura-2026!',
            'password2': 'Password-sicura-2026!',
            'citta': 'Trieste',
            'provincia_obj': str(self.provincia.pk),
            'accetta_regolamento': 'on',
        }
        data.update(overrides)
        return data

    def test_registration_creates_complete_inactive_account_atomically(self):
        form = CustomUserCreationForm(self.registration_data())

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        user.refresh_from_db()
        profile = user.userprofile
        self.assertFalse(user.is_active)
        self.assertEqual(user.email, 'nuovo.utente@example.com')
        self.assertEqual(profile.provincia_obj, self.provincia)
        self.assertEqual(profile.citta, 'Trieste')
        self.assertFalse(profile.email_verified)
        self.assertEqual(
            Notifica.objects.filter(utente=user, tipo='benvenuto').count(),
            1,
        )

    def test_duplicate_email_check_is_case_insensitive(self):
        User.objects.create_user(
            username='esistente',
            email='utente@example.com',
            password='Password-sicura-2026!',
        )
        form = CustomUserCreationForm(
            self.registration_data(email='UTENTE@EXAMPLE.COM'),
        )

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_profile_failure_rolls_back_user_creation(self):
        form = CustomUserCreationForm(self.registration_data())
        self.assertTrue(form.is_valid(), form.errors)

        with patch.object(
            UserProfile.objects,
            'create',
            side_effect=IntegrityError('simulated profile failure'),
        ):
            with self.assertRaises(IntegrityError):
                form.save()

        self.assertFalse(User.objects.filter(username='nuovo_utente').exists())

    def test_direct_user_creation_no_longer_creates_invalid_profile(self):
        user = User.objects.create_user(
            username='creato_da_admin',
            email='admin-created@example.com',
            password='Password-sicura-2026!',
        )

        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_profile_edit_get_does_not_create_profile(self):
        user = User.objects.create_user(username='senza_profilo', password='test')
        self.client.force_login(user)

        response = self.client.get(reverse('modifica_profilo'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserProfile.objects.filter(user=user).exists())
        self.assertContains(response, 'name="provincia_obj"')
        self.assertNotContains(response, 'name="citta_obj"')

    def test_profile_edit_valid_post_creates_complete_profile(self):
        user = User.objects.create_user(username='da_completare', password='test')
        self.client.force_login(user)

        response = self.client.post(
            reverse('modifica_profilo'),
            {
                'citta': 'Trieste',
                'provincia_obj': str(self.provincia.pk),
                'cap': '34100',
            },
        )

        self.assertRedirects(
            response,
            reverse('profilo_utente', kwargs={'username': user.username}),
            fetch_redirect_response=False,
        )
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.provincia_obj, self.provincia)

    def test_own_missing_profile_redirects_without_creating_data(self):
        user = User.objects.create_user(username='profilo_mancante', password='test')
        self.client.force_login(user)

        response = self.client.get(
            reverse('profilo_utente', kwargs={'username': user.username}),
        )

        self.assertRedirects(
            response,
            reverse('modifica_profilo'),
            fetch_redirect_response=False,
        )
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_public_missing_profile_is_404_without_creating_data(self):
        user = User.objects.create_user(username='profilo_non_pubblico', password='test')

        response = self.client.get(
            reverse('profilo_utente', kwargs={'username': user.username}),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_create_listing_requires_complete_profile(self):
        user = User.objects.create_user(username='senza_luogo', password='test')
        request = RequestFactory().get('/crea-annuncio/')
        request.user = user

        with patch('scambi.views.messages.warning'):
            response = crea_annuncio(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('modifica_profilo'))
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_reactivate_listing_requires_complete_profile(self):
        user = User.objects.create_user(username='riattivazione', password='test')
        categoria = Categoria.objects.create(nome='Test')
        annuncio = Annuncio.objects.create(
            utente=user,
            titolo='Oggetto di test',
            descrizione='Descrizione',
            categoria=categoria,
            tipo='offro',
            attivo=False,
        )
        request = RequestFactory().post(f'/attiva-annuncio/{annuncio.pk}/')
        request.user = user

        with patch('scambi.views.messages.warning'):
            response = attiva_annuncio(request, annuncio.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('modifica_profilo'))
        annuncio.refresh_from_db()
        self.assertFalse(annuncio.attivo)
        self.assertFalse(UserProfile.objects.filter(user=user).exists())


class AccountAuditCommandTests(TestCase):
    def test_audit_is_read_only_and_hides_identifiers_by_default(self):
        User.objects.create_user(
            username='audit_user',
            email='audit@example.com',
            password='test',
        )
        before_users = User.objects.count()
        before_profiles = UserProfile.objects.count()
        output = StringIO()

        call_command('audit_account_integrity', stdout=output)

        rendered = output.getvalue()
        self.assertIn('SOLA LETTURA', rendered)
        self.assertIn('Utenti senza profilo: 1', rendered)
        self.assertNotIn('audit_user', rendered)
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(UserProfile.objects.count(), before_profiles)
