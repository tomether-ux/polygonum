from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from cloudinary import CloudinaryResource
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from .forms import AnnuncioForm
from .models import Annuncio, Categoria, UserProfile, Provincia
from .value_bands import adjacent, common_bands, chain_is_equal


def band(first, second=''):
    return SimpleNamespace(fascia_prezzo=first, fascia_secondaria=second)


class BandLogicTests(SimpleTestCase):
    def test_only_adjacent_second_band(self):
        self.assertTrue(adjacent('v4', 'v5'))
        for first, second in [('v1', 'v7'), ('v4', 'v4'), ('medio', 'v4')]:
            self.assertFalse(adjacent(first, second))

    def test_whole_chain_intersection_not_pairwise(self):
        self.assertEqual(common_bands([band('v3', 'v4'), band('v4', 'v5'), band('v4')]), {'v4'})
        self.assertFalse(common_bands([band('v3', 'v4'), band('v4', 'v5'), band('v5')]))

    def test_missing_band_is_not_equal(self):
        self.assertFalse(common_bands([band(''), band('v4')]))
        self.assertFalse(common_bands([]))

    def test_legacy_values_are_not_reinterpreted(self):
        self.assertEqual(common_bands([band('medio'), band('medio')]), {'medio'})
        self.assertFalse(common_bands([band('medio'), band('v3')]))

    def test_alternatives_require_one_common_band_across_all_edges(self):
        chain = {'scambi_opzioni': [
            {'opzioni': [{'offerta': band('v2')}, {'offerta': band('v4')}]},
            {'opzioni': [{'offerta': band('v4', 'v5')}]},
            {'opzioni': [{'offerta': band('v4')}]},
        ]}
        self.assertTrue(chain_is_equal(chain))
        chain['scambi_opzioni'][2]['opzioni'][0]['offerta'] = band('v6')
        self.assertFalse(chain_is_equal(chain))


class BandWorkflowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='fasce')
        province = Provincia.objects.create(sigla='MI', nome='Milano', regione='Lombardia', latitudine=45.46, longitudine=9.19)
        UserProfile.objects.create(user=self.user, provincia_obj=province)
        self.category = Categoria.objects.create(nome='Strumenti musicali')
        self.client.force_login(self.user)

    def data(self, **extra):
        data = {'titolo': 'Sintetizzatore analogico', 'descrizione': 'Strumento funzionante in ottime condizioni',
                'categoria': self.category.pk, 'tipo': 'cerco', 'fascia_prezzo': 'v5',
                'fascia_secondaria': '', 'condizione': 'buono', 'metodo_scambio': 'entrambi'}
        data.update(extra)
        return data

    def listing(self, **extra):
        data = {'utente': self.user, 'categoria': self.category, 'tipo': 'cerco',
                'titolo': 'Sintetizzatore analogico', 'descrizione': 'Strumento usato', 'fascia_prezzo': 'v5'}
        data.update(extra)
        return Annuncio.objects.create(**data)

    def test_new_offer_requires_photo_wanted_does_not(self):
        form = AnnuncioForm(self.data(tipo='offro'))
        self.assertFalse(form.is_valid())
        self.assertIn('immagine', form.errors)
        wanted = AnnuncioForm(self.data())
        self.assertTrue(wanted.is_valid(), wanted.errors)

    def test_two_bands_without_invented_price(self):
        form = AnnuncioForm(self.data(fascia_secondaria='v6'))
        self.assertTrue(form.is_valid(), form.errors)
        listing = form.save(commit=False)
        self.assertIsNone(listing.prezzo_stimato)
        self.assertEqual(listing.fascia_secondaria, 'v6')
        self.assertNotIn('€', listing.fasce_display)

    def test_non_adjacent_and_duplicate_bands_are_rejected(self):
        for secondary in ['v1', 'v5', 'v7']:
            form = AnnuncioForm(self.data(fascia_secondaria=secondary))
            self.assertFalse(form.is_valid())
            self.assertIn('fascia_secondaria', form.errors)

    def test_old_offer_can_be_edited_without_photo_or_conversion(self):
        item = self.listing(tipo='offro', fascia_prezzo='medio')
        form = AnnuncioForm(self.data(tipo='offro', fascia_prezzo='medio'), instance=item)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().fascia_prezzo, 'medio')

    def test_republish_missing_offer_photo_keeps_it_expired(self):
        item = self.listing(tipo='offro', attivo=False, modifiche_effettuate=3,
                            pubblicato_at=timezone.now() - timedelta(days=61))
        response = self.client.post(reverse('ripubblica_annuncio', args=[item.pk]))
        self.assertContains(response, 'Aggiungi una foto e ripubblica')
        item.refresh_from_db()
        self.assertFalse(item.attivo)
        self.assertTrue(item.is_scaduto)
        self.assertEqual(item.modifiche_effettuate, 3)

    def test_republish_photo_follows_moderation_without_consuming_edits(self):
        item = self.listing(tipo='offro', attivo=False, modifiche_effettuate=3,
                            pubblicato_at=timezone.now() - timedelta(days=61))
        with patch('scambi.forms.FotoRipubblicazioneForm.clean_immagine', return_value=CloudinaryResource('annunci/test-upload')), patch.object(Annuncio, 'trigger_moderation'):
            response = self.client.post(reverse('ripubblica_annuncio', args=[item.pk]))
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertFalse(item.is_scaduto)
        self.assertEqual(item.moderation_status, 'pending')
        self.assertEqual(item.modifiche_effettuate, 3)

    def test_photo_priority_is_disabled_by_filters(self):
        photo = self.listing(titolo='Richiesta con immagine', pubblicato_at=timezone.now() - timedelta(days=1))
        Annuncio.objects.filter(pk=photo.pk).update(immagine='annunci/test', moderation_status='approved')
        no_photo = self.listing(titolo='Richiesta senza immagine')
        response = self.client.get(reverse('lista_annunci'))
        self.assertEqual(list(response.context['annunci']), [photo, no_photo])
        response = self.client.get(reverse('lista_annunci'), {'categoria': self.category.pk})
        self.assertEqual(list(response.context['annunci']), [no_photo, photo])
        response = self.client.get(reverse('home'))
        self.assertEqual(list(response.context['annunci_recenti']), [photo])
        self.assertEqual(list(response.context['richieste_senza_foto']), [no_photo])

    def test_guide_and_category_placeholder(self):
        self.assertEqual(self.category.placeholder_icon, 'music')
        self.assertContains(self.client.get(reverse('guida_valore')), '400–900')
