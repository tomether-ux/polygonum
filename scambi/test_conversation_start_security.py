from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Conversazione, Provincia, UserProfile


class StartConversationSecurityTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(
            username='conversazione_mittente',
            email='conversazione-mittente@example.com',
            password='Password-sicura-2026!',
        )
        self.recipient = User.objects.create_user(
            username='conversazione_destinatario',
            email='conversazione-destinatario@example.com',
            password='Password-sicura-2026!',
        )
        self.url = reverse(
            'inizia_conversazione',
            kwargs={'username': self.recipient.username},
        )

    def test_get_cannot_create_conversation(self):
        self.client.force_login(self.sender)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Conversazione.objects.count(), 0)

    def test_post_creates_private_conversation_and_redirects_to_it(self):
        self.client.force_login(self.sender)

        response = self.client.post(self.url)

        conversation = Conversazione.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse(
                'chat_conversazione',
                kwargs={'conversazione_id': conversation.id},
            ),
            fetch_redirect_response=False,
        )
        self.assertEqual(conversation.tipo, 'privata')
        self.assertSetEqual(
            set(conversation.utenti.values_list('id', flat=True)),
            {self.sender.id, self.recipient.id},
        )

    def test_post_reuses_existing_private_conversation(self):
        conversation = Conversazione.objects.create(tipo='privata')
        conversation.utenti.add(self.sender, self.recipient)
        self.client.force_login(self.sender)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Conversazione.objects.count(), 1)
        self.assertRedirects(
            response,
            reverse(
                'chat_conversazione',
                kwargs={'conversazione_id': conversation.id},
            ),
            fetch_redirect_response=False,
        )

    def test_anonymous_post_is_redirected_without_creating_conversation(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertEqual(Conversazione.objects.count(), 0)

    def test_post_to_self_does_not_create_conversation(self):
        self.client.force_login(self.sender)
        self_url = reverse(
            'inizia_conversazione',
            kwargs={'username': self.sender.username},
        )

        response = self.client.post(self_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('lista_messaggi'),
            fetch_redirect_response=False,
        )
        self.assertEqual(Conversazione.objects.count(), 0)

    def test_profile_form_supplies_csrf_for_conversation_creation(self):
        province = Provincia.objects.create(
            sigla='MI',
            nome='Milano',
            regione='Lombardia',
            latitudine=45.4642,
            longitudine=9.1900,
        )
        UserProfile.objects.create(
            user=self.recipient,
            provincia_obj=province,
            citta='Milano',
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.sender)
        profile_response = csrf_client.get(
            reverse(
                'profilo_utente',
                kwargs={'username': self.recipient.username},
            )
        )

        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, f'action="{self.url}"')
        self.assertContains(profile_response, 'method="post"')

        rejected = Client(enforce_csrf_checks=True)
        rejected.force_login(self.sender)
        missing_csrf_response = rejected.post(self.url)
        self.assertEqual(missing_csrf_response.status_code, 403)
        self.assertEqual(Conversazione.objects.count(), 0)

        csrf_token = csrf_client.cookies['csrftoken'].value
        accepted_response = csrf_client.post(
            self.url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(accepted_response.status_code, 302)
        self.assertEqual(Conversazione.objects.count(), 1)
