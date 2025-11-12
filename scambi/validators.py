"""
Validatori per contenuti testuali degli annunci.
Sistema di blacklist per prevenire contenuti inappropriati, illegali o sessuali.
"""

import re
from django.core.exceptions import ValidationError


# ============================================================
# BLACKLIST PAROLE VIETATE
# ============================================================

PAROLE_VIETATE = [
    # Contenuti sessuali espliciti
    'sesso', 'sex', 'porn', 'porno', 'xxx', 'nudo', 'nuda', 'nudi', 'nude',
    'masturbazione', 'orgasmo', 'scopare', 'troia', 'puttana', 'zoccola',
    'cazzo', 'fica', 'pompino', 'bocchino', 'rapporto sessuale', 'amplesso',
    'erotico', 'erotica', 'erotici', 'erotiche', 'sexy',
    'tette', 'tetta', 'seno', 'seni', 'capezzoli', 'capezzolo',
    'culo', 'culo nudo', 'sedere', 'natiche', 'chiappa', 'chiappe',
    'fighe', 'patata', 'passera', 'vagina', 'vagine',
    'coglioni', 'testicoli', 'palle', 'scroto', 'pene', 'pisello',
    'sega', 'seghe', 'masturbare', 'chiavare', 'chiavata',
    'scopata', 'scopate', 'inculare', 'inculata', 'anale',
    'leccata', 'leccare', 'cunnilingus', 'fellatio', 'blowjob',
    'venire', 'sborrata', 'sborrate', 'sperma', 'eiaculazione',

    # Prostituzione e servizi sessuali
    'escort', 'prostituta', 'prostituto', 'squillo', 'accompagnatrice',
    'accompagnatore', 'gigolo', 'prostituzione', 'marchetta',
    'prestazione sessuale', 'prestazioni sessuali', 'servizi sessuali',
    'servizio sessuale', 'compagnia a pagamento', 'incontri a pagamento',

    # Massaggi sospetti
    'massaggio erotico', 'massaggio tantrico', 'massaggio completo',
    'massaggio privato', 'massaggio rilassante a domicilio',
    'massaggio body to body', 'massaggio prostatico',

    # Pattern di scambio inappropriato
    'prestazioni in cambio', 'prestazioni sessuali in cambio',
    'compagnia in cambio', 'sesso in cambio',

    # Droghe
    'droga', 'cocaina', 'eroina', 'marijuana', 'hashish', 'cannabis',
    'ecstasy', 'mdma', 'lsd', 'crack', 'metanfetamina', 'anfetamine',
    'spinello', 'canna', 'erba', 'fumo', 'pusher', 'spacciare',

    # Armi
    'pistola', 'fucile', 'arma da fuoco', 'munizioni', 'esplosivo',
    'bomba', 'granata', 'coltello a serramanico', 'tirapugni',

    # Contenuti illegali
    'pedofilia', 'pedopornografia', 'minorenne', 'bambini nudi',
    'foto intime minori', 'revenge porn', 'ricatto sessuale',

    # Documenti falsi
    'patente falsa', 'carta identità falsa', 'passaporto falso',
    'documenti falsi', 'green pass falso', 'certificato falso',
]


# ============================================================
# PATTERN SOSPETTI (regex che catturano frasi)
# ============================================================

PATTERN_SOSPETTI = [
    # Offerte di compagnia sospette
    r'\b(offro|cerco)\s+(compagnia|company|escort)\b',
    r'\bmassaggio\s+(rilassante|tantrico|completo|speciale)\b',
    r'\bincontro\s+(privato|riservato|discreto|intimo)\b',
    r'\bservizi?\s+(completi?|speciali?|personalizzati?|per\s+adulti)\b',

    # Scambi inappropriati
    r'\b(in\s+)?cambio\s+(di\s+)?(prestazioni?|favori?\s+sessuali?|servizi?\s+sessuali?)\b',
    r'\bprestazioni?\s+in\s+cambio\b',
    r'\bsesso\s+in\s+cambio\b',

    # Linguaggio velato
    r'\bdiscret[oa]\s+(assolut[oa]|garantit[oa])\b',
    r'\bsenza\s+impegno\s+(fisico|sentimentale)\b',
    r'\bincontri?\s+(hot|piccanti?|trasgressiv[io]|osé)\b',

    # Numeri di telefono sospetti (pattern escort)
    r'\b(chiamami|contattami)\s+(per|x)\s+(info|dettagli|altro)\b',
    r'\bdisponibile\s+24/7\b',
    r'\bricevo\s+(a\s+domicilio|in\s+privato|in\s+hotel)\b',
]


# ============================================================
# NORMALIZZAZIONE TESTO
# ============================================================

def normalizza_testo(testo):
    """
    Normalizza il testo per catturare varianti furbe delle parole vietate.

    Esempi:
    - 's3sso' → 'sesso'
    - 's€sso' → 'sesso'
    - 'S E S S O' → 'sesso'
    - 'sexxo' → 'sesso'
    """
    if not testo:
        return ""

    # Converti in minuscolo
    testo_norm = testo.lower()

    # Sostituisci numeri comuni con lettere
    sostituzioni = {
        '0': 'o',
        '1': 'i',
        '3': 'e',
        '4': 'a',
        '5': 's',
        '7': 't',
        '8': 'b',
        '9': 'g',
    }
    for num, lettera in sostituzioni.items():
        testo_norm = testo_norm.replace(num, lettera)

    # Sostituisci simboli comuni
    simboli = {
        '@': 'a',
        '€': 'e',
        '$': 's',
        '!': 'i',
        '£': 'e',
    }
    for simbolo, lettera in simboli.items():
        testo_norm = testo_norm.replace(simbolo, lettera)

    # Rimuovi spazi tra lettere singole (S E S S O → SESSO)
    testo_norm = re.sub(r'(\w)\s+(?=\w)', r'\1', testo_norm)

    # Rimuovi caratteri ripetuti eccessivi (sexxo → sesso)
    testo_norm = re.sub(r'(.)\1{2,}', r'\1\1', testo_norm)

    # Rimuovi punteggiatura e caratteri speciali
    testo_norm = re.sub(r'[^\w\s]', ' ', testo_norm)

    return testo_norm


# ============================================================
# VALIDAZIONE
# ============================================================

def valida_contenuto_testuale(testo, campo_nome="testo"):
    """
    Valida che il testo non contenga parole vietate o pattern sospetti.

    Args:
        testo (str): Il testo da validare
        campo_nome (str): Nome del campo per il messaggio di errore

    Raises:
        ValidationError: Se il testo contiene contenuti vietati
    """
    if not testo:
        return  # Testo vuoto è OK

    testo_originale = testo
    testo_normalizzato = normalizza_testo(testo)

    # ===== CHECK 1: Parole vietate =====
    for parola_vietata in PAROLE_VIETATE:
        parola_norm = normalizza_testo(parola_vietata)

        # Cerca la parola come parola intera (word boundary)
        pattern = r'\b' + re.escape(parola_norm) + r'\b'

        if re.search(pattern, testo_normalizzato, re.IGNORECASE):
            raise ValidationError(
                f"Il {campo_nome} contiene contenuti non ammessi. "
                f"Ti preghiamo di rimuovere termini inappropriati o illegali."
            )

    # ===== CHECK 2: Pattern sospetti =====
    for pattern in PATTERN_SOSPETTI:
        if re.search(pattern, testo_normalizzato, re.IGNORECASE):
            raise ValidationError(
                f"Il {campo_nome} contiene frasi o contenuti non ammessi su questa piattaforma. "
                f"Polygonum è uno spazio per scambi di beni e servizi leciti."
            )

    # ===== CHECK 3: Troppi numeri di telefono/contatti =====
    # Pattern per trovare numeri di telefono
    numeri_telefono = re.findall(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4,}\b', testo_originale)
    if len(numeri_telefono) > 1:
        raise ValidationError(
            f"Il {campo_nome} non può contenere multipli numeri di telefono. "
            f"Utilizza il sistema di messaggistica interno di Polygonum."
        )


def valida_annuncio_contenuto(titolo, descrizione):
    """
    Valida il contenuto testuale completo di un annuncio.

    Args:
        titolo (str): Titolo dell'annuncio
        descrizione (str): Descrizione dell'annuncio

    Raises:
        ValidationError: Se titolo o descrizione contengono contenuti vietati
    """
    # Valida titolo
    valida_contenuto_testuale(titolo, campo_nome="titolo")

    # Valida descrizione
    valida_contenuto_testuale(descrizione, campo_nome="descrizione")

    # Check aggiuntivo: testo combinato (per pattern che potrebbero essere divisi)
    testo_completo = f"{titolo} {descrizione}"
    testo_norm_completo = normalizza_testo(testo_completo)

    # Pattern che potrebbero essere divisi tra titolo e descrizione
    pattern_divisi = [
        r'\bsesso\b.*\bcambio\b',
        r'\bprestazioni?\b.*\bcambio\b',
        r'\bescort\b.*\bdiscret[oa]\b',
    ]

    for pattern in pattern_divisi:
        if re.search(pattern, testo_norm_completo, re.IGNORECASE | re.DOTALL):
            raise ValidationError(
                "Il contenuto dell'annuncio contiene riferimenti a servizi non ammessi. "
                "Polygonum è una piattaforma per scambi leciti di beni e servizi."
            )
