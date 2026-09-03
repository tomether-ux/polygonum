from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from .models import Annuncio, Categoria, Notifica, Provincia, UserProfile
from .moderation import approve_announcement, reject_announcement


class AtomicModerationTests(TestCase):
    def setUp(self):
        provincia = Provincia.objects.create(
            sigla="MI",
            nome="Milano",
            regione="Lombardia",
            latitudine=45.4642,
            longitudine=9.1900,
        )
        self.user = User.objects.create_user(
            username="moderazione",
            email="moderazione@example.com",
            password="Password-sicura-2026!",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            provincia_obj=provincia,
            citta="Milano",
        )
        self.categoria = Categoria.objects.create(nome="Test moderazione")

    def create_pending_announcement(self, suffix):
        annuncio = Annuncio.objects.create(
            utente=self.user,
            titolo=f"Oggetto da moderare {suffix}",
            descrizione="Descrizione valida",
            categoria=self.categoria,
            tipo="offro",
        )
        Annuncio.objects.filter(pk=annuncio.pk).update(
            moderation_status="pending",
            attivo=True,
        )
        annuncio.refresh_from_db()
        return annuncio

    def test_repeated_rejection_applies_only_one_strike_and_notification(self):
        annuncio = self.create_pending_announcement("uno")

        first = reject_announcement(annuncio.pk)
        second = reject_announcement(annuncio.pk)

        self.profile.refresh_from_db()
        annuncio.refresh_from_db()
        self.assertTrue(first.changed)
        self.assertTrue(first.strike_applied)
        self.assertFalse(second.changed)
        self.assertEqual(self.profile.content_strikes, 1)
        self.assertEqual(annuncio.moderation_status, "rejected")
        self.assertFalse(annuncio.attivo)
        self.assertIsNotNone(annuncio.disattivato_at)
        self.assertEqual(Notifica.objects.filter(utente=self.user).count(), 1)

    def test_progressive_rejections_suspend_then_ban_and_cap_strikes(self):
        first = self.create_pending_announcement("uno")
        second = self.create_pending_announcement("due")
        third = self.create_pending_announcement("tre")
        fourth = self.create_pending_announcement("quattro")

        reject_announcement(first.pk)
        reject_announcement(second.pk)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.content_strikes, 2)
        self.assertGreater(self.profile.suspension_until, timezone.now())
        self.assertFalse(self.profile.is_banned)

        reject_announcement(third.pk)
        reject_announcement(fourth.pk)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.content_strikes, 3)
        self.assertTrue(self.profile.is_banned)
        self.assertIsNotNone(self.profile.banned_at)
        self.assertIsNone(self.profile.suspension_until)

    def test_automatic_approval_cannot_override_rejection(self):
        annuncio = self.create_pending_announcement("bloccato")
        reject_announcement(annuncio.pk)

        blocked = approve_announcement(annuncio.pk)
        annuncio.refresh_from_db()

        self.assertTrue(blocked.blocked)
        self.assertFalse(blocked.changed)
        self.assertEqual(annuncio.moderation_status, "rejected")
        self.assertFalse(annuncio.attivo)

        forced = approve_announcement(
            annuncio.pk,
            allow_rejected_override=True,
        )
        annuncio.refresh_from_db()
        self.assertTrue(forced.changed)
        self.assertEqual(annuncio.moderation_status, "approved")
        self.assertTrue(annuncio.attivo)
        self.assertIsNone(annuncio.disattivato_at)

    def test_model_handler_uses_idempotent_rejection(self):
        annuncio = self.create_pending_announcement("webhook")
        payload = {
            "moderation_status": "rejected",
            "moderation": [{"label": "Violence", "confidence": "0.95"}],
        }

        first = annuncio.handle_moderation_result(payload)
        second = annuncio.handle_moderation_result(payload)

        self.profile.refresh_from_db()
        annuncio.refresh_from_db()
        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertEqual(self.profile.content_strikes, 1)
        self.assertEqual(annuncio.moderation_labels[0]["label"], "Violence")
        self.assertEqual(Notifica.objects.filter(utente=self.user).count(), 1)

    def test_approval_notification_is_created_only_on_transition(self):
        annuncio = self.create_pending_announcement("approvato")

        first = approve_announcement(annuncio.pk, notify_user=True)
        second = approve_announcement(annuncio.pk, notify_user=True)

        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertEqual(Notifica.objects.filter(utente=self.user).count(), 1)


class ModerationEmailFailureTests(SimpleTestCase):
    @override_settings(
        ADMIN_MODERATION_EMAIL="moderation@example.invalid",
        DEFAULT_FROM_EMAIL="noreply@example.invalid",
    )
    def test_email_failure_does_not_auto_approve_pending_announcement(self):
        annuncio = SimpleNamespace(
            id=42,
            titolo="Oggetto da moderare",
            descrizione="Descrizione valida",
            moderation_status="pending",
            utente=SimpleNamespace(username="utente"),
            categoria=SimpleNamespace(nome="Categoria"),
            data_creazione=datetime(2026, 1, 1, 12, 0),
            get_tipo_display=lambda: "Offro",
            get_image_url=lambda: "https://example.invalid/image.jpg",
            save=MagicMock(),
        )

        with (
            patch("scambi.models.Annuncio.objects.get", return_value=annuncio),
            patch(
                "django.core.mail.EmailMultiAlternatives.send",
                side_effect=RuntimeError("smtp unavailable"),
            ),
            patch("time.sleep"),
        ):
            Annuncio._perform_moderation_sync(annuncio.id, "unused-public-id")

        self.assertEqual(annuncio.moderation_status, "pending")
        annuncio.save.assert_not_called()
