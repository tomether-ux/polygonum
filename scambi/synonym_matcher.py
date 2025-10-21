"""
Modulo per gestire sinonimi italiani con WordNet e caching intelligente
Ottimizzato per performance massime nel cycle calculator
"""
from functools import lru_cache
import nltk
from datetime import datetime

# Flag per indicare se WordNet è stato inizializzato
_WORDNET_INITIALIZED = False
_WORDNET_AVAILABLE = False


def initialize_wordnet():
    """
    Inizializza WordNet italiano scaricando i dati necessari
    Chiamata automaticamente alla prima richiesta di sinonimi
    """
    global _WORDNET_INITIALIZED, _WORDNET_AVAILABLE

    if _WORDNET_INITIALIZED:
        return _WORDNET_AVAILABLE

    print(f"[{datetime.now()}] 📚 Inizializzazione WordNet italiano...")

    try:
        # Prova a importare wordnet
        from nltk.corpus import wordnet as wn

        # Controlla se i dati sono già scaricati testando una query
        try:
            test = wn.synsets('libro', lang='ita')
            _WORDNET_AVAILABLE = True
            print(f"[{datetime.now()}] ✅ WordNet italiano già disponibile")
        except LookupError:
            # Scarica i dati necessari
            print(f"[{datetime.now()}] 📥 Download WordNet e Open Multilingual WordNet...")
            nltk.download('wordnet', quiet=True)
            nltk.download('omw-1.4', quiet=True)

            # Verifica che il download sia andato a buon fine
            test = wn.synsets('libro', lang='ita')
            _WORDNET_AVAILABLE = True
            print(f"[{datetime.now()}] ✅ WordNet italiano scaricato e pronto")

    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ WordNet non disponibile: {e}")
        print(f"[{datetime.now()}] ℹ️ Il matching funzionerà solo con parole esatte")
        _WORDNET_AVAILABLE = False

    _WORDNET_INITIALIZED = True
    return _WORDNET_AVAILABLE


@lru_cache(maxsize=10000)
def get_synonyms(word):
    """
    Ottiene sinonimi di una parola usando WordNet italiano
    Con cache LRU per performance massime

    Args:
        word (str): Parola italiana per cui cercare sinonimi

    Returns:
        set: Insieme di sinonimi (include la parola originale)
    """
    # Normalizza input
    word = word.lower().strip()

    # Se WordNet non è disponibile, ritorna solo la parola stessa
    if not initialize_wordnet():
        return {word}

    try:
        from nltk.corpus import wordnet as wn

        synonyms = {word}  # Includi sempre la parola originale

        # Cerca tutti i synset per questa parola in italiano
        for syn in wn.synsets(word, lang='ita'):
            # Aggiungi tutti i lemmi italiani di questo synset
            for lemma in syn.lemmas('ita'):
                synonym = lemma.name().replace('_', ' ').lower()
                synonyms.add(synonym)

        return synonyms

    except Exception as e:
        # In caso di errore, ritorna solo la parola originale
        return {word}


@lru_cache(maxsize=5000)
def expand_keywords_with_synonyms(keywords_tuple):
    """
    Espande un set di parole chiave con i loro sinonimi
    Usa LRU cache per evitare lookup ripetuti

    Args:
        keywords_tuple (tuple): Tupla di parole chiave (usa tuple per hashability)

    Returns:
        set: Set espanso con sinonimi
    """
    expanded = set()

    for keyword in keywords_tuple:
        # Aggiungi la parola originale
        expanded.add(keyword)

        # Aggiungi i sinonimi
        synonyms = get_synonyms(keyword)
        expanded.update(synonyms)

    return expanded


def parole_compatibili_con_sinonimi(parole_offerto, parole_cercato, usa_sinonimi=True):
    """
    Verifica compatibilità tra due set di parole considerando i sinonimi

    Args:
        parole_offerto (set): Parole chiave dell'offerta
        parole_cercato (set): Parole chiave della richiesta
        usa_sinonimi (bool): Se True, usa i sinonimi. Se False, solo match esatti/parziali

    Returns:
        tuple: (bool, str) - (compatibile, tipo_match)
            - tipo_match può essere: 'esatto', 'sinonimo', 'parziale', None
    """
    # 1. MATCH ESATTO: Tutte le parole richieste sono presenti esattamente
    parole_mancanti = parole_cercato - parole_offerto
    if not parole_mancanti:
        return True, 'esatto'

    # 2. MATCH CON SINONIMI (solo se abilitato)
    if usa_sinonimi:
        # Converti a tuple per poter usare la cache
        parole_offerto_tuple = tuple(sorted(parole_offerto))
        parole_cercato_tuple = tuple(sorted(parole_cercato))

        # Espandi con sinonimi (cached)
        offerto_expanded = expand_keywords_with_synonyms(parole_offerto_tuple)
        cercato_expanded = expand_keywords_with_synonyms(parole_cercato_tuple)

        # Controlla se tutte le parole richieste (o loro sinonimi) sono nell'offerta
        parole_mancanti_con_sinonimi = cercato_expanded - offerto_expanded

        if not parole_mancanti_con_sinonimi:
            # Verifica se è stato usato un sinonimo o se è match esatto
            if parole_mancanti:  # C'erano parole mancanti prima, ora no → sinonimi usati
                return True, 'sinonimo'
            else:
                return True, 'esatto'

        # 3. MATCH PARZIALE CON SINONIMI: Almeno una parola (o sinonimo) in comune
        parole_in_comune = offerto_expanded & cercato_expanded

        if parole_in_comune:
            # Controlla se ci sono parole significative (>3 caratteri)
            parole_significative = [p for p in parole_in_comune if len(p) > 3]
            if parole_significative:
                return True, 'parziale'
    else:
        # 3. MATCH PARZIALE SENZA SINONIMI: Controllo substring
        for parola_offerta in parole_offerto:
            for parola_cercata in parole_cercato:
                if ((parola_offerta in parola_cercata or parola_cercata in parola_offerta) and
                    len(parola_offerta) > 3 and len(parola_cercata) > 3):
                    return True, 'parziale'

    # 4. NESSUN MATCH
    return False, None


def get_cache_stats():
    """
    Ottiene statistiche sulla cache dei sinonimi
    Utile per debugging e ottimizzazione

    Returns:
        dict: Statistiche sulla cache
    """
    return {
        'get_synonyms_cache_info': get_synonyms.cache_info()._asdict(),
        'expand_keywords_cache_info': expand_keywords_with_synonyms.cache_info()._asdict(),
        'wordnet_available': _WORDNET_AVAILABLE
    }


def clear_cache():
    """
    Svuota la cache dei sinonimi
    Utile se WordNet viene aggiornato o per liberare memoria
    """
    get_synonyms.cache_clear()
    expand_keywords_with_synonyms.cache_clear()
    print(f"[{datetime.now()}] 🧹 Cache sinonimi svuotata")


# Inizializza WordNet al primo import del modulo
# Questo rende il primo lookup più veloce
initialize_wordnet()
