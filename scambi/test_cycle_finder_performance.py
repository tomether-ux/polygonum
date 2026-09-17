from django.contrib.auth.models import User
from django.test import TestCase

from .matching import CycleFinder
from .models import Annuncio, Categoria


class CycleFinderPreloadingTests(TestCase):
    def setUp(self):
        self.category = Categoria.objects.create(nome='Strumenti')
        self.first_user = User.objects.create_user(username='primo')
        self.second_user = User.objects.create_user(username='secondo')

        Annuncio.objects.create(
            utente=self.first_user,
            titolo='Pianoforte digitale',
            descrizione='Offerta valida',
            categoria=self.category,
            tipo='offro',
        )
        Annuncio.objects.create(
            utente=self.first_user,
            titolo='Chitarra elettrica',
            descrizione='Richiesta valida',
            categoria=self.category,
            tipo='cerco',
        )
        Annuncio.objects.create(
            utente=self.second_user,
            titolo='Chitarra elettrica',
            descrizione='Offerta valida',
            categoria=self.category,
            tipo='offro',
        )
        Annuncio.objects.create(
            utente=self.second_user,
            titolo='Pianoforte digitale',
            descrizione='Richiesta valida',
            categoria=self.category,
            tipo='cerco',
        )

    def test_graph_is_built_with_one_announcement_query(self):
        finder = CycleFinder()

        with self.assertNumQueries(1):
            finder.costruisci_grafo()

        self.assertEqual(
            finder.grafo,
            {
                self.first_user.id: [self.second_user.id],
                self.second_user.id: [self.first_user.id],
            },
        )

    def test_cycle_details_reuse_preloaded_announcements(self):
        finder = CycleFinder()
        finder.costruisci_grafo()

        with self.assertNumQueries(0):
            details = finder._get_dettagli_ciclo([
                self.first_user.id,
                self.second_user.id,
            ])
            cached_details = finder._get_dettagli_ciclo([
                self.first_user.id,
                self.second_user.id,
            ])

        self.assertEqual(len(details['scambi']), 2)
        self.assertEqual(len(cached_details['scambi']), 2)
