from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .forms import RicercaAvanzataForm


class QuickUiBatchTests(SimpleTestCase):
    def test_advanced_search_exposes_only_the_price_band(self):
        form = RicercaAvanzataForm()

        self.assertIn('fascia_prezzo', form.fields)
        self.assertNotIn('prezzo_min', form.fields)
        self.assertNotIn('prezzo_max', form.fields)
        self.assertNotIn('prezzo_stimato', dict(form.fields['ordinamento'].choices))
        self.assertNotIn('-prezzo_stimato', dict(form.fields['ordinamento'].choices))

    def test_base_template_contains_one_global_chain_loader_and_favicon(self):
        html = render_to_string(
            'scambi/base.html',
            {'user': AnonymousUser()},
        )

        self.assertEqual(html.count('id="polygonumLoadingOverlay"'), 1)
        self.assertIn('/static/img/favicon.svg', html)
        self.assertIn('Caricamento catene in corso', html)

    def test_announcement_card_displays_offer_or_request_badge(self):
        profile = SimpleNamespace(provincia_obj=None, citta='')
        user = SimpleNamespace(
            username='utente-test',
            userprofile=profile,
        )
        common_data = {
            'id': 1,
            'titolo': 'Oggetto di prova',
            'descrizione': 'Descrizione',
            'categoria': SimpleNamespace(nome='Categoria'),
            'utente': user,
            'immagine': None,
            'moderation_status': 'approved',
            'fascia_prezzo': 'medio',
            'get_fascia_prezzo_display': lambda: 'Medio (€50-150)',
        }

        offer_html = render_to_string(
            'scambi/partials/annuncio_card.html',
            {'annuncio': SimpleNamespace(tipo='offro', **common_data)},
        )
        request_html = render_to_string(
            'scambi/partials/annuncio_card.html',
            {'annuncio': SimpleNamespace(tipo='cerco', **common_data)},
        )

        self.assertIn('Offro', offer_html)
        self.assertIn('Cerco', request_html)
