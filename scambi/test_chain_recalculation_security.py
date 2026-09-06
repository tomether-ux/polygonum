from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Annuncio, Categoria, CicloScambio


class ChainRecalculationSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ricalcolo_utente',
            email='ricalcolo-utente@example.com',
            password='Password-sicura-2026!',
        )
        other_user = User.objects.create_user(
            username='ricalcolo_altro',
            email='ricalcolo-altro@example.com',
            password='Password-sicura-2026!',
        )
        category = Categoria.objects.create(nome='Ricalcolo sicuro')
        Annuncio.objects.create(
            utente=self.user,
            titolo='Oggetto per test ricalcolo',
            descrizione='Descrizione valida',
            categoria=category,
            tipo='offro',
            attivo=True,
        )
        self.cycle = CicloScambio.objects.create(
            users=[self.user.id, other_user.id],
            lunghezza=2,
            dettagli={},
            valido=True,
            hash_ciclo='b' * 32,
        )
        self.client.force_login(self.user)

    @patch('scambi.matching.CycleFinder')
    @patch('scambi.matching.get_cicli_precalcolati')
    def test_legacy_recalculate_parameter_only_loads_saved_cycles(
        self,
        get_precalculated,
        cycle_finder,
    ):
        get_precalculated.return_value = {
            'scambi_diretti': [],
            'catene': [],
            'totale': 0,
            'tempo': 0,
        }

        response = self.client.get(
            reverse('catene_scambio'),
            {'ricalcola': 'true'},
        )

        self.assertEqual(response.status_code, 200)
        cycle_finder.assert_not_called()
        get_precalculated.assert_called_once_with()
        self.cycle.refresh_from_db()
        self.assertTrue(self.cycle.valido)
        self.assertEqual(CicloScambio.objects.count(), 1)

    @patch('scambi.matching.trova_catene_per_annuncio_ottimizzato')
    @patch('scambi.matching.trova_scambi_diretti_ottimizzato')
    def test_legacy_search_parameter_does_not_start_matching(
        self,
        direct_matching,
        announcement_matching,
    ):
        response = self.client.get(
            reverse('le_mie_catene'),
            {'cerca': 'true'},
        )

        self.assertEqual(response.status_code, 200)
        direct_matching.assert_not_called()
        announcement_matching.assert_not_called()
        self.cycle.refresh_from_db()
        self.assertTrue(self.cycle.valido)
        self.assertEqual(CicloScambio.objects.count(), 1)
