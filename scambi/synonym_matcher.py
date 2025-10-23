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

# Lista di termini composti comuni da preservare durante l'analisi
# Questi termini vengono cercati PRIMA di splittare in singole parole
COMPOUND_TERMS = {
    # Elettronica e tecnologia
    'macchina fotografica', 'fotocamera digitale', 'telefono cellulare', 'hard disk',
    'scheda madre', 'scheda video', 'carta di credito', 'chiavetta usb',
    'mouse wireless', 'tastiera meccanica', 'cuffie bluetooth', 'smart tv',
    'power bank', 'action cam', 'dash cam', 'ring light',

    # Casa e mobili
    'divano letto', 'tavolo da pranzo', 'sedia da ufficio', 'lampada da terra',
    'mobile tv', 'armadio guardaroba', 'specchio da parete', 'tappeto persiano',

    # Sport e tempo libero
    'racchetta da tennis', 'mountain bike', 'bici da corsa', 'tavola da surf',
    'sci da discesa', 'pattini a rotelle', 'borsa da palestra', 'scarpe da ginnastica',
    'pallone da calcio', 'tuta da sci',

    # Musica
    'chitarra elettrica', 'chitarra acustica', 'tastiera elettronica', 'cassa bluetooth',

    # Libri e giochi
    'gioco da tavolo', 'libro di testo', 'fumetto manga', 'console portatile',

    # Vari
    'macchina da caffè', 'ferro da stiro', 'asciuga capelli', 'macchina per cucire',
}

# Normalizza i termini composti (tutto minuscolo)
COMPOUND_TERMS = {term.lower() for term in COMPOUND_TERMS}


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


def extract_compound_terms(text):
    """
    Estrae termini composti da un testo prima di splittarlo in singole parole

    Args:
        text (str): Testo da analizzare

    Returns:
        set: Insieme di termini composti trovati nel testo
    """
    text_lower = text.lower()
    found_compounds = set()

    # Cerca ogni termine composto nel testo
    for compound in COMPOUND_TERMS:
        if compound in text_lower:
            found_compounds.add(compound)

    return found_compounds


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


def check_synonym_match(parole_offerto, parole_cercato):
    """
    Verifica se le parole cercate hanno sinonimi nelle parole offerte

    Args:
        parole_offerto (set): Parole chiave dell'offerta
        parole_cercato (set): Parole chiave della richiesta

    Returns:
        tuple: (bool, str) - (compatibile, 'sinonimo' o None)
    """
    # Se WordNet non è disponibile, salta il check
    if not _WORDNET_AVAILABLE:
        return False, None

    # Espandi le parole cercate con sinonimi
    parole_cercato_espanse = set()
    for parola in parole_cercato:
        # Solo parole significative (>2 caratteri) vengono espanse
        if len(parola) > 2:
            sinonimi = get_synonyms(parola)
            parole_cercato_espanse.update(sinonimi)
        else:
            parole_cercato_espanse.add(parola)

    # Espandi anche le parole offerte per match bidirezionale
    parole_offerto_espanse = set()
    for parola in parole_offerto:
        if len(parola) > 2:
            sinonimi = get_synonyms(parola)
            parole_offerto_espanse.update(sinonimi)
        else:
            parole_offerto_espanse.add(parola)

    # Trova match tra sinonimi
    match_trovati = parole_offerto_espanse & parole_cercato_espanse

    if match_trovati:
        # Verifica se ci sono parole significative (>3 caratteri) o numeri
        parole_significative = [p for p in match_trovati if len(p) > 3 or p.isdigit()]
        if parole_significative:
            return True, 'sinonimo'

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
        'wordnet_available': _WORDNET_AVAILABLE
    }


def clear_cache():
    """
    Svuota la cache dei sinonimi
    Utile se WordNet viene aggiornato o per liberare memoria
    """
    get_synonyms.cache_clear()
    print(f"[{datetime.now()}] 🧹 Cache sinonimi svuotata")


# Inizializza WordNet al primo import del modulo
# Questo rende il primo lookup più veloce
initialize_wordnet()
