from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.signing import TimestampSigner
from django.test import Client, TestCase
from django.urls import reverse

from .models import Annuncio, Categoria, Notifica, Provincia, UserProfile


class ModerationLinkSafetyTests(TestCase):
    def setUp(self):
        provincia = Provincia.objects.create(
            sigla='MI',
            nome='Milano',
            regione='Lombardia',
            latitudine=45.4642,
            longitudine=9.1900,
        )
        self.user = User.objects.create_user(
            username='utente_moderato',
            email='moderato@example.com',
            password='Password-sicura-2026!',
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            provincia_obj=provincia,
            citta='Milano',
        )
        categoria = Categoria.objects.create(nome='Moderazione link')
        self.annuncio = Annuncio.objects.create(
            utente=self.user,
            titolo='Oggetto da controllare',
            descrizione='Descrizione valida',
            categoria=categoria,
            tipo='offro',
            attivo=True,
        )
        Annuncio.objects.filter(pk=self.annuncio.pk).update(
            moderation_status='pending',
        )
        self.client = Client(enforce_csrf_checks=True)
        self.approve_url = self.url_for('approve')
        self.reject_url = self.url_for('reject')

    def url_for(self, action):
        token = TimestampSigner(salt=f'moderation-{action}').sign(
            f'{action}_{self.annuncio.id}'
        )
        return reverse(f'moderazione_{action}', kwargs={'token': token})

    def csrf_token_after_get(self, url):
        response = self.client.get(url)
        return response, self.client.cookies['csrftoken'].value

    def assert_announcement_is_pending(self):
        self.annuncio.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.annuncio.moderation_status, 'pending')
        self.assertTrue(self.annuncio.attivo)
        self.assertEqual(self.profile.content_strikes, 0)
        self.assertEqual(Notifica.objects.count(), 0)

    def test_get_on_both_email_links_is_read_only(self):
        approve_response = self.client.get(self.approve_url)
        reject_response = self.client.get(self.reject_url)

        self.assertEqual(approve_response.status_code, 200)
        self.assertContains(approve_response, 'Conferma approvazione')
        self.assertEqual(reject_response.status_code, 200)
        self.assertContains(reject_response, 'Conferma rifiuto')
        self.assertIn('no-store', approve_response['Cache-Control'])
        self.assertIn('no-store', reject_response['Cache-Control'])
        self.assert_announcement_is_pending()

    def test_post_without_csrf_is_rejected_without_changes(self):
        response = self.client.post(self.approve_url)

        self.assertEqual(response.status_code, 403)
        self.assert_announcement_is_pending()

    def test_confirmed_approval_changes_state_once(self):
        _, csrf_token = self.csrf_token_after_get(self.approve_url)

        first = self.client.post(
            self.approve_url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        second = self.client.post(
            self.approve_url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.annuncio.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, 'Annuncio Approvato!')
        self.assertEqual(second.status_code, 200)
        self.assertContains(second, 'Annuncio già approvato')
        self.assertEqual(self.annuncio.moderation_status, 'approved')
        self.assertTrue(self.annuncio.attivo)
        self.assertEqual(Notifica.objects.count(), 1)

    def test_confirmed_rejection_applies_only_one_strike(self):
        _, csrf_token = self.csrf_token_after_get(self.reject_url)

        first = self.client.post(
            self.reject_url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        second = self.client.post(
            self.reject_url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.annuncio.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, 'strike 1/3')
        self.assertEqual(second.status_code, 200)
        self.assertContains(second, 'Nessun ulteriore strike')
        self.assertEqual(self.annuncio.moderation_status, 'rejected')
        self.assertFalse(self.annuncio.attivo)
        self.assertEqual(self.profile.content_strikes, 1)
        self.assertEqual(Notifica.objects.count(), 1)

    def test_head_request_cannot_moderate(self):
        response = self.client.head(self.reject_url)

        self.assertEqual(response.status_code, 405)
        self.assert_announcement_is_pending()

    def test_wrong_salt_and_expired_tokens_are_rejected(self):
        wrong_salt_response = self.client.get(
            reverse(
                'moderazione_approve',
                kwargs={
                    'token': TimestampSigner(salt='moderation-reject').sign(
                        f'approve_{self.annuncio.id}'
                    ),
                },
            )
        )

        with patch('django.core.signing.time.time', return_value=1_000):
            expired_token = TimestampSigner(salt='moderation-approve').sign(
                f'approve_{self.annuncio.id}'
            )
        with patch('django.core.signing.time.time', return_value=1_000 + 86_401):
            expired_response = self.client.get(
                reverse(
                    'moderazione_approve',
                    kwargs={'token': expired_token},
                )
            )

        self.assertEqual(wrong_salt_response.status_code, 400)
        self.assertEqual(expired_response.status_code, 410)
        self.assert_announcement_is_pending()
