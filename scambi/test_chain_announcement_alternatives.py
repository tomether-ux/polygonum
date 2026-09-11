from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import connection
from django.template.loader import render_to_string
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .matching import (
    converti_ciclo_db_a_view_format,
    estrai_annunci_ids_dettagli,
    get_cicli_precalcolati,
)
from .models import Annuncio, Categoria, CatenaPreferita, CicloScambio
from .views import genera_hash_catena


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
        self.assertIn(f'nascondiCatena({self.cycle.id}, event)', html)

    @patch('scambi.views.CicloScambio.find_for_user')
    def test_personal_page_finds_an_announcement_stored_as_alternative(self, find_for_user):
        find_for_user.return_value = CicloScambio.objects.filter(
            pk=self.cycle.pk,
        )
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
            'totale_disponibili': 0,
            'totali_per_lunghezza': {length: 0 for length in range(2, 7)},
            'pagina': None,
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
            user_id=self.user_a.id,
            page=None,
            page_size=None,
            focus_cycle_id=None,
            cycle_length=None,
            per_length_limit=20,
        )

    @patch('scambi.matching.get_cicli_precalcolati')
    def test_main_page_marks_favorites_without_per_chain_queries(self, get_cycles):
        chain = self._convert()
        chain_hash = genera_hash_catena(chain)
        user_c = User.objects.create_user(
            username='alternative_c',
            email='alternative-c@example.com',
            password='Password-sicura-2026!',
        )
        second_chain = self._convert()
        second_chain['utenti'] = [
            dict(user_data) for user_data in second_chain['utenti']
        ]
        second_chain['utenti'][1]['user'] = user_c
        CatenaPreferita.objects.create(
            utente=self.user_a,
            catena_hash=chain_hash,
            catena_data={'id_ciclo': str(self.cycle.id)},
            tipo_catena='scambio_diretto',
            categoria_qualita='generica',
        )
        get_cycles.return_value = {
            'scambi_diretti': [chain, second_chain],
            'catene': [],
            'totale': 2,
            'totale_disponibili': 2,
            'totali_per_lunghezza': {
                length: 2 * int(length == 2) for length in range(2, 7)
            },
            'pagina': None,
            'tempo': 0,
        }
        self.client.force_login(self.user_a)

        with CaptureQueriesContext(connection) as captured_queries:
            response = self.client.get(
                reverse('catene_scambio'),
                {'load': 'true'},
            )

        self.assertEqual(response.status_code, 200)
        favorite_queries = [
            query for query in captured_queries
            if 'scambi_catenapreferita' in query['sql'].lower()
        ]
        self.assertEqual(len(favorite_queries), 1)

        displayed_chains = response.context['catene_specifiche']
        self.assertEqual(len(displayed_chains), 2)
        favorite_chain = next(
            item for item in displayed_chains
            if item['hash_catena'] == chain_hash
        )
        self.assertTrue(favorite_chain['is_favorita'])

    @patch('scambi.matching.get_cicli_precalcolati')
    def test_main_page_applies_closed_length_and_page_size_filters(
        self,
        get_cycles,
    ):
        get_cycles.return_value = {
            'scambi_diretti': [],
            'catene': [],
            'totale': 0,
            'totale_disponibili': 0,
            'totali_per_lunghezza': {length: 0 for length in range(2, 7)},
            'pagina': None,
            'tempo': 0,
        }
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse('catene_scambio'),
            {
                'load': 'true',
                'lunghezza': '6',
                'per_page': '100',
                'page': '2',
            },
        )

        self.assertEqual(response.status_code, 200)
        get_cycles.assert_called_once_with(
            preferred_announcement_id=None,
            user_id=self.user_a.id,
            page='2',
            page_size=100,
            focus_cycle_id=None,
            cycle_length=6,
            per_length_limit=None,
        )
        self.assertEqual(response.context['tipo_catena_selezionato'], 6)
        self.assertEqual(response.context['catene_per_pagina'], 100)

    @patch('scambi.matching.get_cicli_precalcolati')
    def test_main_page_rejects_arbitrary_filter_limits(self, get_cycles):
        get_cycles.return_value = {
            'scambi_diretti': [],
            'catene': [],
            'totale': 0,
            'totale_disponibili': 0,
            'totali_per_lunghezza': {length: 0 for length in range(2, 7)},
            'pagina': None,
            'tempo': 0,
        }
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse('catene_scambio'),
            {'load': 'true', 'lunghezza': '999', 'per_page': '1000000'},
        )

        self.assertEqual(response.status_code, 200)
        get_cycles.assert_called_once_with(
            preferred_announcement_id=None,
            user_id=self.user_a.id,
            page=None,
            page_size=None,
            focus_cycle_id=None,
            cycle_length=None,
            per_length_limit=20,
        )
        self.assertIsNone(response.context['tipo_catena_selezionato'])
        self.assertEqual(response.context['catene_per_pagina'], 50)


class PersonalCycleLoadingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cycle_owner',
            email='cycle-owner@example.com',
            password='Password-sicura-2026!',
        )
        self.user_b = User.objects.create_user(
            username='cycle_b',
            email='cycle-b@example.com',
            password='Password-sicura-2026!',
        )
        self.user_c = User.objects.create_user(
            username='cycle_c',
            email='cycle-c@example.com',
            password='Password-sicura-2026!',
        )
        self.unrelated_a = User.objects.create_user(
            username='cycle_unrelated_a',
            email='cycle-unrelated-a@example.com',
            password='Password-sicura-2026!',
        )
        self.unrelated_b = User.objects.create_user(
            username='cycle_unrelated_b',
            email='cycle-unrelated-b@example.com',
            password='Password-sicura-2026!',
        )

        self.first_cycle = self._cycle(
            [self.user.id, self.user_b.id],
            'd' * 32,
            announcement_id=101,
        )
        self.second_cycle = self._cycle(
            [self.user.id, self.user_c.id],
            'e' * 32,
            announcement_id=202,
        )
        self._cycle(
            [self.unrelated_a.id, self.unrelated_b.id],
            'f' * 32,
            announcement_id=303,
        )

    @staticmethod
    def _details(announcement_id):
        return {
            'scambi': [
                {
                    'oggetti': [
                        {
                            'offerto': {'id': announcement_id},
                            'richiesto': {'id': announcement_id + 1},
                        }
                    ]
                }
            ]
        }

    def _cycle(self, users, cycle_hash, announcement_id):
        return CicloScambio.objects.create(
            users=users,
            lunghezza=len(users),
            dettagli=self._details(announcement_id),
            valido=True,
            hash_ciclo=cycle_hash,
        )

    def test_find_for_user_matches_integer_json_ids_exactly(self):
        cycles = list(CicloScambio.find_for_user(self.user.id, limit=None))

        self.assertEqual(
            {cycle.id for cycle in cycles},
            {self.first_cycle.id, self.second_cycle.id},
        )

    @patch('scambi.matching.converti_ciclo_db_a_view_format')
    def test_personal_cycles_are_filtered_and_paginated_before_conversion(
        self,
        convert_cycle,
    ):
        convert_cycle.side_effect = lambda cycle, *args, **kwargs: {
            'id_ciclo': str(cycle.id),
            'lunghezza': cycle.lunghezza,
            'utenti': [],
        }

        result = get_cicli_precalcolati(
            user_id=self.user.id,
            page=1,
            page_size=1,
        )

        self.assertEqual(result['totale_disponibili'], 2)
        self.assertEqual(result['pagina'].paginator.num_pages, 2)
        self.assertEqual(result['totale'], 1)
        self.assertEqual(convert_cycle.call_count, 1)

    @patch('scambi.matching.converti_ciclo_db_a_view_format')
    def test_announcement_filter_runs_before_pagination(self, convert_cycle):
        convert_cycle.side_effect = lambda cycle, *args, **kwargs: {
            'id_ciclo': str(cycle.id),
            'lunghezza': cycle.lunghezza,
            'utenti': [],
        }

        result = get_cicli_precalcolati(
            preferred_announcement_id=202,
            user_id=self.user.id,
            page=1,
            page_size=1,
        )

        loaded = result['scambi_diretti'] + result['catene']
        self.assertEqual(result['totale_disponibili'], 1)
        self.assertEqual([item['id_ciclo'] for item in loaded], [
            str(self.second_cycle.id),
        ])

    @patch('scambi.matching.converti_ciclo_db_a_view_format')
    def test_notification_focus_opens_the_page_containing_the_cycle(
        self,
        convert_cycle,
    ):
        convert_cycle.side_effect = lambda cycle, *args, **kwargs: {
            'id_ciclo': str(cycle.id),
            'lunghezza': cycle.lunghezza,
            'utenti': [],
        }

        result = get_cicli_precalcolati(
            user_id=self.user.id,
            page_size=1,
            focus_cycle_id=self.first_cycle.id,
        )

        loaded = result['scambi_diretti'] + result['catene']
        self.assertEqual([item['id_ciclo'] for item in loaded], [
            str(self.first_cycle.id),
        ])

    @patch('scambi.matching.converti_ciclo_db_a_view_format')
    def test_balanced_loading_limits_each_cycle_length_separately(
        self,
        convert_cycle,
    ):
        for index in range(23):
            self._cycle(
                [self.user.id, 1000 + index],
                f'balanced-two-{index}',
                announcement_id=1000 + index,
            )
        for index in range(22):
            self._cycle(
                [self.user.id, *range(2000 + index * 5, 2005 + index * 5)],
                f'balanced-six-{index}',
                announcement_id=2000 + index,
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
        loaded_per_length = {
            length: sum(item['lunghezza'] == length for item in loaded)
            for length in range(2, 7)
        }

        self.assertEqual(result['totale_disponibili'], 47)
        self.assertEqual(result['totali_per_lunghezza'][2], 25)
        self.assertEqual(result['totali_per_lunghezza'][6], 22)
        self.assertEqual(loaded_per_length[2], 20)
        self.assertEqual(loaded_per_length[6], 20)
        self.assertEqual(result['totale'], 40)
        self.assertIsNone(result['pagina'])

    @patch('scambi.matching.converti_ciclo_db_a_view_format')
    def test_balanced_loading_keeps_a_notification_cycle_visible(
        self,
        convert_cycle,
    ):
        for index in range(23):
            self._cycle(
                [self.user.id, 3000 + index],
                f'focus-two-{index}',
                announcement_id=3000 + index,
            )

        convert_cycle.side_effect = lambda cycle, *args, **kwargs: {
            'id_ciclo': str(cycle.id),
            'lunghezza': cycle.lunghezza,
            'utenti': [],
        }

        result = get_cicli_precalcolati(
            user_id=self.user.id,
            per_length_limit=20,
            focus_cycle_id=self.first_cycle.id,
        )
        loaded = result['scambi_diretti'] + result['catene']

        self.assertEqual(len(loaded), 20)
        self.assertIn(
            str(self.first_cycle.id),
            {item['id_ciclo'] for item in loaded},
        )
