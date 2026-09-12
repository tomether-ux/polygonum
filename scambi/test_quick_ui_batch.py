from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser, User
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .conversation_services import get_conversation_display
from .forms import RicercaAvanzataForm
from .models import (
    Annuncio,
    Categoria,
    CicloScambio,
    Conversazione,
    Provincia,
    UserProfile,
)


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


class ProfileAndConversationUiTests(TestCase):
    def setUp(self):
        self.province = Provincia.objects.create(
            sigla='MI',
            nome='Milano',
            regione='Lombardia',
            latitudine=45.4642,
            longitudine=9.190,
        )
        self.user = self._create_user('utente_ui')
        self.other_user = self._create_user('altro_utente_ui')
        self.category = Categoria.objects.create(nome='Strumenti musicali')

    def _create_user(self, username):
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='Password-sicura-2026!',
        )
        UserProfile.objects.create(
            user=user,
            provincia_obj=self.province,
            citta='Milano',
        )
        return user

    def test_profile_has_collapsible_compact_offer_and_request_sections(self):
        Annuncio.objects.create(
            utente=self.user,
            titolo='Sintetizzatore',
            descrizione='Descrizione sintetizzatore',
            categoria=self.category,
            tipo='offro',
            attivo=True,
        )
        request_announcement = Annuncio.objects.create(
            utente=self.user,
            titolo='Chitarra elettrica',
            descrizione='Descrizione chitarra',
            categoria=self.category,
            tipo='cerco',
            attivo=True,
        )
        Annuncio.objects.filter(pk=request_announcement.pk).update(
            immagine='annunci/foto-test.jpg',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse(
            'profilo_utente',
            kwargs={'username': self.user.username},
        ))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bs-target="#profileOffers"')
        self.assertContains(response, 'data-bs-target="#profileRequests"')
        self.assertContains(response, 'aria-label="Foto presente"')
        self.assertContains(response, 'aria-label="Nessuna foto"')

    def test_group_chat_name_describes_chain_and_current_user_exchange(self):
        cycle = CicloScambio.objects.create(
            users=[self.user.id, self.other_user.id],
            lunghezza=2,
            dettagli={
                'utenti': [
                    {
                        'user': {'id': self.user.id},
                        'offerta': {'id': 10, 'titolo': 'Sintetizzatore'},
                        'richiede': {'id': 11, 'titolo': 'Chitarra elettrica'},
                    },
                    {
                        'user': {'id': self.other_user.id},
                        'offerta': {'id': 11, 'titolo': 'Chitarra elettrica'},
                        'richiede': {'id': 10, 'titolo': 'Sintetizzatore'},
                    },
                ],
            },
            valido=True,
            hash_ciclo='conversation-ui-cycle',
        )
        conversation = Conversazione.objects.create(
            tipo='gruppo',
            nome=f'Catena di scambio #{cycle.pk}',
            catena_scambio_id=str(cycle.pk),
        )
        conversation.utenti.set([self.user, self.other_user])

        display = get_conversation_display(conversation, self.user)

        self.assertEqual(display['nome'], 'Scambio diretto')
        self.assertEqual(
            display['scambio'],
            'Offri: Sintetizzatore · Cerchi: Chitarra elettrica',
        )

        self.client.force_login(self.user)
        list_response = self.client.get(reverse('lista_messaggi'))
        chat_response = self.client.get(reverse(
            'chat_conversazione',
            kwargs={'conversazione_id': conversation.pk},
        ))

        self.assertContains(list_response, 'Scambio diretto')
        self.assertContains(list_response, 'Offri: Sintetizzatore')
        self.assertContains(chat_response, 'Scambio diretto')
        self.assertContains(chat_response, 'Cerchi: Chitarra elettrica')

    def test_legacy_group_with_same_numeric_id_keeps_its_name(self):
        cycle = CicloScambio.objects.create(
            users=[self.user.id, self.other_user.id],
            lunghezza=2,
            dettagli={'utenti': []},
            valido=True,
            hash_ciclo='legacy-conversation-id-collision',
        )
        conversation = Conversazione.objects.create(
            tipo='gruppo',
            nome='Gruppo storico',
            catena_scambio_id=str(cycle.pk),
        )
        conversation.utenti.set([self.user, self.other_user])

        display = get_conversation_display(conversation, self.user)

        self.assertEqual(display['nome'], 'Gruppo storico')
        self.assertEqual(display['scambio'], '')
        self.assertIsNone(display['ciclo'])
