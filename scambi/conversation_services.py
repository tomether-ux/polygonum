"""Operazioni atomiche condivise per la creazione delle conversazioni."""

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Exists, OuterRef

from .models import CicloScambio, Conversazione, Messaggio


def find_private_conversation(user_a, user_b):
    """Restituisce una chat privata composta esattamente dai due utenti."""
    if user_a.pk == user_b.pk:
        return None

    other_participants = (
        Conversazione.utenti.through.objects.filter(
            conversazione_id=OuterRef('pk')
        )
        .exclude(user_id__in=[user_a.pk, user_b.pk])
    )
    return (
        Conversazione.objects.filter(tipo='privata', utenti=user_a)
        .filter(utenti=user_b)
        .annotate(has_other_participants=Exists(other_participants))
        .filter(has_other_participants=False)
        .order_by('-attiva', 'id')
        .first()
    )


@transaction.atomic
def get_or_create_private_conversation(user_a, user_b):
    """
    Recupera o crea una sola chat privata per la coppia di utenti.

    Il lock sugli utenti, acquisito sempre nello stesso ordine, serializza le
    richieste concorrenti per la stessa coppia senza richiedere una modifica
    allo schema del database.
    """
    if user_a.pk == user_b.pk:
        raise ValueError('Una conversazione privata richiede due utenti diversi')

    user_ids = sorted((user_a.pk, user_b.pk))
    locked_user_ids = list(
        User.objects.select_for_update()
        .filter(pk__in=user_ids)
        .order_by('pk')
        .values_list('pk', flat=True)
    )
    if locked_user_ids != user_ids:
        raise User.DoesNotExist('Uno degli utenti non esiste più')

    conversation = find_private_conversation(user_a, user_b)
    if conversation:
        return conversation, False

    conversation = Conversazione.objects.create(tipo='privata')
    conversation.utenti.add(user_a, user_b)
    return conversation, True


@transaction.atomic
def get_or_create_cycle_group_conversation(ciclo, actor):
    """
    Recupera o crea la chat di gruppo associata a un CicloScambio.

    Il lock sul ciclo rende idempotente la creazione anche quando gli ultimi
    consensi arrivano contemporaneamente.
    """
    locked_cycle = CicloScambio.objects.select_for_update().get(pk=ciclo.pk)
    participants = list(
        User.objects.filter(pk__in=locked_cycle.users).order_by('pk')
    )
    participant_ids = {participant.pk for participant in participants}
    conversation_name = f'Catena di scambio #{locked_cycle.pk}'

    # ``catena_scambio_id`` è condiviso con un vecchio modello di catena e
    # potrebbe contenere casualmente lo stesso numero. Riutilizziamo solo una
    # chat con nome e partecipanti esattamente corrispondenti al ciclo.
    candidates = Conversazione.objects.filter(
        tipo='gruppo',
        nome=conversation_name,
        catena_scambio_id=str(locked_cycle.pk),
    ).order_by('id')
    for conversation in candidates:
        if set(conversation.utenti.values_list('pk', flat=True)) == participant_ids:
            return conversation, False, participants

    conversation = Conversazione.objects.create(
        tipo='gruppo',
        nome=conversation_name,
        catena_scambio_id=str(locked_cycle.pk),
    )
    conversation.utenti.set(participants)
    Messaggio.objects.create(
        conversazione=conversation,
        mittente=actor,
        contenuto=(
            '🎉 Tutti sono interessati! Catena attivata. '
            'Coordinate gli scambi qui.'
        ),
        is_sistema=True,
    )
    return conversation, True, participants
