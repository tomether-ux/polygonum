from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import AnnuncioForm
from .models import Annuncio, Categoria, Provincia, UserProfile


class AnnouncementLimitTests(TestCase):
    def setUp(self):
        self.province = Provincia.objects.create(
            sigla='MI',
            nome='Milano',
            regione='Lombardia',
            latitudine=45.4642,
            longitudine=9.1900,
        )
        self.user = User.objects.create_user(
            username='annunci_limitati',
            email='annunci-limitati@example.com',
            password='Password-sicura-2026!',
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            provincia_obj=self.province,
            citta='Milano',
        )
        self.category = Categoria.objects.create(nome='Strumenti musicali')
        self.client.force_login(self.user)

    def form_data(self, **overrides):
        data = {
            'titolo': 'Chitarra elettrica Fender',
            'descrizione': 'Descrizione completa dell’oggetto',
            'categoria': str(self.category.pk),
            'tipo': 'offro',
            'fascia_prezzo': 'medio',
            'condizione': 'usato',
            'metodo_scambio': 'entrambi',
            'distanza_massima_km': '',
        }
        data.update(overrides)
        return data

    def create_announcement(self, **overrides):
        values = {
            'utente': self.user,
            'titolo': 'Chitarra elettrica Fender',
            'descrizione': 'Descrizione completa dell’oggetto',
            'categoria': self.category,
            'tipo': 'offro',
            'fascia_prezzo': 'medio',
            'condizione': 'usato',
            'metodo_scambio': 'entrambi',
            'attivo': True,
        }
        values.update(overrides)
        return Annuncio.objects.create(**values)

    def test_title_is_limited_to_sixty_characters_and_eight_words(self):
        too_long = AnnuncioForm(self.form_data(titolo='A' * 61))
        too_many_words = AnnuncioForm(self.form_data(
            titolo='uno due tre quattro cinque sei sette otto nove',
        ))
        valid = AnnuncioForm(self.form_data(
            titolo='uno due tre quattro cinque sei sette otto',
        ))

        self.assertFalse(too_long.is_valid())
        self.assertIn('massimo 60 caratteri', too_long.errors['titolo'][0])
        self.assertFalse(too_many_words.is_valid())
        self.assertIn('massimo 8 parole', too_many_words.errors['titolo'][0])
        self.assertTrue(valid.is_valid(), valid.errors)

    def test_standard_account_cannot_create_a_fourth_active_offer(self):
        for index in range(3):
            self.create_announcement(titolo=f'Offerta numero {index}')

        response = self.client.post(
            reverse('crea_annuncio'),
            self.form_data(titolo='Quarta offerta'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.profile.get_limite_annunci('offro'), 3)
        self.assertEqual(
            Annuncio.objects.filter(
                utente=self.user,
                tipo='offro',
                attivo=True,
            ).count(),
            3,
        )
        self.assertContains(response, '3/3')

    def test_three_successful_edits_lock_the_announcement(self):
        announcement = self.create_announcement()

        for edit_number in range(1, 4):
            response = self.client.post(
                reverse('modifica_annuncio', args=[announcement.pk]),
                self.form_data(descrizione=f'Descrizione modificata {edit_number}'),
            )
            self.assertRedirects(
                response,
                reverse('profilo_utente', kwargs={'username': self.user.username}),
                fetch_redirect_response=False,
            )
            announcement.refresh_from_db()
            self.assertEqual(announcement.modifiche_effettuate, edit_number)

        response = self.client.get(
            reverse('modifica_annuncio', args=[announcement.pk]),
        )

        self.assertRedirects(
            response,
            reverse('profilo_utente', kwargs={'username': self.user.username}),
            fetch_redirect_response=False,
        )
        self.assertFalse(announcement.puo_essere_modificato)
        self.assertEqual(announcement.modifiche_rimanenti, 0)

    def test_unchanged_form_does_not_consume_an_edit(self):
        announcement = self.create_announcement()

        response = self.client.post(
            reverse('modifica_annuncio', args=[announcement.pk]),
            self.form_data(),
        )

        self.assertRedirects(
            response,
            reverse('profilo_utente', kwargs={'username': self.user.username}),
            fetch_redirect_response=False,
        )
        announcement.refresh_from_db()
        self.assertEqual(announcement.modifiche_effettuate, 0)

    def test_existing_announcements_over_new_limit_are_not_deleted(self):
        for index in range(4):
            self.create_announcement(titolo=f'Annuncio esistente {index}')

        can_create, _ = self.profile.puo_creare_annuncio('offro')

        self.assertFalse(can_create)
        self.assertEqual(Annuncio.objects.filter(utente=self.user).count(), 4)

    def test_changing_type_cannot_overflow_target_limit(self):
        for index in range(3):
            self.create_announcement(
                titolo=f'Richiesta numero {index}',
                tipo='cerco',
            )
        offer = self.create_announcement(titolo='Offerta da cambiare')

        response = self.client.post(
            reverse('modifica_annuncio', args=[offer.pk]),
            self.form_data(tipo='cerco', titolo=offer.titolo),
        )

        self.assertEqual(response.status_code, 200)
        offer.refresh_from_db()
        self.assertEqual(offer.tipo, 'offro')
        self.assertEqual(offer.modifiche_effettuate, 0)
        self.assertContains(response, 'Hai già 3 annunci attivi di questo tipo')

    def test_inactive_announcement_cannot_be_reactivated_over_limit(self):
        for index in range(3):
            self.create_announcement(titolo=f'Offerta attiva {index}')
        inactive = self.create_announcement(
            titolo='Offerta non attiva',
            attivo=False,
        )

        response = self.client.post(
            reverse('attiva_annuncio', args=[inactive.pk]),
        )

        self.assertRedirects(
            response,
            reverse('profilo_utente', kwargs={'username': self.user.username}),
            fetch_redirect_response=False,
        )
        inactive.refresh_from_db()
        self.assertFalse(inactive.attivo)
