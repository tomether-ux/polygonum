import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Annuncio,
    CatenaScambio,
    Categoria,
    CicloScambio,
    Conversazione,
    Messaggio,
    Notifica,
    PartecipazioneScambio,
    PropostaCatena,
    RispostaProposta,
)


class PrivateConversationIdempotencyTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(
            username='chat_atomica_mittente',
            email='chat-atomica-mittente@example.com',
            password='Password-sicura-2026!',
        )
        self.recipient = User.objects.create_user(
            username='chat_atomica_destinatario',
            email='chat-atomica-destinatario@example.com',
            password='Password-sicura-2026!',
        )
        self.third_user = User.objects.create_user(
            username='chat_atomica_terzo',
            email='chat-atomica-terzo@example.com',
            password='Password-sicura-2026!',
        )
        category = Categoria.objects.create(nome='Chat atomica')
        self.announcement = Annuncio.objects.create(
            utente=self.recipient,
            titolo='Oggetto per chat atomica',
            descrizione='Descrizione',
            categoria=category,
            tipo='offro',
            attivo=True,
        )
        self.client.force_login(self.sender)

    def test_profile_and_announcement_entry_points_reuse_same_chat(self):
        start_response = self.client.post(reverse(
            'inizia_conversazione',
            kwargs={'username': self.recipient.username},
        ))
        message_response = self.client.post(
            reverse('invia_messaggio_da_annuncio'),
            data=json.dumps({
                'destinatario_id': self.recipient.id,
                'annuncio_id': self.announcement.id,
                'messaggio': 'Ciao!',
            }),
            content_type='application/json',
        )

        self.assertEqual(start_response.status_code, 302)
        self.assertEqual(message_response.status_code, 200)
        self.assertEqual(Conversazione.objects.filter(tipo='privata').count(), 1)
        conversation = Conversazione.objects.get(tipo='privata')
        self.assertEqual(
            message_response.json()['conversazione_id'],
            conversation.id,
        )

    def test_private_chat_with_third_participant_is_not_reused(self):
        malformed = Conversazione.objects.create(tipo='privata')
        malformed.utenti.add(self.sender, self.recipient, self.third_user)

        response = self.client.post(reverse(
            'inizia_conversazione',
            kwargs={'username': self.recipient.username},
        ))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Conversazione.objects.filter(tipo='privata').count(), 2)
        exact_chat = (
            Conversazione.objects.filter(tipo='privata', utenti=self.sender)
            .filter(utenti=self.recipient)
            .exclude(pk=malformed.pk)
            .get()
        )
        self.assertSetEqual(
            set(exact_chat.utenti.values_list('id', flat=True)),
            {self.sender.id, self.recipient.id},
        )


class CycleProposalIdempotencyTests(TestCase):
    def setUp(self):
        self.initiator = User.objects.create_user(
            username='proposta_atomica_iniziatore',
            email='proposta-atomica-iniziatore@example.com',
            password='Password-sicura-2026!',
        )
        self.participant = User.objects.create_user(
            username='proposta_atomica_partecipante',
            email='proposta-atomica-partecipante@example.com',
            password='Password-sicura-2026!',
        )
        self.cycle = CicloScambio.objects.create(
            users=[self.initiator.id, self.participant.id],
            lunghezza=2,
            dettagli={},
            valido=True,
            hash_ciclo='cycle-proposal-idempotency',
        )

    def _create_pending_proposal(self):
        proposal = PropostaCatena.objects.create(
            ciclo=self.cycle,
            iniziatore=self.initiator,
        )
        RispostaProposta.objects.create(
            proposta=proposal,
            utente=self.initiator,
            risposta='interessato',
        )
        RispostaProposta.objects.create(
            proposta=proposal,
            utente=self.participant,
            risposta='in_attesa',
        )
        return proposal

    def test_repeated_interested_response_does_not_duplicate_group_side_effects(self):
        proposal = self._create_pending_proposal()
        self.client.force_login(self.participant)
        url = reverse(
            'rispondi_proposta_catena',
            kwargs={'proposta_id': proposal.id},
        )

        first_response = self.client.post(url, {'azione': 'interessato'})
        second_response = self.client.post(url, {'azione': 'interessato'})

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        group_chats = Conversazione.objects.filter(
            tipo='gruppo',
            catena_scambio_id=str(self.cycle.id),
        )
        self.assertEqual(group_chats.count(), 1)
        self.assertEqual(
            Messaggio.objects.filter(
                conversazione=group_chats.get(),
                is_sistema=True,
            ).count(),
            1,
        )
        self.assertEqual(
            Notifica.objects.filter(tipo='tutti_interessati').count(),
            2,
        )

    def test_proposal_toggle_path_creates_only_one_group_chat(self):
        self.client.force_login(self.initiator)
        url = reverse('proponi_catena', kwargs={'ciclo_id': self.cycle.id})
        created_response = self.client.post(url)

        self.client.force_login(self.participant)
        completed_response = self.client.post(url)

        self.assertEqual(created_response.status_code, 200)
        self.assertEqual(completed_response.status_code, 200)
        self.assertTrue(completed_response.json()['tutti_interessati'])
        self.assertEqual(
            Conversazione.objects.filter(
                tipo='gruppo',
                catena_scambio_id=str(self.cycle.id),
            ).count(),
            1,
        )
        self.assertEqual(PropostaCatena.objects.filter(ciclo=self.cycle).count(), 1)

    def test_group_with_colliding_legacy_id_is_not_reused(self):
        unrelated_group = Conversazione.objects.create(
            tipo='gruppo',
            nome='Vecchia catena con ID numerico',
            catena_scambio_id=str(self.cycle.id),
        )
        unrelated_group.utenti.add(self.initiator)
        proposal = self._create_pending_proposal()
        self.client.force_login(self.participant)

        response = self.client.post(
            reverse(
                'rispondi_proposta_catena',
                kwargs={'proposta_id': proposal.id},
            ),
            {'azione': 'interessato'},
        )

        self.assertEqual(response.status_code, 200)
        proposal_group = Conversazione.objects.exclude(
            pk=unrelated_group.pk
        ).get(
            tipo='gruppo',
            catena_scambio_id=str(self.cycle.id),
        )
        self.assertSetEqual(
            set(proposal_group.utenti.values_list('id', flat=True)),
            {self.initiator.id, self.participant.id},
        )


class LegacyChainActivationIdempotencyTests(TestCase):
    def setUp(self):
        self.initiator = User.objects.create_user(
            username='attivazione_atomica_iniziatore',
            email='attivazione-atomica-iniziatore@example.com',
            password='Password-sicura-2026!',
        )
        self.participant = User.objects.create_user(
            username='attivazione_atomica_partecipante',
            email='attivazione-atomica-partecipante@example.com',
            password='Password-sicura-2026!',
        )
        category = Categoria.objects.create(nome='Attivazione atomica')
        first_announcement = Annuncio.objects.create(
            utente=self.initiator,
            titolo='Primo oggetto',
            descrizione='Descrizione',
            categoria=category,
            tipo='offro',
        )
        second_announcement = Annuncio.objects.create(
            utente=self.participant,
            titolo='Secondo oggetto',
            descrizione='Descrizione',
            categoria=category,
            tipo='offro',
        )
        self.chain = CatenaScambio.objects.create(
            catena_id='legacy-chain-idempotency',
            nome='Catena atomica',
            dati_catena={},
        )
        PartecipazioneScambio.objects.create(
            catena=self.chain,
            utente=self.initiator,
            annuncio_da_dare=first_announcement,
            annuncio_da_ricevere=second_announcement,
        )
        PartecipazioneScambio.objects.create(
            catena=self.chain,
            utente=self.participant,
            annuncio_da_dare=second_announcement,
            annuncio_da_ricevere=first_announcement,
        )
        self.client.force_login(self.initiator)

    def test_repeated_activation_does_not_create_a_second_group_chat(self):
        url = reverse('attiva_catena', kwargs={'catena_id': self.chain.catena_id})

        first_response = self.client.post(url)
        second_response = self.client.post(url)

        self.assertEqual(first_response.status_code, 200)
        self.assertTrue(first_response.json()['success'])
        self.assertEqual(second_response.status_code, 200)
        self.assertFalse(second_response.json()['success'])
        group_chats = Conversazione.objects.filter(
            tipo='gruppo',
            catena_scambio_id=self.chain.catena_id,
        )
        self.assertEqual(group_chats.count(), 1)
        self.assertEqual(
            Messaggio.objects.filter(conversazione=group_chats.get()).count(),
            1,
        )
