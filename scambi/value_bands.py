"""Value bands: legacy identifiers stay distinct until an explicit migration."""

BANDS = [
    ('v1', 'Minima', 'Fino a 25 €'),
    ('v2', 'Bassa', 'Oltre 25–60 €'),
    ('v3', 'Medio-bassa', 'Oltre 60–150 €'),
    ('v4', 'Media', 'Oltre 150–400 €'),
    ('v5', 'Medio-alta', 'Oltre 400–900 €'),
    ('v6', 'Alta', 'Oltre 900–2.000 €'),
    ('v7', 'Molto alta', 'Oltre 2.000 €'),
]
LEGACY_CHOICES = [('economico', 'Economico'), ('basso', 'Basso'),
                  ('medio', 'Medio'), ('alto', 'Alto'), ('premium', 'Premium')]
CHOICES = [(code, label) for code, label, _ in BANDS]
INPUT_CHOICES = [(code, f'{label} · {interval}') for code, label, interval in BANDS]


def adjacent(first, second):
    codes = [code for code, _, _ in BANDS]
    return first in codes and second in codes and abs(codes.index(first) - codes.index(second)) == 1


def bands_for(announcement):
    if not announcement:
        return set()
    first = getattr(announcement, 'fascia_prezzo', None)
    second = getattr(announcement, 'fascia_secondaria', None)
    known = dict(CHOICES + LEGACY_CHOICES)
    result = {first} if first in known else set()
    if second and adjacent(first, second):
        result.add(second)
    return result


def common_bands(announcements):
    groups = [bands_for(item) for item in announcements]
    return set.intersection(*groups) if groups else set()


def chain_is_equal(chain):
    # Only the offered objects travel around the chain; a wanted listing is
    # a search criterion, not an additional object being exchanged.
    exchanges = chain.get('scambi_opzioni') or []
    if exchanges:
        # Existence of a common band, without enumerating every combination.
        groups = [set().union(*(bands_for(option.get('offerta'))
                               for option in exchange.get('opzioni', [])))
                  for exchange in exchanges]
        return bool(set.intersection(*groups))
    return bool(common_bands([row.get('offerta') for row in chain.get('utenti', [])]))
