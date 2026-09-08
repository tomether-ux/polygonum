from unittest.mock import patch

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from .matching import (
    converti_ciclo_db_a_view_format,
    estrai_annunci_ids_dettagli,
)
from .models import Annuncio, Categoria, CicloScambio


class ChainAnnouncementAlternativesTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='alternative_a',
            email='alternative-a@example.com',
            password='Password-sicura-2026!',
        )
        self.user_b = User.objects.create_user(
            username='alternative_b',
            email='alternative-b@example.com',
            password='Password-sicura-2026!',
        )
        self.category = Categoria.objects.create(nome='Strumenti musicali')

        self.offer_a_1 = self._annuncio(self.user_a, 'offro', 'Synth Alpha')
        self.offer_a_2 = self._annuncio(self.user_a, 'offro', 'Synth Beta')
        self.request_b_1 = self._annuncio(self.user_b, 'cerco', 'Synth Alpha')
        self.request_b_2 = self._annuncio(self.user_b, 'cerco', 'Synth Beta')

        self.offer_b_1 = self._annuncio(self.user_b, 'offro', 'Chitarra Alpha')
        self.offer_b_2 = self._annuncio(self.user_b, 'offro', 'Chitarra Beta')
        self.request_a_1 = self._annuncio(self.user_a, 'cerco', 'Chitarra Alpha')
        self.request_a_2 = self._annuncio(self.user_a, 'cerco', 'Chitarra Beta')

        self.details = {
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
                    'oggetti': [
                        self._pair(self.offer_b_1, self.request_a_1),
                        self._pair(self.offer_b_2, self.request_a_2),
                    ],
                },
            ],
            'punteggio_qualita': 80,
        }
        self.cycle = CicloScambio.objects.create(
            users=[self.user_a.id, self.user_b.id],
            lunghezza=2,
            dettagli=self.details,
            valido=True,
            hash_ciclo='c' * 32,
        )

    def _annuncio(self, user, tipo, title):
        return Annuncio.objects.create(
            utente=user,
            titolo=title,
            descrizione='Descrizione valida per il test',
            categoria=self.category,
            tipo=tipo,
            attivo=True,
        )

    @staticmethod
    def _pair(offer, request):
        return {
            'offerto': {
                'id': offer.id,
                'titolo': offer.titolo,
                'categoria': offer.categoria.nome,
            },
            'richiesto': {
                'id': request.id,
                'titolo': request.titolo,
                'categoria': request.categoria.nome,
            },
            'tipo_match': 'specifico',
        }

    def _convert(self, preferred_announcement_id=None):
        annunci_dict = Annuncio.objects.select_related('categoria').in_bulk()
        utenti_dict = User.objects.in_bulk()
        return converti_ciclo_db_a_view_format(
            self.cycle,
            annunci_dict,
            utenti_dict=utenti_dict,
            preferred_announcement_id=preferred_announcement_id,
        )

    def test_converter_preserves_all_compatible_announcements(self):
        chain = self._convert()
        user_a_data = next(
            item for item in chain['utenti'] if item['user'].id == self.user_a.id
        )

        self.assertEqual(
            [item.id for item in user_a_data['richiede_opzioni']],
            [self.request_a_1.id, self.request_a_2.id],
        )
        self.assertEqual(
            set(chain['annunci_ids']),
            {
                self.offer_a_1.id,
                self.offer_a_2.id,
                self.request_b_1.id,
                self.request_b_2.id,
                self.offer_b_1.id,
                self.offer_b_2.id,
                self.request_a_1.id,
                self.request_a_2.id,
            },
        )
        self.assertEqual(
            estrai_annunci_ids_dettagli(self.details),
            chain['annunci_ids'],
        )

    def test_selected_alternative_becomes_preview_with_its_matching_pair(self):
        chain = self._convert(preferred_announcement_id=self.request_a_1.id)
        user_a_data = next(
            item for item in chain['utenti'] if item['user'].id == self.user_a.id
        )
        user_b_data = next(
            item for item in chain['utenti'] if item['user'].id == self.user_b.id
        )

        self.assertEqual(user_a_data['richiede'].id, self.request_a_1.id)
        self.assertEqual(user_b_data['offerta'].id, self.offer_b_1.id)

    def test_chain_card_renders_dropdowns_and_all_filter_ids(self):
        chain = self._convert()
        html = render_to_string(
            'scambi/partials/chain_card.html',
            {
                'catena': chain,
                'forloop': {'counter': 1},
                'user': self.user_a,
                'cicli_interessati': set(),
            },
        )

        self.assertIn('Vedi altre richieste compatibili (1)', html)
        self.assertIn('Vedi altre offerte compatibili (1)', html)
        self.assertIn(
            f'data-annuncio-option-id="{self.request_a_1.id}"',
            html,
        )
        self.assertIn(
            f'data-annunci-ids="{",".join(map(str, chain["annunci_ids"]))}"',
            html,
        )

    @patch('scambi.views.CicloScambio.find_for_user')
    def test_personal_page_finds_an_announcement_stored_as_alternative(self, find_for_user):
        find_for_user.return_value = [self.cycle]
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse('le_mie_catene'),
            {'annuncio_id': self.request_a_1.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['totale_catene'], 1)
        self.assertContains(response, self.request_a_1.titolo)

    @patch('scambi.matching.get_cicli_precalcolati')
    def test_main_page_passes_selected_announcement_to_converter(self, get_cycles):
        get_cycles.return_value = {
            'scambi_diretti': [],
            'catene': [],
            'totale': 0,
            'tempo': 0,
        }
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse('catene_scambio'),
            {'load': 'true', 'annuncio_id': self.request_a_1.id},
        )

        self.assertEqual(response.status_code, 200)
        get_cycles.assert_called_once_with(
            preferred_announcement_id=self.request_a_1.id,
        )
