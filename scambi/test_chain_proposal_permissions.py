from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import CicloScambio, PropostaCatena, RispostaProposta


class ChainProposalStatusPermissionTests(TestCase):
    def setUp(self):
        self.initiator = User.objects.create_user(
            username='catena_iniziatore',
            email='catena-iniziatore@example.com',
            password='Password-sicura-2026!',
        )
        self.participant = User.objects.create_user(
            username='catena_partecipante',
            email='catena-partecipante@example.com',
            password='Password-sicura-2026!',
        )
        self.outsider = User.objects.create_user(
            username='catena_estraneo',
            email='catena-estraneo@example.com',
            password='Password-sicura-2026!',
        )
        self.cycle = CicloScambio.objects.create(
            users=[self.initiator.id, self.participant.id],
            lunghezza=2,
            dettagli={},
            valido=True,
            hash_ciclo='chain-proposal-permissions-cycle',
        )
        self.proposal = PropostaCatena.objects.create(
            ciclo=self.cycle,
            iniziatore=self.initiator,
        )
        RispostaProposta.objects.create(
            proposta=self.proposal,
            utente=self.initiator,
            risposta='interessato',
        )
        RispostaProposta.objects.create(
            proposta=self.proposal,
            utente=self.participant,
            risposta='in_attesa',
        )
        self.url = reverse(
            'stato_proposta_catena',
            kwargs={'ciclo_id': self.cycle.id},
        )

    def test_participant_can_read_proposal_status(self):
        self.client.force_login(self.participant)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['has_proposta'])
        self.assertEqual(payload['proposta_id'], self.proposal.id)
        self.assertEqual(payload['iniziatore'], self.initiator.username)
        self.assertEqual(payload['stato'], 'in_attesa')
        self.assertEqual(payload['count_interessati'], 1)
        self.assertEqual(payload['count_totale'], 2)
        self.assertEqual(payload['mia_risposta'], 'in_attesa')
        self.assertIn('giorni_scadenza', payload)
        self.assertEqual(
            payload['data_scadenza'],
            self.proposal.data_scadenza.isoformat(),
        )
        self.assertIn('no-store', response['Cache-Control'])

    def test_status_endpoint_accepts_get_only(self):
        self.client.force_login(self.participant)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_outsider_receives_not_found_without_proposal_metadata(self):
        self.client.force_login(self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(
            response,
            self.initiator.username,
            status_code=404,
        )
        self.assertNotContains(
            response,
            'has_proposta',
            status_code=404,
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_missing_or_invalid_cycle_is_not_disclosed(self):
        self.client.force_login(self.participant)
        self.cycle.valido = False
        self.cycle.save(update_fields=['valido'])

        invalid_response = self.client.get(self.url)
        missing_response = self.client.get(
            reverse('stato_proposta_catena', kwargs={'ciclo_id': 999999})
        )

        self.assertEqual(invalid_response.status_code, 404)
        self.assertEqual(missing_response.status_code, 404)
