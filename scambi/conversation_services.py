"""Operazioni atomiche condivise per la creazione delle conversazioni."""

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Exists, OuterRef

from .models import CicloScambio, Conversazione, Messaggio


_CYCLE_NOT_SUPPLIED = object()


def _conversation_cycle_id(conversation):
    """Restituisce l'ID numerico del ciclo associato, se valido."""
    if conversation.tipo != 'gruppo' or not conversation.catena_scambio_id:
        return None
    try:
        cycle_id = int(conversation.catena_scambio_id)
    except (TypeError, ValueError):
        return None
    return cycle_id if cycle_id > 0 else None


def _announcement_title(value):
    """Estrae in modo tollerante il titolo da un annuncio serializzato."""
    if not isinstance(value, dict):
        return ''
    return str(value.get('titolo') or '').strip()


def get_conversation_display(conversation, user, cycle=_CYCLE_NOT_SUPPLIED):
    """
    Costruisce titolo e riepilogo della chat dal punto di vista dell'utente.

    Il nome memorizzato nel database resta stabile per l'idempotenza; questa
    rappresentazione è soltanto per l'interfaccia e funziona anche con le chat
    già esistenti.
    """
    if conversation.tipo != 'gruppo':
        other_users = [
            participant
            for participant in conversation.utenti.all()
            if participant.pk != user.pk
        ]
        return {
            'nome': other_users[0].username if other_users else 'Conversazione',
            'scambio': '',
            'ciclo': None,
        }

    cycle_id = _conversation_cycle_id(conversation)
    if cycle is _CYCLE_NOT_SUPPLIED and cycle_id is not None:
        cycle = CicloScambio.objects.filter(pk=cycle_id).first()
    elif cycle is _CYCLE_NOT_SUPPLIED:
        cycle = None

    # ``catena_scambio_id`` era usato anche dal vecchio modello CatenaScambio:
    # un ID uguale non basta per associare in sicurezza la conversazione al
    # nuovo CicloScambio. Le chat create dal servizio hanno sempre questo nome.
    expected_cycle_name = f'Catena di scambio #{cycle_id}'
    if cycle is not None and conversation.nome != expected_cycle_name:
        cycle = None

    if cycle is None:
        return {
            'nome': conversation.nome or f'Catena di scambio #{cycle_id or conversation.pk}',
            'scambio': '',
            'ciclo': None,
        }

    if cycle.lunghezza == 2:
        display_name = 'Scambio diretto'
    else:
        display_name = f'Catena a {cycle.lunghezza} partecipanti'

    offer_title = ''
    request_title = ''
    details = cycle.dettagli if isinstance(cycle.dettagli, dict) else {}
    for user_details in details.get('utenti', []):
        if not isinstance(user_details, dict):
            continue
        serialized_user = user_details.get('user') or {}
        serialized_user_id = (
            serialized_user.get('id')
            if isinstance(serialized_user, dict)
            else serialized_user
        )
        if str(serialized_user_id) != str(user.pk):
            continue
        offer_title = _announcement_title(user_details.get('offerta'))
        request_title = _announcement_title(user_details.get('richiede'))
        break

    exchange_parts = []
    if offer_title:
        exchange_parts.append(f'Offri: {offer_title}')
    if request_title:
        exchange_parts.append(f'Cerchi: {request_title}')

    return {
        'nome': display_name,
        'scambio': ' · '.join(exchange_parts),
        'ciclo': cycle,
    }


def decorate_conversations_for_user(conversations, user):
    """Aggiunge le etichette UI a una lista di conversazioni con una query."""
    conversation_list = list(conversations)
    cycle_ids = {
        cycle_id
        for conversation in conversation_list
        if (cycle_id := _conversation_cycle_id(conversation)) is not None
    }
    cycles = CicloScambio.objects.in_bulk(cycle_ids)

    for conversation in conversation_list:
        cycle_id = _conversation_cycle_id(conversation)
        display = get_conversation_display(
            conversation,
            user,
            cycle=cycles.get(cycle_id),
        )
        conversation.display_name = display['nome']
        conversation.display_exchange = display['scambio']

    return conversation_list


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
