import json
import os
import subprocess
import sys

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import (
    Annuncio,
    Categoria,
    CicloScambio,
    ConfermaCompletamento,
    Conversazione,
    Messaggio,
    Notifica,
    PropostaCatena,
    PropostaScambio,
)


class DirectExchangeIdempotencyTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='scambio_diretto_richiedente',
            email='scambio-diretto-richiedente@example.com',
            password='Password-sicura-2026!',
        )
        self.recipient = User.objects.create_user(
            username='scambio_diretto_destinatario',
            email='scambio-diretto-destinatario@example.com',
            password='Password-sicura-2026!',
        )
        category = Categoria.objects.create(nome='Scambi diretti atomici')
        self.offered = Annuncio.objects.create(
            utente=self.requester,
            titolo='Oggetto offerto',
            descrizione='Descrizione',
            categoria=category,
            tipo='offro',
            attivo=True,
        )
        self.requested = Annuncio.objects.create(
            utente=self.recipient,
            titolo='Oggetto richiesto',
            descrizione='Descrizione',
            categoria=category,
            tipo='offro',
            attivo=True,
        )
        self.create_url = reverse(
            'crea_proposta_scambio',
            kwargs={
                'annuncio_offerto_id': self.offered.id,
                'annuncio_richiesto_id': self.requested.id,
            },
        )

    def test_repeated_creation_has_one_pending_proposal_and_notification(self):
        self.client.force_login(self.requester)

        first_response = self.client.post(
            self.create_url,
            {'messaggio': 'Ti propongo questo scambio.'},
        )
        second_response = self.client.post(
            self.create_url,
            {'messaggio': 'Richiesta duplicata.'},
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(PropostaScambio.objects.count(), 1)
        self.assertEqual(
            Notifica.objects.filter(tipo='proposta_scambio').count(),
            1,
        )

    def test_first_response_wins_and_cannot_be_overwritten(self):
        proposal = PropostaScambio.objects.create(
            richiedente=self.requester,
            destinatario=self.recipient,
            annuncio_offerto=self.offered,
            annuncio_richiesto=self.requested,
        )
        self.client.force_login(self.recipient)
        url = reverse(
            'rispondi_proposta_scambio',
            kwargs={'proposta_id': proposal.id},
        )

        accepted = self.client.post(url, {'azione': 'accetta'})
        repeated = self.client.post(url, {'azione': 'rifiuta'})

        proposal.refresh_from_db()
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(accepted.json()['success'])
        self.assertEqual(repeated.status_code, 200)
        self.assertFalse(repeated.json()['success'])
        self.assertEqual(proposal.stato, 'accettata')

    def test_invalid_response_action_returns_bad_request(self):
        proposal = PropostaScambio.objects.create(
            richiedente=self.requester,
            destinatario=self.recipient,
            annuncio_offerto=self.offered,
            annuncio_richiesto=self.requested,
        )
        self.client.force_login(self.recipient)

        response = self.client.post(
            reverse(
                'rispondi_proposta_scambio',
                kwargs={'proposta_id': proposal.id},
            ),
            {'azione': 'azione-sconosciuta'},
        )

        proposal.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(proposal.stato, 'in_attesa')


class ChainCompletionIdempotencyTests(TestCase):
    def setUp(self):
        self.first_user = User.objects.create_user(
            username='completamento_primo',
            email='completamento-primo@example.com',
            password='Password-sicura-2026!',
        )
        self.second_user = User.objects.create_user(
            username='completamento_secondo',
            email='completamento-secondo@example.com',
            password='Password-sicura-2026!',
        )
        self.cycle = CicloScambio.objects.create(
            users=[self.first_user.id, self.second_user.id],
            lunghezza=2,
            dettagli={},
            valido=True,
            hash_ciclo='cycle-completion-idempotency',
        )
        self.proposal = PropostaCatena.objects.create(
            ciclo=self.cycle,
            iniziatore=self.first_user,
            stato='tutti_interessati',
        )
        self.conversation = Conversazione.objects.create(
            tipo='gruppo',
            catena_scambio_id=str(self.cycle.id),
        )
        self.conversation.utenti.add(self.first_user, self.second_user)
        self.url = reverse(
            'conferma_completamento_catena',
            kwargs={'ciclo_id': self.cycle.id},
        )

    def test_only_final_confirmation_completes_and_notifies_once(self):
        self.client.force_login(self.first_user)
        first_response = self.client.post(self.url)

        self.client.force_login(self.second_user)
        final_response = self.client.post(self.url)
        repeated_response = self.client.post(self.url)

        self.proposal.refresh_from_db()
        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(final_response.status_code, 302)
        self.assertEqual(repeated_response.status_code, 302)
        self.assertEqual(self.proposal.stato, 'completata')
        self.assertEqual(
            ConfermaCompletamento.objects.filter(
                proposta=self.proposal,
            ).count(),
            2,
        )
        self.assertEqual(
            Messaggio.objects.filter(
                conversazione=self.conversation,
                is_sistema=True,
            ).count(),
            1,
        )

    def test_completed_legacy_state_does_not_emit_completion_again(self):
        self.proposal.stato = 'completata'
        self.proposal.save(update_fields=['stato'])
        ConfermaCompletamento.objects.create(
            proposta=self.proposal,
            utente=self.first_user,
        )
        self.client.force_login(self.second_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Messaggio.objects.filter(
                conversazione=self.conversation,
                is_sistema=True,
            ).count(),
            0,
        )

    def test_completion_transition_reports_true_only_once(self):
        ConfermaCompletamento.objects.create(
            proposta=self.proposal,
            utente=self.first_user,
        )
        ConfermaCompletamento.objects.create(
            proposta=self.proposal,
            utente=self.second_user,
        )

        first_transition = self.proposal.check_tutti_confermato()
        repeated_check = self.proposal.check_tutti_confermato()

        self.assertTrue(first_transition)
        self.assertFalse(repeated_check)


class CycleApiHardeningTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='api_cicli_utente',
            email='api-cicli-utente@example.com',
            password='Password-sicura-2026!',
        )
        self.client.force_login(self.user)
        self.user_url = reverse(
            'api_cicli_utente',
            kwargs={'user_id': self.user.id},
        )

    def test_invalid_pagination_returns_bad_request(self):
        invalid_queries = (
            {'limit': 'non-un-numero'},
            {'limit': '0'},
            {'limit': '101'},
            {'offset': '-1'},
        )

        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(self.user_url, query)
                self.assertEqual(response.status_code, 400)

    def test_user_cycle_api_is_rate_limited(self):
        for _ in range(60):
            response = self.client.get(self.user_url)
            self.assertEqual(response.status_code, 200)

        blocked = self.client.get(self.user_url)

        self.assertEqual(blocked.status_code, 429)

    def test_public_stats_api_is_rate_limited_by_ip(self):
        stats_url = reverse('api_cicli_stats')

        for _ in range(60):
            response = self.client.get(stats_url)
            self.assertEqual(response.status_code, 200)

        blocked = self.client.get(stats_url)

        self.assertEqual(blocked.status_code, 429)


class ProductionDatabaseConnectionTests(SimpleTestCase):
    def test_render_database_reuses_and_health_checks_connections(self):
        environment = os.environ.copy()
        environment.update({
            'PYTHONDONTWRITEBYTECODE': '1',
            'RENDER': 'true',
            'DJANGO_SECRET_KEY': 'test-only-secret-key',
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',
            'ADMIN_MODERATION_EMAIL': 'moderation@example.invalid',
            'ALLOWED_HOSTS': '.onrender.com,polygonum.io,www.polygonum.io',
        })
        code = (
            'import json; '
            'from scambio_sito import settings; '
            'db = settings.DATABASES["default"]; '
            'print(json.dumps({'
            '"conn_max_age": db["CONN_MAX_AGE"], '
            '"conn_health_checks": db["CONN_HEALTH_CHECKS"]'
            '}))'
        )

        result = subprocess.run(
            [sys.executable, '-c', code],
            cwd=str(os.path.dirname(os.path.dirname(__file__))),
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        config = json.loads(result.stdout.strip().splitlines()[-1])

        self.assertEqual(config['conn_max_age'], 60)
        self.assertTrue(config['conn_health_checks'])
