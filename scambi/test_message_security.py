import json

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import Annuncio, Categoria, Conversazione, Messaggio


class AnnouncementMessageSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.sender = User.objects.create_user(
            username='mittente',
            email='mittente@example.com',
            password='Password-sicura-2026!',
        )
        self.owner = User.objects.create_user(
            username='proprietario',
            email='proprietario@example.com',
            password='Password-sicura-2026!',
        )
        self.other_user = User.objects.create_user(
            username='estraneo',
            email='estraneo@example.com',
            password='Password-sicura-2026!',
        )
        categoria = Categoria.objects.create(nome='Messaggistica')
        self.annuncio = Annuncio.objects.create(
            utente=self.owner,
            titolo='Oggetto disponibile',
            descrizione='Descrizione valida',
            categoria=categoria,
            tipo='offro',
            attivo=True,
        )
        self.client.force_login(self.sender)
        self.url = reverse('invia_messaggio_da_annuncio')

    def send_message(self, **overrides):
        payload = {
            'destinatario_id': self.owner.id,
            'annuncio_id': self.annuncio.id,
            'messaggio': 'Ciao, sono interessato.',
        }
        payload.update(overrides)
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_valid_message_is_sent_to_announcement_owner(self):
        response = self.send_message()

        self.assertEqual(response.status_code, 200)
        conversation = Conversazione.objects.get()
        self.assertSetEqual(
            set(conversation.utenti.values_list('id', flat=True)),
            {self.sender.id, self.owner.id},
        )
        self.assertEqual(Messaggio.objects.count(), 1)

    def test_forged_recipient_is_rejected(self):
        response = self.send_message(destinatario_id=self.other_user.id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Messaggio.objects.count(), 0)
        self.assertEqual(Conversazione.objects.count(), 0)

    def test_inactive_announcement_cannot_be_used_to_send_message(self):
        Annuncio.objects.filter(pk=self.annuncio.pk).update(attivo=False)

        response = self.send_message()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Messaggio.objects.count(), 0)

    def test_non_object_json_is_rejected(self):
        response = self.client.post(
            self.url,
            data=json.dumps(['not', 'an', 'object']),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Messaggio.objects.count(), 0)

    def test_announcement_messages_are_rate_limited_per_user(self):
        for _ in range(20):
            response = self.send_message()
            self.assertEqual(response.status_code, 200)

        blocked = self.send_message()

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(Messaggio.objects.count(), 20)


class ConversationMessageRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.sender = User.objects.create_user(
            username='chat_mittente',
            email='chat-mittente@example.com',
            password='Password-sicura-2026!',
        )
        recipient = User.objects.create_user(
            username='chat_destinatario',
            email='chat-destinatario@example.com',
            password='Password-sicura-2026!',
        )
        self.conversation = Conversazione.objects.create(tipo='privata')
        self.conversation.utenti.add(self.sender, recipient)
        self.client.force_login(self.sender)
        self.url = reverse(
            'chat_conversazione',
            kwargs={'conversazione_id': self.conversation.id},
        )

    def test_chat_post_is_rate_limited_but_get_remains_available(self):
        for index in range(20):
            response = self.client.post(
                self.url,
                data={'contenuto': f'Messaggio {index}'},
            )
            self.assertEqual(response.status_code, 302)

        blocked = self.client.post(
            self.url,
            data={'contenuto': 'Messaggio oltre il limite'},
        )
        page = self.client.get(self.url)

        self.assertEqual(blocked.status_code, 302)
        self.assertEqual(Messaggio.objects.count(), 20)
        self.assertEqual(page.status_code, 200)
