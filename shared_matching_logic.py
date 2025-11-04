#!/usr/bin/env python
"""
LOGICA CONDIVISA TRA DJANGO APP E CYCLECALCULATOR

Questo file contiene le funzioni che DEVONO essere identiche
tra la Django App e il CycleCalculator per garantire coerenza.

Copiare queste funzioni nel CycleCalculator per assicurare che
i cicli salvati nel DB siano compatibili con i filtri della Django App.
"""

import re
from difflib import SequenceMatcher


# ============================================================================
# ESTRAZIONE PAROLE (copia semplificata da matching.py)
# ============================================================================

STOP_WORDS = {
    'il', 'lo', 'la', 'i', 'gli', 'le',
    'un', 'uno', 'una',
    'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
    'del', 'dello', 'della', 'dei', 'degli', 'delle',
    'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle',
    'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
    'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
    'e', 'o', 'ma', 'anche', 'che', 'non', 'più', 'molto',
    'vendo', 'cerco', 'scambio', 'offro', 'regalo', 'disponibile'
}


def estrai_parole_chiave_semplice(testo):
    """
    Versione semplificata di estrai_parole_chiave per il CycleCalculator.
    Non usa WordNet per evitare dipendenze pesanti.
    """
    if not testo:
        return set()

    # Normalizza
    testo = testo.lower().strip()

    # Rimuovi punteggiatura
    testo = re.sub(r'[^\w\s]', ' ', testo)

    # Estrai parole
    parole = testo.split()

    # Rimuovi stop words e parole corte
    parole_filtrate = {
        p for p in parole
        if p not in STOP_WORDS and len(p) > 2
    }

    return parole_filtrate


# ============================================================================
# COMPATIBILITÀ ANNUNCI (copia da matching.py linee 656-732)
# ============================================================================

def oggetti_compatibili_con_tipo(offerto, cercato):
    """
    Verifica se un annuncio offerto è compatibile con un annuncio cercato
    e restituisce il TIPO di match.

    Args:
        offerto: Oggetto Annuncio (tipo='offro')
        cercato: Oggetto Annuncio (tipo='cerco')

    Returns:
        tuple: (compatibile: bool, tipo_match: str)
               tipo_match può essere:
               - 'specifico': match esatto sui titoli
               - 'parziale': parole in comune nei titoli
               - 'sinonimo': sinonimi o parole simili
               - 'categoria': stessa categoria
               - 'generico': match generico
               - None: non compatibile
    """
    # 1. Verifica categoria
    if offerto.categoria != cercato.categoria:
        return False, None

    # 2. Estrai parole chiave
    parole_offerto = estrai_parole_chiave_semplice(offerto.titolo)
    parole_cercato = estrai_parole_chiave_semplice(cercato.titolo)

    # 3. Match SPECIFICO: tutte le parole del cercato sono nell'offerto
    if parole_cercato and parole_cercato.issubset(parole_offerto):
        return True, 'specifico'

    # 4. Match PARZIALE: almeno una parola in comune
    parole_comuni = parole_offerto.intersection(parole_cercato)
    if parole_comuni:
        # Verifica similarità tra parole
        for p_off in parole_offerto:
            for p_cer in parole_cercato:
                similarity = SequenceMatcher(None, p_off, p_cer).ratio()
                if similarity >= 0.8:  # 80% similarità
                    return True, 'parziale'

    # 5. Match SINONIMO: parole molto simili (60-80% similarità)
    for p_off in parole_offerto:
        for p_cer in parole_cercato:
            similarity = SequenceMatcher(None, p_off, p_cer).ratio()
            if 0.6 <= similarity < 0.8:
                return True, 'sinonimo'

    # 6. Match CATEGORIA: stessa categoria ma nessuna parola in comune
    return True, 'categoria'


# ============================================================================
# CALCOLO QUALITÀ CICLO (copia da matching.py linee 1691-1741)
# ============================================================================

def calcola_qualita_ciclo(ciclo, return_tipo_match=False):
    """
    Calcola un punteggio di qualità per un ciclo di scambio.

    Args:
        ciclo: Dizionario con struttura:
               {
                   'utenti': [
                       {'user': User, 'offerta': Annuncio, 'richiede': Annuncio},
                       ...
                   ]
               }
        return_tipo_match: Se True, restituisce anche se ha match titoli

    Returns:
        Se return_tipo_match=False: int (punteggio 0-100)
        Se return_tipo_match=True: tuple (punteggio: int, ha_match_titoli: bool)
    """
    punteggio = 0
    ha_match_titoli = False  # specifico, parziale o sinonimo

    utenti = ciclo.get('utenti', [])
    if not utenti:
        return (0, False) if return_tipo_match else 0

    # Per ogni scambio nel ciclo
    num_scambi = len(utenti)

    for i in range(num_scambi):
        utente_corrente = utenti[i]
        utente_successivo = utenti[(i + 1) % num_scambi]

        offerta = utente_corrente.get('offerta')
        richiesta = utente_successivo.get('richiede')

        if not offerta or not richiesta:
            continue

        # Calcola compatibilità
        compatibile, tipo_match = oggetti_compatibili_con_tipo(offerta, richiesta)

        if not compatibile:
            continue

        # Assegna punteggi in base al tipo di match
        if tipo_match == 'specifico':
            punteggio += 40
            ha_match_titoli = True
        elif tipo_match == 'parziale':
            punteggio += 30
            ha_match_titoli = True
        elif tipo_match == 'sinonimo':
            punteggio += 20
            ha_match_titoli = True
        elif tipo_match == 'categoria':
            punteggio += 5
        else:  # generico
            punteggio += 2

    # Normalizza per numero di scambi
    if num_scambi > 0:
        punteggio = punteggio // num_scambi

    if return_tipo_match:
        return punteggio, ha_match_titoli

    return punteggio


# ============================================================================
# FUNZIONE DI TEST
# ============================================================================

if __name__ == '__main__':
    # Test della logica
    print("=" * 80)
    print("TEST LOGICA CONDIVISA")
    print("=" * 80)

    # Mock di Annuncio per test
    class MockAnnuncio:
        def __init__(self, titolo, categoria, tipo):
            self.titolo = titolo
            self.categoria = categoria
            self.tipo = tipo

    # Test 1: Match specifico
    offro_synth = MockAnnuncio("vendo synth udo6", "STRUMENTI MUSICALI", "offro")
    cerco_synth = MockAnnuncio("cerco synth", "STRUMENTI MUSICALI", "cerco")

    comp, tipo = oggetti_compatibili_con_tipo(offro_synth, cerco_synth)
    print(f"\nTest 1: synth ↔ synth")
    print(f"   Compatibile: {comp}, Tipo: {tipo}")
    assert comp == True
    assert tipo == 'specifico'

    # Test 2: Match categoria
    offro_basso = MockAnnuncio("basso", "STRUMENTI MUSICALI", "offro")
    cerco_chitarra = MockAnnuncio("chitarra", "STRUMENTI MUSICALI", "cerco")

    comp, tipo = oggetti_compatibili_con_tipo(offro_basso, cerco_chitarra)
    print(f"\nTest 2: basso ↔ chitarra (categoria)")
    print(f"   Compatibile: {comp}, Tipo: {tipo}")
    assert comp == True
    assert tipo == 'categoria'

    # Test 3: Non compatibile (categoria diversa)
    offro_libro = MockAnnuncio("libro", "LIBRI", "offro")
    cerco_synth2 = MockAnnuncio("synth", "STRUMENTI MUSICALI", "cerco")

    comp, tipo = oggetti_compatibili_con_tipo(offro_libro, cerco_synth2)
    print(f"\nTest 3: libro (LIBRI) ↔ synth (STRUMENTI)")
    print(f"   Compatibile: {comp}, Tipo: {tipo}")
    assert comp == False
    assert tipo == None

    print("\n" + "=" * 80)
    print("✅ TUTTI I TEST PASSATI!")
    print("=" * 80)
