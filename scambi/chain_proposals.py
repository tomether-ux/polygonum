"""Validazione e presentazione della combinazione scelta per una catena."""

from dataclasses import dataclass

from django.contrib.auth.models import User

from .models import Annuncio


@dataclass
class ChainSelectionError(ValueError):
    message: str
    requires_selection: bool = False

    def __str__(self):
        return self.message


def _positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _serialized_exchanges(ciclo):
    details = ciclo.dettagli if isinstance(ciclo.dettagli, dict) else {}
    exchanges = details.get('scambi')
    return exchanges if isinstance(exchanges, list) else []


def _load_valid_options(ciclo):
    """Restituisce le opzioni ancora valide, raggruppate per passaggio."""
    serialized_exchanges = _serialized_exchanges(ciclo)
    if not serialized_exchanges:
        # Compatibilità con cicli/proposte legacy privi del formato ``scambi``.
        return []

    cycle_users = {
        user_id
        for value in (ciclo.users or [])
        if (user_id := _positive_int(value)) is not None
    }
    announcement_ids = set()
    for exchange in serialized_exchanges:
        if not isinstance(exchange, dict):
            continue
        for item in exchange.get('oggetti') or []:
            if not isinstance(item, dict):
                continue
            offered_id = _positive_int((item.get('offerto') or {}).get('id'))
            requested_id = _positive_int((item.get('richiesto') or {}).get('id'))
            if offered_id:
                announcement_ids.add(offered_id)
            if requested_id:
                announcement_ids.add(requested_id)

    announcements = Annuncio.objects.select_related(
        'utente', 'categoria'
    ).in_bulk(announcement_ids)
    users = User.objects.in_bulk(cycle_users)
    valid_exchanges = []
    seen_edges = set()

    for exchange in serialized_exchanges:
        if not isinstance(exchange, dict):
            raise ChainSelectionError('La catena contiene dati non validi.')

        from_user = _positive_int(exchange.get('da_user'))
        to_user = _positive_int(exchange.get('a_user'))
        edge = (from_user, to_user)
        if (
            from_user not in cycle_users
            or to_user not in cycle_users
            or from_user == to_user
            or edge in seen_edges
        ):
            raise ChainSelectionError('La catena contiene passaggi non validi.')
        seen_edges.add(edge)

        options = {}
        for item in exchange.get('oggetti') or []:
            if not isinstance(item, dict):
                continue
            offered_id = _positive_int((item.get('offerto') or {}).get('id'))
            requested_id = _positive_int((item.get('richiesto') or {}).get('id'))
            offered = announcements.get(offered_id)
            requested = announcements.get(requested_id)
            if (
                offered is None
                or requested is None
                or offered.utente_id != from_user
                or requested.utente_id != to_user
                or offered.tipo != 'offro'
                or requested.tipo != 'cerco'
                or not offered.attivo
                or not requested.attivo
                or offered.is_scaduto
                or requested.is_scaduto
            ):
                continue

            options.setdefault(
                (offered.id, requested.id),
                {
                    'offerto': offered,
                    'richiesto': requested,
                },
            )

        if not options:
            raise ChainSelectionError(
                'Una delle opzioni della catena non è più disponibile. '
                'Attendi il prossimo ricalcolo.'
            )

        valid_exchanges.append({
            'da_user': from_user,
            'a_user': to_user,
            'da_username': users.get(from_user).username if users.get(from_user) else str(from_user),
            'a_username': users.get(to_user).username if users.get(to_user) else str(to_user),
            'opzioni': options,
        })

    if len(valid_exchanges) != len(cycle_users):
        raise ChainSelectionError('La catena non contiene tutti i passaggi previsti.')
    return valid_exchanges


def normalize_chain_selection(ciclo, raw_selection=None):
    """
    Valida la scelta client contro le coppie precalcolate nel ciclo.

    Se ogni passaggio ha una sola opzione, la combinazione viene selezionata
    automaticamente. I cicli legacy privi di ``scambi`` restituiscono ``{}``.
    """
    valid_exchanges = _load_valid_options(ciclo)
    if not valid_exchanges:
        return {}

    if isinstance(raw_selection, dict):
        raw_selection = raw_selection.get('scambi')

    if raw_selection is None:
        if any(len(exchange['opzioni']) > 1 for exchange in valid_exchanges):
            raise ChainSelectionError(
                'Scegli una combinazione prima di inviare la proposta.',
                requires_selection=True,
            )
        selected_by_edge = {}
    elif not isinstance(raw_selection, list):
        raise ChainSelectionError('La combinazione selezionata non è valida.')
    else:
        selected_by_edge = {}
        for item in raw_selection:
            if not isinstance(item, dict):
                raise ChainSelectionError('La combinazione selezionata non è valida.')
            edge = (
                _positive_int(item.get('da_user')),
                _positive_int(item.get('a_user')),
            )
            pair = (
                _positive_int(item.get('offerto_id')),
                _positive_int(item.get('richiesto_id')),
            )
            if None in edge or None in pair or edge in selected_by_edge:
                raise ChainSelectionError('La combinazione selezionata non è valida.')
            selected_by_edge[edge] = pair

    normalized = []
    expected_edges = set()
    for exchange in valid_exchanges:
        edge = (exchange['da_user'], exchange['a_user'])
        expected_edges.add(edge)
        options = exchange['opzioni']
        pair = selected_by_edge.get(edge)
        if pair is None and len(options) == 1:
            pair = next(iter(options))
        if pair not in options:
            raise ChainSelectionError(
                'Una delle opzioni selezionate non appartiene più alla catena.'
            )

        offered = options[pair]['offerto']
        requested = options[pair]['richiesto']
        normalized.append({
            'da_user': exchange['da_user'],
            'a_user': exchange['a_user'],
            'da_username': exchange['da_username'],
            'a_username': exchange['a_username'],
            'offerto_id': offered.id,
            'offerto_titolo': offered.titolo,
            'richiesto_id': requested.id,
            'richiesto_titolo': requested.titolo,
        })

    if selected_by_edge and set(selected_by_edge) != expected_edges:
        raise ChainSelectionError('La combinazione selezionata è incompleta.')

    return {'versione': 1, 'scambi': normalized}


def proposal_exchange_rows(proposta):
    """Prepara per il template la combinazione salvata su una proposta."""
    selection = proposta.selezione_annunci
    selected = selection.get('scambi') if isinstance(selection, dict) else None
    if not isinstance(selected, list) or not selected:
        return None

    announcement_ids = {
        announcement_id
        for item in selected
        if isinstance(item, dict)
        for announcement_id in (
            _positive_int(item.get('offerto_id')),
            _positive_int(item.get('richiesto_id')),
        )
        if announcement_id is not None
    }
    user_ids = {
        user_id
        for item in selected
        if isinstance(item, dict)
        for user_id in (
            _positive_int(item.get('da_user')),
            _positive_int(item.get('a_user')),
        )
        if user_id is not None
    }
    announcements = Annuncio.objects.in_bulk(announcement_ids)
    users = User.objects.in_bulk(user_ids)
    rows = []
    for item in selected:
        if not isinstance(item, dict):
            continue
        giver = users.get(_positive_int(item.get('da_user')))
        receiver = users.get(_positive_int(item.get('a_user')))
        giving_ad = announcements.get(_positive_int(item.get('offerto_id')))
        receiving_ad = announcements.get(_positive_int(item.get('richiesto_id')))
        if giver and receiver and giving_ad and receiving_ad:
            rows.append({
                'giver': giver,
                'receiver': receiver,
                'giving_ad': giving_ad,
                'receiving_ad': receiving_ad,
            })
    return rows
