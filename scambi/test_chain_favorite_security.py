import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import CatenaPreferita, CicloScambio
from .views import _canonical_chain_favorite, processa_catene_preferite


class ChainFavoriteSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='preferiti_partecipante',
            email='preferiti-partecipante@example.com',
            password='Password-sicura-2026!',
        )
        self.other_participant = User.objects.create_user(
            username='preferiti_altro',
            email='preferiti-altro@example.com',
            password='Password-sicura-2026!',
        )
        self.outsider = User.objects.create_user(
            username='preferiti_estraneo',
            email='preferiti-estraneo@example.com',
            password='Password-sicura-2026!',
        )
        self.cycle = CicloScambio.objects.create(
            users=[self.user.id, self.other_participant.id],
            lunghezza=2,
            dettagli={},
            valido=True,
            hash_ciclo='a' * 32,
        )
        _, self.expected_hash = _canonical_chain_favorite(self.cycle)
        self.url = reverse('aggiungi_catena_preferita')
        self.client.force_login(self.user)

    def payload(self, **overrides):
        payload = {
            'catena_hash': self.expected_hash,
            'catena_data': {
                'id_ciclo': self.cycle.id,
                'utenti': ['dato inventato dal browser'],
                'tipo': 'valore_non_valido',
                'campo_inatteso': '<script>non deve essere salvato</script>',
            },
        }
        payload.update(overrides)
        return payload

    def post_json(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_valid_request_saves_only_server_side_snapshot(self):
        response = self.post_json(self.payload())

        favorite = CatenaPreferita.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['action'], 'added')
        self.assertEqual(favorite.catena_hash, self.expected_hash)
        self.assertEqual(favorite.tipo_catena, 'scambio_diretto')
        self.assertEqual(favorite.catena_data['id_ciclo'], str(self.cycle.id))
        self.assertNotIn('campo_inatteso', favorite.catena_data)
        self.assertNotIn(
            'dato inventato dal browser',
            json.dumps(favorite.catena_data),
        )
        self.assertIn(self.user.username, json.dumps(favorite.catena_data))

    def test_outsider_cannot_save_another_users_cycle(self):
        self.client.force_login(self.outsider)

        response = self.post_json(self.payload())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(CatenaPreferita.objects.count(), 0)

    def test_hash_mismatch_is_rejected(self):
        response = self.post_json(self.payload(catena_hash='0' * 32))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CatenaPreferita.objects.count(), 0)

    def test_server_cycle_hash_remains_compatible(self):
        response = self.post_json(
            self.payload(catena_hash=self.cycle.hash_ciclo)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['action'], 'added')
        self.assertEqual(
            CatenaPreferita.objects.get().catena_hash,
            self.expected_hash,
        )

    def test_form_encoded_client_remains_compatible(self):
        response = self.client.post(
            self.url,
            data={
                'catena_hash': self.expected_hash,
                'catena_data': json.dumps({
                    'id_ciclo': self.cycle.id,
                }),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['action'], 'added')

    def test_malformed_hash_and_non_object_json_are_rejected(self):
        malformed_hash = self.post_json(self.payload(catena_hash='../invalid'))
        list_payload = self.post_json(['not', 'an', 'object'])

        self.assertEqual(malformed_hash.status_code, 400)
        self.assertEqual(list_payload.status_code, 400)
        self.assertEqual(CatenaPreferita.objects.count(), 0)

    def test_oversized_request_is_rejected(self):
        oversized = {
            'catena_data': {
                'id_ciclo': self.cycle.id,
                'padding': 'x' * (64 * 1024),
            }
        }

        response = self.post_json(oversized)

        self.assertEqual(response.status_code, 413)
        self.assertEqual(CatenaPreferita.objects.count(), 0)

    def test_existing_favorite_can_be_removed_after_cycle_is_invalid(self):
        canonical_data, _ = _canonical_chain_favorite(self.cycle)
        favorite = CatenaPreferita.objects.create(
            utente=self.user,
            catena_hash=self.expected_hash,
            catena_data=canonical_data,
            tipo_catena='scambio_diretto',
            categoria_qualita='generica',
        )
        self.cycle.valido = False
        self.cycle.save(update_fields=['valido'])

        response = self.post_json({'catena_hash': self.expected_hash})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['action'], 'removed')
        self.assertFalse(CatenaPreferita.objects.filter(pk=favorite.pk).exists())

    def test_limit_blocks_new_favorites_but_not_removal(self):
        CatenaPreferita.objects.create(
            utente=self.user,
            catena_hash='1' * 32,
            catena_data={'id_ciclo': 'legacy'},
            tipo_catena='catena_lunga',
            categoria_qualita='generica',
        )

        with patch('scambi.views.MAX_CHAIN_FAVORITES_PER_USER', 1):
            response = self.post_json(self.payload())

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CatenaPreferita.objects.count(), 1)

    def test_invalid_saved_data_is_ignored_without_database_deletion(self):
        favorite = CatenaPreferita.objects.create(
            utente=self.user,
            catena_hash='2' * 32,
            catena_data='not-json',
            tipo_catena='catena_lunga',
            categoria_qualita='generica',
        )

        processed = processa_catene_preferite([favorite])

        self.assertEqual(processed, [])
        self.assertTrue(CatenaPreferita.objects.filter(pk=favorite.pk).exists())
