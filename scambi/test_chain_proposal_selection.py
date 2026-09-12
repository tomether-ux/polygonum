import json

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from .matching import converti_ciclo_db_a_view_format
from .models import (
    Annuncio,
    Categoria,
    CicloScambio,
    Conversazione,
    PropostaCatena,
)


class ChainProposalSelectionTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='selection_a',
            email='selection-a@example.com',
            password='Password-sicura-2026!',
        )
        self.user_b = User.objects.create_user(
            username='selection_b',
            email='selection-b@example.com',
            password='Password-sicura-2026!',
        )
        self.category = Categoria.objects.create(nome='Selezione proposta')

        self.offer_a_1 = self._announcement(self.user_a, 'offro', 'Synth Alpha')
        self.offer_a_2 = self._announcement(self.user_a, 'offro', 'Synth Beta')
        self.request_b_1 = self._announcement(self.user_b, 'cerco', 'Cerco Alpha')
        self.request_b_2 = self._announcement(self.user_b, 'cerco', 'Cerco Beta')
        self.offer_b = self._announcement(self.user_b, 'offro', 'Chitarra')
        self.request_a = self._announcement(self.user_a, 'cerco', 'Cerco chitarra')

        self.cycle = CicloScambio.objects.create(
            users=[self.user_a.id, self.user_b.id],
            lunghezza=2,
            valido=True,
            hash_ciclo='proposal-selection-cycle',
            dettagli={
                'scambi': [
                    {
                        'da_user': self.user_a.id,
                        'a_user': self.user_b.id,
                        'oggetti': [
                            self._pair(self.offer_a_1, self.request_b_1),
                            self._pair(self.offer_a_2, self.request_b_2),
                        ],
                    },
                    {
                        'da_user': self.user_b.id,
                        'a_user': self.user_a.id,
                        'oggetti': [self._pair(self.offer_b, self.request_a)],
                    },
                ],
            },
        )
        self.url = reverse('proponi_catena', kwargs={'ciclo_id': self.cycle.id})
        self.client.force_login(self.user_a)

    def _announcement(self, user, kind, title):
        return Annuncio.objects.create(
            utente=user,
            titolo=title,
            descrizione='Descrizione valida',
            categoria=self.category,
            tipo=kind,
            attivo=True,
        )

    @staticmethod
    def _pair(offered, requested):
        return {
            'offerto': {'id': offered.id, 'titolo': offered.titolo},
            'richiesto': {'id': requested.id, 'titolo': requested.titolo},
        }

    def _selection(self, offered=None, requested=None):
        offered = offered or self.offer_a_1
        requested = requested or self.request_b_1
        return [
            {
                'da_user': self.user_a.id,
                'a_user': self.user_b.id,
                'offerto_id': offered.id,
                'richiesto_id': requested.id,
            },
            {
                'da_user': self.user_b.id,
                'a_user': self.user_a.id,
                'offerto_id': self.offer_b.id,
                'richiesto_id': self.request_a.id,
            },
        ]

    def _post_selection(self, selection):
        return self.client.post(
            self.url,
            data=json.dumps({'selezione_annunci': selection}),
            content_type='application/json',
        )

    def test_multiple_options_require_an_explicit_selection(self):
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.json()['requires_selection'])
        self.assertFalse(PropostaCatena.objects.exists())

    def test_valid_selection_is_saved_as_an_immutable_snapshot(self):
        response = self._post_selection(self._selection())

        self.assertEqual(response.status_code, 200)
        proposal = PropostaCatena.objects.get()
        selected = proposal.selezione_annunci['scambi']
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]['offerto_id'], self.offer_a_1.id)
        self.assertEqual(selected[0]['richiesto_id'], self.request_b_1.id)
        self.assertEqual(selected[0]['offerto_titolo'], self.offer_a_1.titolo)
        self.assertEqual(response.json()['selezione_annunci'], proposal.selezione_annunci)

    def test_pair_not_present_in_cycle_is_rejected(self):
        response = self._post_selection(
            self._selection(self.offer_a_1, self.request_b_2)
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PropostaCatena.objects.exists())

    def test_later_participant_cannot_replace_the_initial_selection(self):
        self._post_selection(self._selection(self.offer_a_1, self.request_b_1))
        proposal = PropostaCatena.objects.get()
        original_selection = proposal.selezione_annunci
        self.client.force_login(self.user_b)

        response = self._post_selection(
            self._selection(self.offer_a_2, self.request_b_2)
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['tutti_interessati'])
        proposal.refresh_from_db()
        self.assertEqual(proposal.selezione_annunci, original_selection)
        self.assertEqual(
            Conversazione.objects.filter(
                tipo='gruppo',
                catena_scambio_id=str(self.cycle.id),
            ).count(),
            1,
        )

    def test_unavailable_selected_announcement_cancels_pending_proposal(self):
        self._post_selection(self._selection())
        proposal = PropostaCatena.objects.get()
        self.offer_a_1.attivo = False
        self.offer_a_1.save(update_fields=['attivo'])
        self.client.force_login(self.user_b)

        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 409)
        proposal.refresh_from_db()
        self.assertEqual(proposal.stato, 'annullata')
        self.assertFalse(Conversazione.objects.exists())

    def test_status_exposes_selection_only_to_cycle_participants(self):
        self._post_selection(self._selection())
        self.client.force_login(self.user_b)

        response = self.client.get(reverse(
            'stato_proposta_catena',
            kwargs={'ciclo_id': self.cycle.id},
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['selezione_annunci']['scambi'][0]['offerto_id'],
            self.offer_a_1.id,
        )

    def test_my_proposals_show_only_the_selected_pair(self):
        self._post_selection(self._selection(self.offer_a_1, self.request_b_1))

        response = self.client.get(reverse('mie_proposte_catene'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.offer_a_1.titolo)
        self.assertContains(response, self.request_b_1.titolo)
        self.assertNotContains(response, self.offer_a_2.titolo)
        self.assertNotContains(response, self.request_b_2.titolo)

    def test_card_renders_selector_for_each_exchange(self):
        chain = converti_ciclo_db_a_view_format(
            self.cycle,
            Annuncio.objects.select_related('categoria').in_bulk(),
            utenti_dict=User.objects.in_bulk(),
        )
        self.assertEqual(len(chain['scambi_opzioni']), 2)

        html = render_to_string(
            'scambi/partials/chain_card.html',
            {
                'catena': chain,
                'forloop': {'counter': 1},
                'user': self.user_a,
                'cicli_interessati': set(),
                'csrf_token': 'test-token',
            },
        )

        self.assertIn('data-requires-selection="true"', html)
        self.assertEqual(
            html.count('class="form-select exchange-option-select"'),
            2,
        )
        self.assertIn('Scegli cosa scambiare', html)
        self.assertIn(self.offer_a_1.titolo, html)
        self.assertIn(self.offer_a_2.titolo, html)

    def test_single_option_per_exchange_is_selected_automatically(self):
        self.cycle.dettagli['scambi'][0]['oggetti'] = [
            self._pair(self.offer_a_1, self.request_b_1)
        ]
        self.cycle.save(update_fields=['dettagli'])

        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        proposal = PropostaCatena.objects.get()
        self.assertEqual(
            proposal.selezione_annunci['scambi'][0]['offerto_id'],
            self.offer_a_1.id,
        )
