from .models import Annuncio
from django.contrib.auth.models import User
from collections import defaultdict
import re

def trova_catene_scambio(max_lunghezza=6):
    """Trova catene di scambio con classificazione di qualità"""
    print("\n=== DEBUG: Inizio ricerca catene ===")
    catene = trova_catene_ricorsive(max_lunghezza)
    print(f"=== DEBUG: Catene trovate: {len(catene)} ===")
    return rimuovi_duplicati(catene)

def trova_catene_ricorsive(max_lunghezza=6):
    """Algoritmo per trovare catene con annunci dettagliati"""
    print(f"\n=== RICERCA CATENE CON CLASSIFICAZIONE QUALITÀ ===")
    
    utenti = list(User.objects.filter(annuncio__attivo=True).distinct())
    print(f"DEBUG: Trovati {len(utenti)} utenti con annunci attivi")
    
    catene_trovate = []
    
    for utente_partenza in utenti:
        print(f"DEBUG: Inizio ricerca da utente {utente_partenza.username}")
        catene = cerca_catene_con_annunci(
            utente_partenza,
            utente_partenza, 
            [],
            [],
            utenti,
            max_lunghezza
        )
        catene_trovate.extend(catene)
        print(f"DEBUG: Utente {utente_partenza.username} ha generato {len(catene)} catene")
    
    print(f"Trovate {len(catene_trovate)} catene complete")
    return catene_trovate

def cerca_catene_con_annunci(utente_corrente, utente_partenza, percorso_utenti, percorso_annunci, tutti_utenti, max_lunghezza):
    """Ricerca catene includendo gli annunci specifici"""
    catene = []
    
    if len(percorso_utenti) > max_lunghezza:
        return catene
    
    nuovo_percorso = percorso_utenti + [utente_corrente]
    
    if len(nuovo_percorso) >= 3:
        catena_completa = verifica_chiusura_cerchio(
            utente_corrente, 
            utente_partenza, 
            nuovo_percorso, 
            percorso_annunci
        )
        if catena_completa:
            catene.append(catena_completa)
    
    if len(nuovo_percorso) < max_lunghezza:
        offerte_correnti = Annuncio.objects.filter(
            utente=utente_corrente, 
            tipo='offro', 
            attivo=True
        )
        
        print(f"DEBUG: {utente_corrente.username} ha {len(offerte_correnti)} offerte")
        
        for offerta in offerte_correnti:
            print(f"DEBUG: Controllo offerta '{offerta.titolo}' di {utente_corrente.username}")
            
            for prossimo_utente in tutti_utenti:
                if prossimo_utente not in nuovo_percorso:
                    richieste_prossime = Annuncio.objects.filter(
                        utente=prossimo_utente,
                        tipo='cerco',
                        attivo=True
                    )
                    
                    print(f"DEBUG: {prossimo_utente.username} ha {len(richieste_prossime)} richieste")
                    
                    for richiesta in richieste_prossime:
                        print(f"DEBUG: Confronto '{offerta.titolo}' con '{richiesta.titolo}'")
                        
                        if oggetti_compatibili(offerta, richiesta):
                            print(f"DEBUG: MATCH TROVATO! {offerta.titolo} → {richiesta.titolo}")
                            
                            nuovi_annunci = percorso_annunci + [{
                                'da': utente_corrente,
                                'a': prossimo_utente,
                                'annuncio_offro': offerta,
                                'annuncio_cerco': richiesta
                            }]
                            
                            catene_ricorsive = cerca_catene_con_annunci(
                                prossimo_utente,
                                utente_partenza,
                                nuovo_percorso,
                                nuovi_annunci,
                                tutti_utenti,
                                max_lunghezza
                            )
                            catene.extend(catene_ricorsive)
                        else:
                            print(f"DEBUG: NO MATCH tra '{offerta.titolo}' e '{richiesta.titolo}'")
    
    return catene

def verifica_chiusura_cerchio(utente_corrente, utente_partenza, percorso_utenti, percorso_annunci):
    """Verifica se può chiudere il cerchio e crea la catena completa"""
    print(f"DEBUG: Verifica chiusura cerchio da {utente_corrente.username} verso {utente_partenza.username}")
    
    offerte_correnti = Annuncio.objects.filter(
        utente=utente_corrente,
        tipo='offro', 
        attivo=True
    )
    
    richieste_partenza = Annuncio.objects.filter(
        utente=utente_partenza,
        tipo='cerco',
        attivo=True
    )
    
    for offerta in offerte_correnti:
        for richiesta in richieste_partenza:
            print(f"DEBUG: Chiusura? '{offerta.titolo}' vs '{richiesta.titolo}'")
            if oggetti_compatibili(offerta, richiesta):
                print(f"DEBUG: CERCHIO CHIUSO! {offerta.titolo} → {richiesta.titolo}")
                annunci_completi = percorso_annunci + [{
                    'da': utente_corrente,
                    'a': utente_partenza, 
                    'annuncio_offro': offerta,
                    'annuncio_cerco': richiesta
                }]
                
                return crea_catena_dettagliata(percorso_utenti, annunci_completi)
    
    return None

def crea_catena_dettagliata(percorso_utenti, annunci_scambi):
    """Crea la rappresentazione dettagliata della catena con classificazione qualità"""
    scambi_dettagliati = []
    annunci_coinvolti = []
    punteggio_qualita = 0
    tipi_match = []
    
    for scambio in annunci_scambi:
        _, tipo_match = oggetti_compatibili_con_tipo(scambio['annuncio_offro'], scambio['annuncio_cerco'])
        tipi_match.append(tipo_match)
        
        # Assegna punteggi: specifico=3, categoria=2, generico=1
        if tipo_match == "specifico":
            punteggio_qualita += 3
        elif tipo_match == "categoria":
            punteggio_qualita += 2
        elif tipo_match == "generico":
            punteggio_qualita += 1
        
        scambi_dettagliati.extend([
            f"{scambio['da'].username} dà: {scambio['annuncio_offro'].titolo}",
            f"{scambio['a'].username} riceve: {scambio['annuncio_offro'].titolo}"
        ])
        
        annunci_coinvolti.extend([
            {
                'annuncio': scambio['annuncio_offro'],
                'ruolo': 'offre',
                'utente': scambio['da'].username,
                'tipo_match': tipo_match
            },
            {
                'annuncio': scambio['annuncio_cerco'], 
                'ruolo': 'cerca',
                'utente': scambio['a'].username,
                'tipo_match': tipo_match
            }
        ])
    
    # Determina categoria di qualità
    num_scambi = len(annunci_scambi)
    punteggio_medio = punteggio_qualita / num_scambi if num_scambi > 0 else 0
    
    if punteggio_medio >= 2.5:
        categoria_qualita = "alta"
    else:
        categoria_qualita = "generica"
    
    return {
        'tipo': f'catena_{len(percorso_utenti)}_persone',
        'utenti': [u.username for u in percorso_utenti],
        'scambi': scambi_dettagliati,
        'annunci_coinvolti': annunci_coinvolti,
        'categoria_qualita': categoria_qualita,
        'punteggio_qualita': punteggio_qualita,
        'tipi_match': tipi_match
    }

def rimuovi_duplicati(catene):
    """Rimuove catene duplicate"""
    catene_uniche = []
    combinazioni_viste = set()
    
    for catena in catene:
        utenti_ordinati = tuple(sorted(catena['utenti']))
        if utenti_ordinati not in combinazioni_viste:
            combinazioni_viste.add(utenti_ordinati)
            catene_uniche.append(catena)
    
    return catene_uniche

def normalizza_testo(testo):
    """Normalizza il testo per il matching"""
    # Converti in minuscolo
    testo = testo.lower()
    
    # Rimuovi prefissi comuni
    prefissi = ['vendo ', 'offro ', 'cerco ', 'cerca ', 'scambio ']
    for prefisso in prefissi:
        if testo.startswith(prefisso):
            testo = testo[len(prefisso):]
    
    # Rimuovi punteggiatura e caratteri speciali
    testo = re.sub(r'[^\w\s]', ' ', testo)
    
    # Rimuovi spazi multipli
    testo = ' '.join(testo.split())
    
    return testo

def estrai_parole_chiave(testo):
    """Estrae le parole chiave significative dal testo"""
    print(f"🔧 ESTRAZIONE PAROLE da: '{testo}'")

    testo_normalizzato = normalizza_testo(testo)
    print(f"🔧 Testo normalizzato: '{testo_normalizzato}'")

    # Stop words ridotte (solo le più comuni)
    stop_words = {'di', 'da', 'per', 'con', 'in', 'su', 'a', 'il', 'la', 'lo', 'e', 'o', 'del', 'della'}

    parole_base = set(testo_normalizzato.split())
    print(f"🔧 Parole base: {parole_base}")

    parole_senza_stop = parole_base - stop_words
    print(f"🔧 Senza stop words: {parole_senza_stop}")

    # Rimuovi parole troppo corte
    parole_finali = {p for p in parole_senza_stop if len(p) > 2}
    print(f"🔧 Parole finali (>2 caratteri): {parole_finali}")

    return parole_finali

def oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato):
    """Matching avanzato che restituisce anche il tipo di match"""

    print(f"\n🔍 DEBUG: === CONTROLLO COMPATIBILITÀ ===")
    print(f"🔍 Offerto - Titolo: '{annuncio_offerto.titolo}', Descrizione: '{annuncio_offerto.descrizione or 'VUOTA'}'")
    print(f"🔍 Cercato - Titolo: '{annuncio_cercato.titolo}', Descrizione: '{annuncio_cercato.descrizione or 'VUOTA'}'")
    print(f"🔍 Categorie - Offerto: '{annuncio_offerto.categoria}', Cercato: '{annuncio_cercato.categoria}'")

    # 1. MATCH SPECIFICO: Confronta titolo + descrizione
    testo_offerto = f"{annuncio_offerto.titolo} {annuncio_offerto.descrizione or ''}"
    testo_cercato = f"{annuncio_cercato.titolo} {annuncio_cercato.descrizione or ''}"

    print(f"🔍 Testo completo offerto: '{testo_offerto}'")
    print(f"🔍 Testo completo cercato: '{testo_cercato}'")

    parole_offerto = estrai_parole_chiave(testo_offerto)
    parole_cercato = estrai_parole_chiave(testo_cercato)

    print(f"🔍 Parole chiave offerto: {parole_offerto}")
    print(f"🔍 Parole chiave cercato: {parole_cercato}")

    # Controlla se ci sono parole in comune
    parole_comuni = parole_offerto & parole_cercato
    print(f"🔍 Parole in comune trovate: {parole_comuni}")

    if parole_comuni:
        print(f"✅ MATCH SPECIFICO: '{annuncio_offerto.titolo}' → '{annuncio_cercato.titolo}' (parole comuni: {parole_comuni})")
        return True, "specifico"

    # 2. MATCH PARZIALE: Alcune parole dell'offerta sono contenute nella ricerca
    print(f"🔍 Controllo match parziale...")
    for parola_offerta in parole_offerto:
        for parola_cercata in parole_cercato:
            print(f"🔍 Confronto parziale: '{parola_offerta}' vs '{parola_cercata}'")
            if ((parola_offerta in parola_cercata or parola_cercata in parola_offerta) and
                len(parola_offerta) > 3 and len(parola_cercata) > 3):
                print(f"✅ MATCH PARZIALE: '{annuncio_offerto.titolo}' → '{annuncio_cercato.titolo}' (parole simili: {parola_offerta} ~ {parola_cercata})")
                return True, "parziale"

    # 3. MATCH PER CATEGORIA: Stessa categoria
    print(f"🔍 Controllo match per categoria...")
    print(f"🔍 Categoria offerto: '{annuncio_offerto.categoria}' (ID: {annuncio_offerto.categoria.id if annuncio_offerto.categoria else 'None'})")
    print(f"🔍 Categoria cercato: '{annuncio_cercato.categoria}' (ID: {annuncio_cercato.categoria.id if annuncio_cercato.categoria else 'None'})")

    if annuncio_offerto.categoria == annuncio_cercato.categoria:
        print(f"✅ MATCH CATEGORIA: '{annuncio_offerto.titolo}' → '{annuncio_cercato.titolo}' ({annuncio_offerto.categoria.nome})")
        return True, "categoria"

    # 4. MATCH GENERICO: Cerco "qualsiasi cosa" di una categoria
    print(f"🔍 Controllo match generico...")
    parole_generiche = {'qualsiasi', 'qualunque', 'qualcosa', 'oggetto', 'cosa', 'tutto', 'roba'}
    parole_generiche_trovate = parole_generiche & parole_cercato
    print(f"🔍 Parole generiche nel cercato: {parole_generiche_trovate}")

    if (parole_generiche_trovate and
        annuncio_offerto.categoria == annuncio_cercato.categoria):
        print(f"✅ MATCH GENERICO: '{annuncio_offerto.titolo}' → qualsiasi {annuncio_cercato.categoria.nome}")
        return True, "generico"

    print(f"❌ NESSUN MATCH trovato")
    return False, None

def oggetti_compatibili(annuncio_offerto, annuncio_cercato):
    """Wrapper per compatibilità"""
    compatible, _ = oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato)
    return compatible
