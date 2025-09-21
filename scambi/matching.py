from .models import Annuncio
from django.contrib.auth.models import User
from collections import defaultdict
import re

def trova_catene_scambio(max_lunghezza=6):
    """Trova catene di scambio con classificazione di qualità"""
    catene = trova_catene_ricorsive(max_lunghezza)
    return rimuovi_duplicati(catene)

def trova_catene_ricorsive(max_lunghezza=6):
    """Algoritmo per trovare catene con annunci dettagliati"""
    print(f"\n=== RICERCA CATENE CON CLASSIFICAZIONE QUALITÀ ===")
    
    utenti = list(User.objects.filter(annuncio__attivo=True).distinct())
    catene_trovate = []
    
    for utente_partenza in utenti:
        catene = cerca_catene_con_annunci(
            utente_partenza,
            utente_partenza, 
            [],
            [],
            utenti,
            max_lunghezza
        )
        catene_trovate.extend(catene)
    
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
        
        for offerta in offerte_correnti:
            for prossimo_utente in tutti_utenti:
                if prossimo_utente not in nuovo_percorso:
                    richieste_prossime = Annuncio.objects.filter(
                        utente=prossimo_utente,
                        tipo='cerco',
                        attivo=True
                    )
                    
                    for richiesta in richieste_prossime:
                        if oggetti_compatibili(offerta, richiesta):
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
    
    return catene

def verifica_chiusura_cerchio(utente_corrente, utente_partenza, percorso_utenti, percorso_annunci):
    """Verifica se può chiudere il cerchio e crea la catena completa"""
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
            if oggetti_compatibili(offerta, richiesta):
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
    testo_normalizzato = normalizza_testo(testo)
    
    # Stop words ridotte (solo le più comuni)
    stop_words = {'di', 'da', 'per', 'con', 'in', 'su', 'a', 'il', 'la', 'lo', 'e', 'o', 'del', 'della'}
    
    parole = set(testo_normalizzato.split()) - stop_words
    
    # Rimuovi parole troppo corte
    parole = {p for p in parole if len(p) > 2}
    
    return parole

def oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato):
    """Matching avanzato che restituisce anche il tipo di match"""
    
    # 1. MATCH SPECIFICO: Confronta titolo + descrizione
    testo_offerto = f"{annuncio_offerto.titolo} {annuncio_offerto.descrizione or ''}"
    testo_cercato = f"{annuncio_cercato.titolo} {annuncio_cercato.descrizione or ''}"
    
    parole_offerto = estrai_parole_chiave(testo_offerto)
    parole_cercato = estrai_parole_chiave(testo_cercato)
    
    # Controlla se ci sono parole in comune
    parole_comuni = parole_offerto & parole_cercato
    
    if parole_comuni:
        print(f"MATCH SPECIFICO: '{annuncio_offerto.titolo}' → '{annuncio_cercato.titolo}' (parole comuni: {parole_comuni})")
        return True, "specifico"
    
    # 2. MATCH PARZIALE: Alcune parole dell'offerta sono contenute nella ricerca
    for parola_offerta in parole_offerto:
        for parola_cercata in parole_cercato:
            if (parola_offerta in parola_cercata or 
                parola_cercata in parola_offerta and 
                len(parola_offerta) > 3 and len(parola_cercata) > 3):
                print(f"MATCH PARZIALE: '{annuncio_offerto.titolo}' → '{annuncio_cercato.titolo}' (parole simili: {parola_offerta} ~ {parola_cercata})")
                return True, "specifico"
    
    # 3. MATCH PER CATEGORIA: Stessa categoria
    if annuncio_offerto.categoria == annuncio_cercato.categoria:
        print(f"MATCH CATEGORIA: '{annuncio_offerto.titolo}' → '{annuncio_cercato.titolo}' ({annuncio_offerto.categoria.nome})")
        return True, "categoria"
    
    # 4. MATCH GENERICO: Cerco "qualsiasi cosa" di una categoria
    parole_generiche = {'qualsiasi', 'qualunque', 'qualcosa', 'oggetto', 'cosa', 'tutto', 'roba', 'qualcosè'}
    
    if (parole_generiche & parole_cercato and 
        annuncio_offerto.categoria == annuncio_cercato.categoria):
        print(f"MATCH GENERICO: '{annuncio_offerto.titolo}' → qualsiasi {annuncio_cercato.categoria.nome}")
        return True, "generico"
    
    return False, None

def oggetti_compatibili(annuncio_offerto, annuncio_cercato):
    """Wrapper per compatibilità"""
    compatible, _ = oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato)
    return compatible
