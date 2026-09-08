import hashlib
import json
import time
from unittest.mock import patch

import cloudinary
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .moderation import get_announcement_by_cloudinary_public_id
from .models import Annuncio, Categoria


class CloudinaryTestDataMixin:
    def setUp(self):
        self.user = User.objects.create_user(
            username='cloudinary_lookup_user',
            email='cloudinary-lookup@example.com',
            password='Password-sicura-2026!',
        )
        self.category = Categoria.objects.create(nome='Cloudinary lookup')

    def create_announcement(self, title, stored_image):
        announcement = Annuncio.objects.create(
            utente=self.user,
            titolo=title,
            descrizione='Descrizione valida',
            categoria=self.category,
            tipo='offro',
        )
        Annuncio.objects.filter(pk=announcement.pk).update(
            immagine=stored_image,
            moderation_status='pending',
        )
        return Annuncio.objects.get(pk=announcement.pk)


class CloudinaryAnnouncementLookupTests(CloudinaryTestDataMixin, TestCase):
    def test_exact_public_id_wins_over_same_filename_in_another_folder(self):
        wrong_announcement = self.create_announcement(
            'Immagine omonima',
            'image/upload/v11/archivio/foto.jpg',
        )
        expected_announcement = self.create_announcement(
            'Immagine corretta',
            'image/upload/v12/annunci/foto.jpg',
        )

        result = get_announcement_by_cloudinary_public_id('annunci/foto')

        self.assertEqual(result.pk, expected_announcement.pk)
        self.assertNotEqual(result.pk, wrong_announcement.pk)

    def test_similar_public_id_is_not_accepted(self):
        self.create_announcement(
            'Immagine simile',
            'image/upload/v20/annunci/foto-estesa.jpg',
        )

        with self.assertRaises(Annuncio.DoesNotExist):
            get_announcement_by_cloudinary_public_id('annunci/foto')

    def test_duplicate_exact_public_id_is_rejected_as_ambiguous(self):
        self.create_announcement(
            'Prima immagine duplicata',
            'image/upload/v30/annunci/duplicata.jpg',
        )
        self.create_announcement(
            'Seconda immagine duplicata',
            'image/upload/v31/annunci/duplicata.png',
        )

        with self.assertRaises(Annuncio.MultipleObjectsReturned):
            get_announcement_by_cloudinary_public_id('annunci/duplicata')

    def test_invalid_public_id_is_rejected_before_querying(self):
        with (
            patch.object(Annuncio.objects, 'filter') as filter_announcements,
            self.assertRaises(ValueError),
        ):
            get_announcement_by_cloudinary_public_id(123)

        filter_announcements.assert_not_called()


class CloudinaryWebhookMappingTests(CloudinaryTestDataMixin, TestCase):
    api_secret = 'cloudinary-webhook-test-secret'

    def signed_post(self, payload):
        body = json.dumps(payload, separators=(',', ':'))
        timestamp = int(time.time())
        signature = hashlib.sha1(
            f'{body}{timestamp}{self.api_secret}'.encode('utf-8')
        ).hexdigest()
        config = cloudinary.config()
        with patch.object(config, 'api_secret', self.api_secret):
            return self.client.post(
                reverse('cloudinary_moderation_webhook'),
                data=body,
                content_type='application/json',
                HTTP_X_CLD_SIGNATURE=signature,
                HTTP_X_CLD_TIMESTAMP=str(timestamp),
            )

    def test_unsigned_webhook_is_rejected_before_asset_lookup(self):
        with patch(
            'scambi.views.get_announcement_by_cloudinary_public_id'
        ) as lookup:
            response = self.client.post(
                reverse('cloudinary_moderation_webhook'),
                data=json.dumps({'public_id': 'annunci/foto'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 401)
        lookup.assert_not_called()

    def test_webhook_moderates_only_the_exact_announcement(self):
        wrong_announcement = self.create_announcement(
            'Webhook immagine omonima',
            'image/upload/v40/archivio/foto.jpg',
        )
        expected_announcement = self.create_announcement(
            'Webhook immagine corretta',
            'image/upload/v41/annunci/foto.jpg',
        )

        def approve_in_memory(announcement, payload):
            announcement.moderation_status = 'approved'

        with patch.object(
            Annuncio,
            'handle_moderation_result',
            autospec=True,
            side_effect=approve_in_memory,
        ) as handle_result:
            response = self.signed_post({
                'public_id': 'annunci/foto',
                'moderation_status': 'approved',
                'moderation': [],
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['annuncio_id'], expected_announcement.pk)
        self.assertEqual(handle_result.call_count, 1)
        handled_announcement = handle_result.call_args.args[0]
        self.assertEqual(handled_announcement.pk, expected_announcement.pk)
        self.assertNotEqual(handled_announcement.pk, wrong_announcement.pk)

    def test_webhook_for_replaced_image_is_ignored(self):
        announcement = self.create_announcement(
            'Immagine sostituita',
            'image/upload/v60/annunci/vecchia.jpg',
        )

        def replace_image_during_lookup(public_id):
            Annuncio.objects.filter(pk=announcement.pk).update(
                immagine='image/upload/v61/annunci/nuova.jpg',
                moderation_status='pending',
            )
            return announcement

        with (
            patch(
                'scambi.views.get_announcement_by_cloudinary_public_id',
                side_effect=replace_image_during_lookup,
            ),
            patch.object(Annuncio, 'handle_moderation_result') as handle_result,
        ):
            response = self.signed_post({
                'public_id': 'annunci/vecchia',
                'moderation_status': 'approved',
                'moderation': [],
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ignored')
        handle_result.assert_not_called()

    def test_ambiguous_mapping_changes_nothing(self):
        self.create_announcement(
            'Webhook duplicata uno',
            'image/upload/v50/annunci/duplicata.jpg',
        )
        self.create_announcement(
            'Webhook duplicata due',
            'image/upload/v51/annunci/duplicata.png',
        )

        with patch.object(Annuncio, 'handle_moderation_result') as handle_result:
            response = self.signed_post({
                'public_id': 'annunci/duplicata',
                'moderation_status': 'rejected',
                'moderation': [],
            })

        self.assertEqual(response.status_code, 409)
        handle_result.assert_not_called()

    def test_non_string_public_id_is_bad_request(self):
        with patch.object(Annuncio, 'handle_moderation_result') as handle_result:
            response = self.signed_post({
                'public_id': 123,
                'moderation_status': 'approved',
            })

        self.assertEqual(response.status_code, 400)
        handle_result.assert_not_called()
