from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .matching import get_cicli_precalcolati
from .models import CatenaNascosta, CicloScambio


class HiddenChainTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='catene_nascoste_utente',
            email='catene-nascoste@example.com',
            password='Password-sicura-2026!',
        )
        self.participant_a = User.objects.create_user(
            username='catene_nascoste_a',
            email='catene-nascoste-a@example.com',
            password='Password-sicura-2026!',
        )
        self.participant_b = User.objects.create_user(
            username='catene_nascoste_b',
            email='catene-nascoste-b@example.com',
            password='Password-sicura-2026!',
        )
        self.outsider = User.objects.create_user(
            username='catene_nascoste_estraneo',
            email='catene-nascoste-estraneo@example.com',
            password='Password-sicura-2026!',
        )
        self.first_cycle = self._cycle(
            self.participant_a,
            'hidden-cycle-first',
            'Sintetizzatore',
        )
        self.second_cycle = self._cycle(
            self.participant_b,
            'hidden-cycle-second',
            'Chitarra',
        )
        self.client.force_login(self.user)

    def _cycle(self, participant, cycle_hash, title):
        return CicloScambio.objects.create(
            users=[self.user.id, participant.id],
            lunghezza=2,
            dettagli={
                'scambi': [{
                    'oggetti': [{
                        'offerto': {'id': 1, 'titolo': title},
                        'richiesto': {'id': 2, 'titolo': f'Cerco {title}'},
                    }],
                }],
            },
            valido=True,
            hash_ciclo=cycle_hash,
        )

    def test_participant_can_hide_chain_and_redirect_back(self):
        response = self.client.post(
            reverse('nascondi_catena', kwargs={'ciclo_id': self.first_cycle.id}),
            {'next': '/catene-scambio/?load=true'},
        )

        self.assertRedirects(
            response,
            '/catene-scambio/?load=true',
            fetch_redirect_response=False,
        )
        self.assertTrue(CatenaNascosta.objects.filter(
            utente=self.user,
            ciclo=self.first_cycle,
        ).exists())

    def test_ajax_hide_returns_json(self):
        response = self.client.post(
            reverse('nascondi_catena', kwargs={'ciclo_id': self.first_cycle.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        self.assertTrue(CatenaNascosta.objects.filter(
            utente=self.user,
            ciclo=self.first_cycle,
        ).exists())

    def test_outsider_cannot_hide_chain_and_get_is_rejected(self):
        self.client.force_login(self.outsider)

        post_response = self.client.post(reverse(
            'nascondi_catena',
            kwargs={'ciclo_id': self.first_cycle.id},
        ))
        get_response = self.client.get(reverse(
            'nascondi_catena',
            kwargs={'ciclo_id': self.first_cycle.id},
        ))

        self.assertEqual(post_response.status_code, 404)
        self.assertEqual(get_response.status_code, 405)
        self.assertEqual(CatenaNascosta.objects.count(), 0)

    @patch('scambi.matching.converti_ciclo_db_a_view_format')
    def test_hidden_chain_is_filtered_before_counts(self, convert_cycle):
        CatenaNascosta.objects.create(
            utente=self.user,
            ciclo=self.first_cycle,
        )
        convert_cycle.side_effect = lambda cycle, *args, **kwargs: {
            'id_ciclo': str(cycle.id),
            'lunghezza': cycle.lunghezza,
            'utenti': [],
        }

        result = get_cicli_precalcolati(
            user_id=self.user.id,
            per_length_limit=20,
        )

        loaded = result['scambi_diretti'] + result['catene']
        self.assertEqual(result['totale_disponibili'], 1)
        self.assertEqual(result['totali_per_lunghezza'][2], 1)
        self.assertEqual(
            [item['id_ciclo'] for item in loaded],
            [str(self.second_cycle.id)],
        )

    def test_hidden_chains_page_lists_only_current_users_preferences(self):
        CatenaNascosta.objects.create(
            utente=self.user,
            ciclo=self.first_cycle,
        )
        CatenaNascosta.objects.create(
            utente=self.outsider,
            ciclo=self.second_cycle,
        )

        response = self.client.get(reverse('catene_nascoste'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sintetizzatore')
        self.assertContains(response, self.participant_a.username)
        self.assertNotContains(response, 'Chitarra')
        self.assertNotContains(response, self.participant_b.username)

    def test_restore_removes_only_personal_marker_not_cycle(self):
        CatenaNascosta.objects.create(
            utente=self.user,
            ciclo=self.first_cycle,
        )

        response = self.client.post(reverse(
            'ripristina_catena',
            kwargs={'ciclo_id': self.first_cycle.id},
        ))

        self.assertRedirects(response, reverse('catene_nascoste'))
        self.assertFalse(CatenaNascosta.objects.filter(
            utente=self.user,
            ciclo=self.first_cycle,
        ).exists())
        self.assertTrue(CicloScambio.objects.filter(
            pk=self.first_cycle.pk,
        ).exists())

    def test_user_cannot_restore_another_users_hidden_chain(self):
        hidden = CatenaNascosta.objects.create(
            utente=self.outsider,
            ciclo=self.first_cycle,
        )

        post_response = self.client.post(reverse(
            'ripristina_catena',
            kwargs={'ciclo_id': self.first_cycle.id},
        ))
        get_response = self.client.get(reverse(
            'ripristina_catena',
            kwargs={'ciclo_id': self.first_cycle.id},
        ))

        self.assertEqual(post_response.status_code, 404)
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(CatenaNascosta.objects.filter(pk=hidden.pk).exists())

    def test_external_next_url_is_not_used(self):
        response = self.client.post(
            reverse('nascondi_catena', kwargs={'ciclo_id': self.first_cycle.id}),
            {'next': 'https://attacker.example/phishing'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('catene_scambio')}?load=true",
        )
