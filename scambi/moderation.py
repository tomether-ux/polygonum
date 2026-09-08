"""Operazioni centralizzate e atomiche per la moderazione degli annunci."""

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Annuncio, Notifica, UserProfile


@dataclass(frozen=True)
class ModerationDecision:
    annuncio: Annuncio
    changed: bool
    blocked: bool = False
    strike_applied: bool = False
    strike_count: int | None = None


def get_announcement_by_cloudinary_public_id(public_id):
    """Trova un solo annuncio tramite il public_id Cloudinary esatto.

    Il valore nel database contiene anche resource type, upload type, versione
    ed estensione. CloudinaryField lo converte però in una CloudinaryResource,
    dalla quale possiamo confrontare il public_id originale senza affidarci a
    una corrispondenza parziale sul nome del file.
    """
    if (
        not isinstance(public_id, str)
        or not public_id
        or len(public_id) > 255
        or '\x00' in public_id
    ):
        raise ValueError('public_id Cloudinary non valido')

    matches = []
    candidates = (
        Annuncio.objects.filter(immagine__contains=public_id)
        .order_by('pk')
    )
    for announcement in candidates:
        stored_public_id = getattr(announcement.immagine, 'public_id', None)
        if stored_public_id == public_id:
            matches.append(announcement)
            if len(matches) > 1:
                raise Annuncio.MultipleObjectsReturned(
                    'Più annunci usano lo stesso public_id Cloudinary'
                )

    if not matches:
        raise Annuncio.DoesNotExist(
            'Nessun annuncio usa questo public_id Cloudinary'
        )
    return matches[0]


@transaction.atomic
def apply_cloudinary_moderation_result(
    announcement_id,
    expected_public_id,
    payload,
):
    """Applica il risultato solo se l'immagine non è cambiata nel frattempo."""
    announcement = Annuncio.objects.select_for_update().get(pk=announcement_id)
    current_public_id = getattr(announcement.immagine, 'public_id', None)
    if current_public_id != expected_public_id:
        return None

    announcement.handle_moderation_result(payload)
    return announcement


def _strike_details(annuncio, strike_count):
    if strike_count == 1:
        return (
            "Prima violazione: contenuto inappropriato rilevato",
            f"⚠️ Il tuo annuncio '{annuncio.titolo}' è stato rimosso perché "
            "contiene contenuto inappropriato.\n\nHai ricevuto il tuo PRIMO "
            "strike. Ti preghiamo di rispettare le linee guida della "
            "community.\n\n⚠️ Attenzione: al terzo strike riceverai un ban "
            "permanente.",
        )
    if strike_count == 2:
        return (
            "Seconda violazione: sospensione 7 giorni",
            f"🚫 Il tuo annuncio '{annuncio.titolo}' è stato rimosso per "
            "contenuto inappropriato.\n\nHai ricevuto il SECONDO strike. "
            "Il tuo account è stato SOSPESO per 7 giorni.\n\n⚠️ ULTIMO "
            "AVVISO: al prossimo strike riceverai un ban permanente!",
        )
    return (
        "Terza violazione: ban permanente",
        f"❌ Il tuo annuncio '{annuncio.titolo}' è stato rimosso per "
        "contenuto inappropriato.\n\nHai raggiunto il TERZO strike. Il "
        "tuo account è stato BANNATO PERMANENTEMENTE.\n\nNon potrai più "
        "pubblicare annunci o partecipare alla piattaforma.",
    )


@transaction.atomic
def reject_announcement(
    annuncio_id,
    *,
    moderation_response=None,
    moderation_labels=None,
):
    """Rifiuta una sola volta un annuncio e applica al massimo uno strike."""
    annuncio = Annuncio.objects.select_for_update().get(pk=annuncio_id)

    if annuncio.moderation_status == "rejected":
        strike_count = UserProfile.objects.filter(
            user_id=annuncio.utente_id,
        ).values_list("content_strikes", flat=True).first()
        return ModerationDecision(
            annuncio=annuncio,
            changed=False,
            strike_count=strike_count,
        )

    profile = UserProfile.objects.select_for_update().get(
        user_id=annuncio.utente_id,
    )
    previous_count = min(max(profile.content_strikes or 0, 0), 3)
    strike_count = min(previous_count + 1, 3)
    now = timezone.now()

    annuncio.moderation_status = "rejected"
    annuncio.attivo = False
    annuncio.moderated_at = now
    annuncio_fields = [
        "moderation_status",
        "attivo",
        "moderated_at",
        "disattivato_at",
    ]
    if moderation_response is not None:
        annuncio.moderation_response = moderation_response
        annuncio_fields.append("moderation_response")
    if moderation_labels is not None:
        annuncio.moderation_labels = moderation_labels
        annuncio_fields.append("moderation_labels")
    annuncio.save(update_fields=annuncio_fields)

    ban_reason, notification_message = _strike_details(
        annuncio,
        strike_count,
    )
    profile.content_strikes = strike_count
    profile.ban_reason = ban_reason
    profile_fields = ["content_strikes", "ban_reason"]

    if strike_count == 2:
        profile.suspension_until = now + timedelta(days=7)
        profile_fields.append("suspension_until")
    elif strike_count == 3:
        profile.is_banned = True
        profile.banned_at = profile.banned_at or now
        profile.suspension_until = None
        profile_fields.extend(["is_banned", "banned_at", "suspension_until"])

    profile.save(update_fields=profile_fields)
    Notifica.objects.create(
        utente_id=annuncio.utente_id,
        tipo="sistema",
        titolo=f"⚠️ Annuncio rimosso - Strike {strike_count}/3",
        messaggio=notification_message,
        letta=False,
    )

    return ModerationDecision(
        annuncio=annuncio,
        changed=True,
        strike_applied=strike_count > previous_count,
        strike_count=strike_count,
    )


@transaction.atomic
def approve_announcement(
    annuncio_id,
    *,
    moderation_response=None,
    moderation_labels=None,
    allow_rejected_override=False,
    notify_user=False,
):
    """Approva un annuncio senza riaprire rifiuti, salvo override esplicito."""
    annuncio = Annuncio.objects.select_for_update().get(pk=annuncio_id)

    if annuncio.moderation_status == "rejected" and not allow_rejected_override:
        return ModerationDecision(annuncio=annuncio, changed=False, blocked=True)

    if annuncio.moderation_status == "approved" and annuncio.attivo:
        return ModerationDecision(annuncio=annuncio, changed=False)

    annuncio.moderation_status = "approved"
    annuncio.attivo = True
    annuncio.moderated_at = timezone.now()
    annuncio_fields = [
        "moderation_status",
        "attivo",
        "moderated_at",
        "disattivato_at",
    ]
    if moderation_response is not None:
        annuncio.moderation_response = moderation_response
        annuncio_fields.append("moderation_response")
    if moderation_labels is not None:
        annuncio.moderation_labels = moderation_labels
        annuncio_fields.append("moderation_labels")
    annuncio.save(update_fields=annuncio_fields)

    if notify_user:
        Notifica.objects.create(
            utente_id=annuncio.utente_id,
            tipo="sistema",
            titolo="✅ Annuncio approvato",
            messaggio=(
                f'Il tuo annuncio "{annuncio.titolo}" è stato approvato ed è '
                "ora visibile a tutti gli utenti!"
            ),
            letta=False,
            url_azione=f"/annuncio/{annuncio.id}/",
        )

    return ModerationDecision(annuncio=annuncio, changed=True)
