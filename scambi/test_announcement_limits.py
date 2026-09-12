from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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

    def test_expired_active_announcement_does_not_consume_active_limit(self):
        expired = self.create_announcement(titolo='Annuncio scaduto non contato')
        Annuncio.objects.filter(pk=expired.pk).update(
            pubblicato_at=timezone.now() - timedelta(days=61),
        )
        for index in range(2):
            self.create_announcement(titolo=f'Offerta recente {index}')

        can_create, _ = self.profile.puo_creare_annuncio('offro')

        self.assertTrue(can_create)
        self.assertEqual(self.profile.get_count_annunci('offro'), 2)

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

    def test_expired_announcement_can_be_republished_for_sixty_days(self):
        old_publication = timezone.now() - timedelta(days=61)
        announcement = self.create_announcement(
            titolo='Annuncio da ripubblicare',
            attivo=False,
            modifiche_effettuate=3,
        )
        Annuncio.objects.filter(pk=announcement.pk).update(
            pubblicato_at=old_publication,
            scaduto_at=timezone.now() - timedelta(days=1),
        )

        response = self.client.post(
            reverse('ripubblica_annuncio', args=[announcement.pk]),
        )

        self.assertRedirects(
            response,
            reverse('profilo_utente', kwargs={'username': self.user.username}),
            fetch_redirect_response=False,
        )
        announcement.refresh_from_db()
        self.assertTrue(announcement.attivo)
        self.assertIsNone(announcement.scaduto_at)
        self.assertGreater(announcement.pubblicato_at, old_publication)
        self.assertEqual(announcement.modifiche_effettuate, 3)
        self.assertEqual(announcement.giorni_alla_scadenza, 60)

    def test_republication_respects_three_active_listings_limit(self):
        for index in range(3):
            self.create_announcement(titolo=f'Offerta attiva {index}')
        expired = self.create_announcement(
            titolo='Offerta scaduta',
            attivo=False,
        )
        Annuncio.objects.filter(pk=expired.pk).update(
            pubblicato_at=timezone.now() - timedelta(days=61),
            scaduto_at=timezone.now(),
        )

        response = self.client.post(
            reverse('ripubblica_annuncio', args=[expired.pk]),
        )

        self.assertRedirects(
            response,
            reverse('profilo_utente', kwargs={'username': self.user.username}),
            fetch_redirect_response=False,
        )
        expired.refresh_from_db()
        self.assertFalse(expired.attivo)
        self.assertIsNotNone(expired.scaduto_at)

    def test_expired_active_listing_is_hidden_from_public_pages(self):
        expired = self.create_announcement(titolo='Offerta scaduta pubblica')
        Annuncio.objects.filter(pk=expired.pk).update(
            pubblicato_at=timezone.now() - timedelta(days=61),
        )
        self.client.logout()

        list_response = self.client.get(reverse('lista_annunci'))
        detail_response = self.client.get(
            reverse('dettaglio_annuncio', args=[expired.pk]),
        )

        self.assertNotContains(list_response, expired.titolo)
        self.assertEqual(detail_response.status_code, 404)

    def test_rejected_listing_cannot_be_activated_or_republished(self):
        rejected = self.create_announcement(
            titolo='Annuncio bloccato',
            attivo=False,
        )
        Annuncio.objects.filter(pk=rejected.pk).update(
            pubblicato_at=timezone.now() - timedelta(days=61),
            scaduto_at=timezone.now(),
            moderation_status='rejected',
            attivo=False,
        )

        self.client.post(reverse('attiva_annuncio', args=[rejected.pk]))
        self.client.post(reverse('ripubblica_annuncio', args=[rejected.pk]))

        rejected.refresh_from_db()
        self.assertFalse(rejected.attivo)
        self.assertEqual(rejected.moderation_status, 'rejected')
