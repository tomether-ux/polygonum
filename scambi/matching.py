from .models import Annuncio, UserProfile
from django.contrib.auth.models import User
from collections import defaultdict
import re
import math

def trova_scambi_diretti():
    """Trova scambi diretti tra 2 persone (massima priorità) - VERSIONE OTTIMIZZATA"""
    print("\n🔄 === RICERCA SCAMBI DIRETTI OTTIMIZZATA (2 PERSONE) ===")

    # Ottimizzazione: Limita gli utenti anche per scambi diretti
    utenti = list(User.objects.filter(annuncio__attivo=True).distinct())
    print(f"🔍 Trovati {len(utenti)} utenti totali")

    if len(utenti) > 10:
        print(f"⚡ Limitando a 10 utenti per stabilità massima")
        utenti = utenti[:10]

    scambi_diretti = []

    # Timeout per scambi diretti
    import time
    start_time = time.time()
    timeout_scambi_diretti = 5.0  # 5 secondi max per scambi diretti (ultra-sicuro)

    iterazioni_totali = 0
    max_iterazioni = 1000  # Limite massimo di iterazioni per sicurezza (ridotto)

    for i, utente_a in enumerate(utenti):
        if time.time() - start_time > timeout_scambi_diretti:
            print(f"⏰ Timeout scambi diretti raggiunto dopo {i} utenti")
            break

        if iterazioni_totali > max_iterazioni:
            print(f"🛡️ Limite iterazioni raggiunto ({max_iterazioni}) per sicurezza")
            break

        for utente_b in utenti:
            iterazioni_totali += 1
            if utente_a == utente_b:
                continue

            # Check timeout e iterazioni anche nel loop interno
            if time.time() - start_time > timeout_scambi_diretti:
                print(f"⏰ Timeout scambi diretti raggiunto nel loop interno")
                break

            if iterazioni_totali > max_iterazioni:
                print(f"🛡️ Limite iterazioni raggiunto nel loop interno")
                break

            # Trova cosa offre A e cosa cerca B
            offerte_a = Annuncio.objects.filter(utente=utente_a, tipo='offro', attivo=True)
            richieste_b = Annuncio.objects.filter(utente=utente_b, tipo='cerco', attivo=True)

            # Trova cosa offre B e cosa cerca A
            offerte_b = Annuncio.objects.filter(utente=utente_b, tipo='offro', attivo=True)
            richieste_a = Annuncio.objects.filter(utente=utente_a, tipo='cerco', attivo=True)

            # Calcola distanza geografica tra i due utenti
            distanza_km, categoria_distanza = calcola_distanza_geografica(utente_a, utente_b)

            # Verifica match A→B e B→A con algoritmo avanzato
            for offerta_a in offerte_a:
                for richiesta_b in richieste_b:
                    # Usa algoritmo avanzato per A→B
                    compatible_ab, punteggio_ab, dettagli_ab = oggetti_compatibili_avanzato(offerta_a, richiesta_b, distanza_km)

                    if compatible_ab:
                        # A offre quello che B cerca, ora verifica il contrario
                        for offerta_b in offerte_b:
                            for richiesta_a in richieste_a:
                                # Usa algoritmo avanzato per B→A
                                compatible_ba, punteggio_ba, dettagli_ba = oggetti_compatibili_avanzato(offerta_b, richiesta_a, distanza_km)

                                if compatible_ba:
                                    # Scambio diretto trovato con algoritmo avanzato!
                                    punteggio_totale = (punteggio_ab + punteggio_ba) / 2

                                    scambio = crea_scambio_diretto_avanzato(
                                        utente_a, utente_b,
                                        offerta_a, richiesta_b,
                                        offerta_b, richiesta_a,
                                        distanza_km, punteggio_totale,
                                        dettagli_ab, dettagli_ba
                                    )

                                    # Evita duplicati (A-B è uguale a B-A)
                                    utenti_coppia = tuple(sorted([utente_a.username, utente_b.username]))

                                    # Controlla se questa coppia è già stata aggiunta
                                    gia_presente = any(
                                        tuple(sorted(s['utenti'])) == utenti_coppia
                                        for s in scambi_diretti
                                    )

                                    if not gia_presente:
                                        scambi_diretti.append(scambio)
                                        print(f"💫 SCAMBIO DIRETTO: {utente_a.username} ↔ {utente_b.username}")
                                        print(f"   📤 {utente_a.username} dà '{offerta_a.titolo}' → {utente_b.username}")
                                        print(f"   📤 {utente_b.username} dà '{offerta_b.titolo}' → {utente_a.username}")

    print(f"💫 Trovati {len(scambi_diretti)} scambi diretti")
    return scambi_diretti

def filtra_catene_per_utente(scambi_diretti, catene_lunghe, utente):
    """Filtra le catene di scambio per mostrare solo quelle rilevanti per l'utente specificato"""

    # Ottieni annunci dell'utente
    annunci_utente = list(Annuncio.objects.filter(utente=utente, attivo=True))
    annunci_utente_ids = set(ann.id for ann in annunci_utente)

    print(f"🔍 Filtraggio per utente {utente.username}: {len(annunci_utente)} annunci attivi")

    # Se l'utente non ha annunci, non può partecipare a nessuno scambio
    if not annunci_utente_ids:
        print(f"❌ Utente {utente.username} non ha annunci attivi - nessuno scambio possibile")
        return [], []

    # Filtra scambi diretti
    scambi_diretti_utente = []
    for scambio in scambi_diretti:
        # Controlla se l'utente è coinvolto nel scambio
        utenti_coinvolti = scambio['utenti']
        if utente.username in utenti_coinvolti:
            # Verifica che almeno uno dei suoi annunci sia coinvolto
            annunci_coinvolti_ids = set(item['annuncio'].id for item in scambio['annunci_coinvolti'])
            if annunci_coinvolti_ids.intersection(annunci_utente_ids):
                scambi_diretti_utente.append(scambio)
                print(f"✅ Scambio diretto incluso: {utenti_coinvolti}")
            else:
                print(f"❌ Scambio escluso: utente nel nome ma annunci non corrispondono")

    # Filtra catene lunghe
    catene_utente = []
    for catena in catene_lunghe:
        # Controlla se l'utente è nella catena
        utenti_catena = catena['utenti']
        if utente.username in utenti_catena:
            # Verifica che almeno uno dei suoi annunci sia coinvolto
            annunci_coinvolti_ids = set(item['annuncio'].id for item in catena['annunci_coinvolti'])
            if annunci_coinvolti_ids.intersection(annunci_utente_ids):
                catene_utente.append(catena)
                print(f"✅ Catena lunga inclusa: {len(utenti_catena)} persone")
            else:
                print(f"❌ Catena esclusa: utente nel nome ma annunci non corrispondono")

    print(f"📊 Risultati filtrati per {utente.username}:")
    print(f"   - Scambi diretti: {len(scambi_diretti_utente)}")
    print(f"   - Catene lunghe: {len(catene_utente)}")

    return scambi_diretti_utente, catene_utente

def crea_scambio_diretto(utente_a, utente_b, offerta_a, richiesta_b, offerta_b, richiesta_a):
    """Crea la struttura dati per uno scambio diretto"""

    # Calcola punteggio qualità degli oggetti
    _, tipo_match_1 = oggetti_compatibili_con_tipo(offerta_a, richiesta_b)
    _, tipo_match_2 = oggetti_compatibili_con_tipo(offerta_b, richiesta_a)

    punteggio_match_1 = {"specifico": 10, "sinonimo": 9, "parziale": 8, "categoria": 6, "generico": 4}.get(tipo_match_1, 0)
    punteggio_match_2 = {"specifico": 10, "sinonimo": 9, "parziale": 8, "categoria": 6, "generico": 4}.get(tipo_match_2, 0)

    # Calcola punteggio distanza geografica
    distanza_km, tipo_distanza = calcola_distanza_geografica(utente_a, utente_b)
    categoria_distanza, bonus_distanza = classifica_distanza(distanza_km)

    # Calcola punteggio finale combinando match oggetti + distanza
    punteggio_oggetti = (punteggio_match_1 + punteggio_match_2) / 2
    punteggio_qualita = (punteggio_oggetti * 0.7) + (bonus_distanza * 0.3)  # 70% oggetti, 30% distanza

    # Se c'è anche un solo match "categoria" o "generico", lo scambio è generico
    ha_match_non_specifici = any(match in ["categoria", "generico"] for match in [tipo_match_1, tipo_match_2])

    if ha_match_non_specifici:
        categoria_qualita = "generica"
    else:
        categoria_qualita = "alta" if punteggio_qualita >= 7 else "generica"

    return {
        'tipo': 'scambio_diretto',
        'utenti': [utente_a.username, utente_b.username],
        'scambi': [
            f"{utente_a.username} dà '{offerta_a.titolo}' a {utente_b.username}",
            f"{utente_b.username} dà '{offerta_b.titolo}' a {utente_a.username}"
        ],
        'annunci_coinvolti': [
            {'utente': utente_a.username, 'annuncio': offerta_a, 'ruolo': 'offre'},
            {'utente': utente_b.username, 'annuncio': richiesta_b, 'ruolo': 'cerca'},
            {'utente': utente_b.username, 'annuncio': offerta_b, 'ruolo': 'offre'},
            {'utente': utente_a.username, 'annuncio': richiesta_a, 'ruolo': 'cerca'}
        ],
        'categoria_qualita': categoria_qualita,
        'punteggio_qualita': punteggio_qualita,
        'tipi_match': [tipo_match_1, tipo_match_2],
        'distanza_km': distanza_km,
        'categoria_distanza': categoria_distanza,
        'tipo_distanza': tipo_distanza
    }

def crea_scambio_diretto_avanzato(utente_a, utente_b, offerta_a, richiesta_b, offerta_b, richiesta_a,
                                distanza_km, punteggio_totale, dettagli_ab, dettagli_ba):
    """Crea la struttura dati per uno scambio diretto con algoritmo avanzato"""

    # Verifica se ci sono match per sola categoria o generici
    _, tipo_match_1 = oggetti_compatibili_con_tipo(offerta_a, richiesta_b)
    _, tipo_match_2 = oggetti_compatibili_con_tipo(offerta_b, richiesta_a)

    ha_match_non_specifici = any(match in ["categoria", "generico"] for match in [tipo_match_1, tipo_match_2])
    ha_sinonimi = any(match == "sinonimo" for match in [tipo_match_1, tipo_match_2])

    if ha_match_non_specifici:
        categoria_qualita = "generica"
    else:
        categoria_qualita = "alta" if punteggio_totale >= 60 else "generica"

    # Raggruppa dettagli per categorie
    dettagli_prezzo = []
    dettagli_metodo = []
    dettagli_distanza = []

    for dettaglio in dettagli_ab + dettagli_ba:
        if "prezzo" in str(dettaglio) or "compatibili" in str(dettaglio) or "non_specificato" in str(dettaglio):
            dettagli_prezzo.append(dettaglio)
        elif "mano" in str(dettaglio) or "spedizione" in str(dettaglio) or "flessibile" in str(dettaglio):
            dettagli_metodo.append(dettaglio)
        elif "distanza" in str(dettaglio) or "km" in str(dettaglio):
            dettagli_distanza.append(dettaglio)

    return {
        'tipo': 'scambio_diretto',
        'utenti': [utente_a.username, utente_b.username],
        'scambi': [
            f"{utente_a.username} dà '{offerta_a.titolo}' a {utente_b.username}",
            f"{utente_b.username} dà '{offerta_b.titolo}' a {utente_a.username}"
        ],
        'annunci_coinvolti': [
            {'utente': utente_a.username, 'annuncio': offerta_a, 'ruolo': 'offre'},
            {'utente': utente_b.username, 'annuncio': richiesta_b, 'ruolo': 'cerca'},
            {'utente': utente_b.username, 'annuncio': offerta_b, 'ruolo': 'offre'},
            {'utente': utente_a.username, 'annuncio': richiesta_a, 'ruolo': 'cerca'}
        ],
        'categoria_qualita': categoria_qualita,
        'punteggio_qualita': punteggio_totale,
        'distanza_km': distanza_km,
        'dettagli_prezzo': dettagli_prezzo,
        'dettagli_metodo': dettagli_metodo,
        'dettagli_distanza': dettagli_distanza,

        # Informazioni aggiuntive sugli oggetti per il display
        'prezzo_offerto_a': offerta_a.prezzo_stimato,
        'prezzo_offerto_b': offerta_b.prezzo_stimato,
        'metodo_a': offerta_a.metodo_scambio,
        'metodo_b': offerta_b.metodo_scambio,
        'distanza_limite_a': offerta_a.distanza_massima_km,
        'distanza_limite_b': offerta_b.distanza_massima_km,
        'usa_sinonimi': ha_sinonimi  # Flag per filtraggio UI
    }

def trova_catene_per_annuncio(annuncio_specifico, max_lunghezza=6):
    """Trova catene che coinvolgono uno specifico annuncio - OTTIMIZZATO"""
    print(f"\n=== RICERCA OTTIMIZZATA PER ANNUNCIO: {annuncio_specifico.titolo} ===")

    utente_proprietario = annuncio_specifico.utente
    catene_trovate = []

    # 1. Cerca scambi diretti che coinvolgono questo annuncio
    print("🔍 Cercando scambi diretti per l'annuncio specifico...")

    utenti = list(User.objects.filter(annuncio__attivo=True).distinct())[:10]  # Limite per performance

    for altro_utente in utenti:
        if altro_utente == utente_proprietario:
            continue

        # Se l'annuncio è "offro", cerca chi cerca qualcosa di compatibile
        if annuncio_specifico.tipo == 'offro':
            richieste_altri = Annuncio.objects.filter(utente=altro_utente, tipo='cerco', attivo=True)
            for richiesta in richieste_altri:
                if oggetti_compatibili(annuncio_specifico, richiesta):
                    # Controlla se c'è uno scambio di ritorno
                    offerte_altri = Annuncio.objects.filter(utente=altro_utente, tipo='offro', attivo=True)
                    richieste_proprietario = Annuncio.objects.filter(utente=utente_proprietario, tipo='cerco', attivo=True)

                    for offerta_altro in offerte_altri:
                        for richiesta_proprietario in richieste_proprietario:
                            if oggetti_compatibili(offerta_altro, richiesta_proprietario):
                                # Scambio diretto trovato!
                                scambio = crea_scambio_diretto(
                                    utente_proprietario, altro_utente,
                                    annuncio_specifico, richiesta,
                                    offerta_altro, richiesta_proprietario
                                )
                                catene_trovate.append(scambio)
                                print(f"✅ Scambio diretto: {utente_proprietario.username} ↔ {altro_utente.username}")

        # Se l'annuncio è "cerco", cerca chi offre qualcosa di compatibile
        elif annuncio_specifico.tipo == 'cerco':
            offerte_altri = Annuncio.objects.filter(utente=altro_utente, tipo='offro', attivo=True)
            for offerta in offerte_altri:
                if oggetti_compatibili(offerta, annuncio_specifico):
                    # Controlla se c'è uno scambio di ritorno
                    offerte_proprietario = Annuncio.objects.filter(utente=utente_proprietario, tipo='offro', attivo=True)
                    richieste_altri = Annuncio.objects.filter(utente=altro_utente, tipo='cerco', attivo=True)

                    for offerta_proprietario in offerte_proprietario:
                        for richiesta_altro in richieste_altri:
                            if oggetti_compatibili(offerta_proprietario, richiesta_altro):
                                # Scambio diretto trovato!
                                scambio = crea_scambio_diretto(
                                    altro_utente, utente_proprietario,
                                    offerta, annuncio_specifico,
                                    offerta_proprietario, richiesta_altro
                                )
                                catene_trovate.append(scambio)
                                print(f"✅ Scambio diretto: {altro_utente.username} ↔ {utente_proprietario.username}")

    print(f"=== RICERCA OTTIMIZZATA: Trovati {len(catene_trovate)} scambi per '{annuncio_specifico.titolo}' ===")
    return rimuovi_duplicati(catene_trovate)

def trova_catene_scambio(max_lunghezza=6):
    """Trova catene di scambio con classificazione di qualità"""
    print("\n=== DEBUG: Inizio ricerca catene ===")

    # 1. Prima trova scambi diretti (priorità massima)
    scambi_diretti = trova_scambi_diretti()

    # 2. Poi trova catene lunghe
    catene_lunghe = trova_catene_ricorsive(max_lunghezza)

    # 3. Combina i risultati (scambi diretti hanno priorità)
    tutte_catene = scambi_diretti + catene_lunghe

    print(f"=== DEBUG: Totale trovato: {len(scambi_diretti)} scambi diretti + {len(catene_lunghe)} catene lunghe ===")
    return rimuovi_duplicati(tutte_catene)

def rimuovi_duplicati(catene):
    """Rimuove duplicati dalle catene basandosi su utenti coinvolti"""
    catene_uniche = []
    combinazioni_viste = set()

    for catena in catene:
        # Crea una chiave univoca basata sugli utenti ordinati
        utenti_ordinati = tuple(sorted(catena['utenti']))

        # Evita duplicati
        if utenti_ordinati not in combinazioni_viste:
            combinazioni_viste.add(utenti_ordinati)
            catene_uniche.append(catena)

    print(f"🔧 Deduplicazione: {len(catene)} → {len(catene_uniche)} catene uniche")
    return catene_uniche

def trova_catene_ricorsive(max_lunghezza=3):
    """Algoritmo per trovare catene con annunci dettagliati - VERSIONE OTTIMIZZATA"""
    import time

    print(f"\n=== RICERCA CATENE CON CLASSIFICAZIONE QUALITÀ (MAX {max_lunghezza} UTENTI) ===")

    utenti = list(User.objects.filter(annuncio__attivo=True).distinct())
    print(f"DEBUG: Trovati {len(utenti)} utenti con annunci attivi")

    # OTTIMIZZAZIONE AVANZATA: Limita ulteriormente per velocità
    if len(utenti) > 8:
        print(f"⚠️ Troppi utenti ({len(utenti)}), limitando a 8 per stabilità massima")
        # Ordina per numero di annunci attivi (utenti più attivi hanno priorità)
        utenti_con_count = []
        for utente in utenti:
            count_annunci = Annuncio.objects.filter(utente=utente, attivo=True).count()
            utenti_con_count.append((utente, count_annunci))

        # Prendi i 8 utenti con più annunci attivi
        utenti_con_count.sort(key=lambda x: x[1], reverse=True)
        utenti = [u[0] for u in utenti_con_count[:8]]
        print(f"🎯 Selezionati i 8 utenti più attivi")

    catene_trovate = []
    start_time = time.time()
    timeout_per_utente = 1.0  # 1 secondo max per utente (ultra-sicuro)
    timeout_totale = 8.0      # 8 secondi totali (ultra-sicuro per evitare errori)

    iterazioni_ricorsive = 0
    max_iterazioni_ricorsive = 500  # Limite per catene ricorsive (ridotto)

    for i, utente_partenza in enumerate(utenti):
        if time.time() - start_time > timeout_totale:
            print(f"⏰ Timeout totale raggiunto dopo {i} utenti")
            break

        print(f"DEBUG: Inizio ricerca da utente {utente_partenza.username} ({i+1}/{len(utenti)})")

        utente_start_time = time.time()
        try:
            catene = cerca_catene_con_annunci(
                utente_partenza,
                utente_partenza,
                [],
                [],
                utenti,
                max_lunghezza,
                timeout_per_utente,
                utente_start_time
            )
            catene_trovate.extend(catene)
            print(f"DEBUG: Utente {utente_partenza.username} ha generato {len(catene)} catene")
        except Exception as e:
            print(f"⚠️ Errore durante ricerca per {utente_partenza.username}: {e}")
            continue

    elapsed = time.time() - start_time
    print(f"Trovate {len(catene_trovate)} catene complete in {elapsed:.1f} secondi")
    return catene_trovate

def cerca_catene_con_annunci(utente_corrente, utente_partenza, percorso_utenti, percorso_annunci, tutti_utenti, max_lunghezza, timeout_per_utente=None, start_time=None):
    """Ricerca catene includendo gli annunci specifici - VERSIONE OTTIMIZZATA"""
    import time
    catene = []

    # Controllo timeout per utente
    if timeout_per_utente and start_time and (time.time() - start_time > timeout_per_utente):
        print(f"⏰ Timeout per utente raggiunto")
        return catene

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
                                max_lunghezza,
                                timeout_per_utente,
                                start_time
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
        
        # Assegna punteggi: specifico=3, sinonimo=2.5, parziale=2.5, categoria=2, generico=1
        if tipo_match == "specifico":
            punteggio_qualita += 3
        elif tipo_match == "sinonimo":
            punteggio_qualita += 2.5
        elif tipo_match == "parziale":
            punteggio_qualita += 2.5
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

    # Se c'è anche un solo match "categoria" o "generico", la catena è generica
    ha_match_non_specifici = any(match in ["categoria", "generico"] for match in tipi_match)

    # Controlla se ci sono match tramite sinonimi
    ha_sinonimi = any(match == "sinonimo" for match in tipi_match)

    if ha_match_non_specifici:
        categoria_qualita = "generica"
    elif punteggio_medio >= 2.5:
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
        'tipi_match': tipi_match,
        'usa_sinonimi': ha_sinonimi  # Flag per filtraggio UI
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
    """Estrae le parole chiave significative dal testo, preservando termini composti"""
    print(f"🔧 ESTRAZIONE PAROLE da: '{testo}'")

    # NOVITÀ: Estrai termini composti PRIMA di normalizzare
    from .synonym_matcher import extract_compound_terms
    termini_composti = extract_compound_terms(testo)
    print(f"🔧 Termini composti trovati: {termini_composti}")

    testo_normalizzato = normalizza_testo(testo)
    print(f"🔧 Testo normalizzato: '{testo_normalizzato}'")

    # Stop words ridotte (solo le più comuni)
    stop_words = {'di', 'da', 'per', 'con', 'in', 'su', 'a', 'il', 'la', 'lo', 'e', 'o', 'del', 'della'}

    parole_base = set(testo_normalizzato.split())
    print(f"🔧 Parole base: {parole_base}")

    parole_senza_stop = parole_base - stop_words
    print(f"🔧 Senza stop words: {parole_senza_stop}")

    # Rimuovi parole troppo corte
    parole_singole = {p for p in parole_senza_stop if len(p) > 2}
    print(f"🔧 Parole singole (>2 caratteri): {parole_singole}")

    # UNISCI parole singole + termini composti
    parole_finali = parole_singole | termini_composti
    print(f"🔧 Parole finali (singole + composti): {parole_finali}")

    return parole_finali

def oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato):
    """Matching avanzato che restituisce anche il tipo di match"""

    print(f"\n🔍 DEBUG: === CONTROLLO COMPATIBILITÀ ===")
    print(f"🔍 Offerto - Titolo: '{annuncio_offerto.titolo}', Descrizione: '{annuncio_offerto.descrizione or 'VUOTA'}'")
    print(f"🔍 Cercato - Titolo: '{annuncio_cercato.titolo}', Descrizione: '{annuncio_cercato.descrizione or 'VUOTA'}'")
    print(f"🔍 Categorie - Offerto: '{annuncio_offerto.categoria}', Cercato: '{annuncio_cercato.categoria}'")

    # 1. MATCH SPECIFICO OTTIMIZZATO: Usa solo i titoli per velocità
    testo_offerto = annuncio_offerto.titolo
    testo_cercato = annuncio_cercato.titolo

    print(f"🔍 Testo offerto (solo titolo): '{testo_offerto}'")
    print(f"🔍 Testo cercato (solo titolo): '{testo_cercato}'")

    parole_offerto = estrai_parole_chiave(testo_offerto)
    parole_cercato = estrai_parole_chiave(testo_cercato)

    print(f"🔍 Parole chiave offerto: {parole_offerto}")
    print(f"🔍 Parole chiave cercato: {parole_cercato}")

    # NUOVA LOGICA: L'offerta deve contenere TUTTE le parole richieste
    # Questo permette ricerche specifiche ("iPhone 12 Pro") o generiche ("telefono")
    parole_mancanti = parole_cercato - parole_offerto
    print(f"🔍 Parole richieste: {parole_cercato}")
    print(f"🔍 Parole nell'offerta: {parole_offerto}")
    print(f"🔍 Parole mancanti nell'offerta: {parole_mancanti}")

    if not parole_mancanti:  # Tutte le parole richieste sono presenti nell'offerta
        print(f"✅ MATCH SPECIFICO: '{annuncio_offerto.titolo}' contiene tutte le parole richieste: {parole_cercato}")
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

    # 2.5 MATCH CON SINONIMI: Priorità ALTA - Prima della categoria
    # I sinonimi sono match semantici forti, devono avere priorità sulla categoria
    print(f"🔍 Controllo match con sinonimi...")
    try:
        from .synonym_matcher import check_synonym_match
        compatibile_sinonimo, tipo = check_synonym_match(parole_offerto, parole_cercato)
        if compatibile_sinonimo:
            print(f"✅ MATCH SINONIMO: '{annuncio_offerto.titolo}' → '{annuncio_cercato.titolo}' (via WordNet)")
            return True, "sinonimo"  # Marcato come 'sinonimo' per consentire filtraggio
    except Exception as e:
        print(f"⚠️ Errore check sinonimi: {e}")
        pass  # Se fallisce, continua con gli altri controlli

    # 3. MATCH PER CATEGORIA: Stessa categoria (priorità più bassa dei sinonimi)
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

def verifica_compatibilita_prezzo(annuncio_offerto, annuncio_cercato, tolleranza_percentuale=30):
    """Verifica se i prezzi sono compatibili per uno scambio equo"""
    prezzo_offerto = annuncio_offerto.prezzo_stimato
    prezzo_cercato = annuncio_cercato.prezzo_stimato

    # Se almeno uno non ha prezzo, consideriamo compatibile
    if not prezzo_offerto or not prezzo_cercato:
        return True, "prezzo_non_specificato"

    # Calcola differenza percentuale
    prezzo_medio = (prezzo_offerto + prezzo_cercato) / 2
    differenza_percentuale = abs(prezzo_offerto - prezzo_cercato) / prezzo_medio * 100

    if differenza_percentuale <= tolleranza_percentuale:
        return True, f"prezzi_compatibili_{differenza_percentuale:.1f}%"

    return False, f"prezzi_incompatibili_{differenza_percentuale:.1f}%"

def verifica_compatibilita_metodo_scambio(annuncio_a, annuncio_b):
    """Verifica se i metodi di scambio sono compatibili tra due annunci"""
    metodo_a = annuncio_a.metodo_scambio
    metodo_b = annuncio_b.metodo_scambio

    # Se almeno uno accetta entrambi i metodi, è sempre compatibile
    if metodo_a == 'entrambi' or metodo_b == 'entrambi':
        return True, "flessibile"

    # Se entrambi vogliono lo stesso metodo specifico
    if metodo_a == metodo_b:
        return True, metodo_a

    # Altrimenti incompatibile
    return False, f"incompatibile_{metodo_a}_vs_{metodo_b}"

def verifica_compatibilita_distanza(annuncio_a, annuncio_b, distanza_km):
    """Verifica se la distanza è accettabile per entrambi gli utenti"""
    # Se almeno uno preferisce solo spedizione, distanza non conta
    if annuncio_a.metodo_scambio == 'spedizione' or annuncio_b.metodo_scambio == 'spedizione':
        return True, "spedizione_disponibile"

    # Controllo distanza massima per entrambi
    limiti = []

    if annuncio_a.distanza_massima_km:
        limiti.append(annuncio_a.distanza_massima_km)

    if annuncio_b.distanza_massima_km:
        limiti.append(annuncio_b.distanza_massima_km)

    # Se nessuno ha specificato limiti, accetta qualsiasi distanza
    if not limiti:
        return True, "distanza_illimitata"

    # Verifica se la distanza reale è accettabile per entrambi
    distanza_massima_accettabile = min(limiti)

    if distanza_km <= distanza_massima_accettabile:
        return True, f"distanza_ok_{distanza_km:.0f}km_limite_{distanza_massima_accettabile}km"

    return False, f"distanza_eccessiva_{distanza_km:.0f}km_limite_{distanza_massima_accettabile}km"

def calcola_punteggio_qualita_avanzato(annuncio_offerto, annuncio_cercato, distanza_km):
    """Calcola punteggio di qualità considerando tutti i nuovi criteri"""
    punteggio = 0
    dettagli = []

    # 1. Compatibilità contenuto (peso: 40%)
    compatible, tipo_match = oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato)
    if compatible:
        if "specifico" in tipo_match:
            punteggio += 40
            dettagli.append("match_specifico")
        elif "generico" in tipo_match:
            punteggio += 25
            dettagli.append("match_generico")

    # 2. Compatibilità prezzo (peso: 25%)
    prezzo_ok, prezzo_dettagli = verifica_compatibilita_prezzo(annuncio_offerto, annuncio_cercato)
    if prezzo_ok:
        if "non_specificato" in prezzo_dettagli:
            punteggio += 15  # Bonus minore se prezzo non specificato
        else:
            # Più i prezzi sono simili, più punteggio
            if "compatibili" in prezzo_dettagli:
                percentuale_str = prezzo_dettagli.split('_')[-1].replace('%', '')
                try:
                    differenza = float(percentuale_str)
                    punteggio += max(5, 25 - differenza)  # Da 25 (identici) a 5 (30% differenza)
                except:
                    punteggio += 15
        dettagli.append(prezzo_dettagli)

    # 3. Compatibilità metodo scambio (peso: 15%)
    metodo_ok, metodo_dettagli = verifica_compatibilita_metodo_scambio(annuncio_offerto, annuncio_cercato)
    if metodo_ok:
        if metodo_dettagli == "flessibile":
            punteggio += 15
        else:
            punteggio += 12  # Bonus minore per metodo specifico uguale
        dettagli.append(metodo_dettagli)

    # 4. Compatibilità distanza (peso: 20%)
    distanza_ok, distanza_dettagli = verifica_compatibilita_distanza(
        annuncio_offerto, annuncio_cercato, distanza_km
    )
    if distanza_ok:
        if "stessa_citta" in str(distanza_km):
            punteggio += 20
        elif distanza_km <= 10:
            punteggio += 18
        elif distanza_km <= 30:
            punteggio += 15
        elif distanza_km <= 100:
            punteggio += 10
        else:
            punteggio += 5
        dettagli.append(distanza_dettagli)

    return punteggio, dettagli

def oggetti_compatibili(annuncio_offerto, annuncio_cercato):
    """Wrapper per compatibilità"""
    compatible, _ = oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato)
    return compatible

def oggetti_compatibili_avanzato(annuncio_offerto, annuncio_cercato, distanza_km):
    """Compatibilità avanzata che considera tutti i nuovi criteri"""
    # 1. Prima verifica compatibilità di base (contenuto)
    compatible_base, tipo_match = oggetti_compatibili_con_tipo(annuncio_offerto, annuncio_cercato)
    if not compatible_base:
        return False, 0, ["contenuto_incompatibile"]

    # 2. Prezzo: SEMPRE compatibile (rimosso il controllo)
    # Gli utenti possono accordarsi sul valore dello scambio

    # 3. Verifica metodo scambio
    metodo_ok, _ = verifica_compatibilita_metodo_scambio(annuncio_offerto, annuncio_cercato)
    if not metodo_ok:
        return False, 0, ["metodo_scambio_incompatibile"]

    # 4. Verifica distanza
    distanza_ok, _ = verifica_compatibilita_distanza(annuncio_offerto, annuncio_cercato, distanza_km)
    if not distanza_ok:
        return False, 0, ["distanza_incompatibile"]

    # 5. Calcola punteggio di qualità
    punteggio, dettagli = calcola_punteggio_qualita_avanzato(annuncio_offerto, annuncio_cercato, distanza_km)

    return True, punteggio, dettagli

def calcola_distanza_geografica(utente_a, utente_b):
    """Calcola distanza geografica tra due utenti usando il database città"""
    try:
        profile_a = UserProfile.objects.get(user=utente_a)
        profile_b = UserProfile.objects.get(user=utente_b)

        # Usa il nuovo metodo del profilo
        distanza_km = profile_a.get_distanza_km(profile_b)

        if distanza_km == 0:
            return 0, "stessa_citta"
        elif distanza_km == 999:
            return 999, "posizione_sconosciuta"
        elif distanza_km <= 50:
            return distanza_km, "province_vicine"
        else:
            return distanza_km, "province_lontane"

    except UserProfile.DoesNotExist:
        return 999, "profilo_mancante"

def calcola_distanza_haversine(lat1, lon1, lat2, lon2):
    """Calcola distanza in km tra due punti usando la formula di Haversine"""
    R = 6371  # Raggio della Terra in km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (math.sin(dlat/2)**2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
    c = 2 * math.asin(math.sqrt(a))

    return R * c

def classifica_distanza(distanza_km):
    """Classifica la distanza geografica"""
    if distanza_km == 0:
        return "locale", 10  # Bonus massimo per stessa città
    elif distanza_km <= 10:
        return "vicinissimo", 9
    elif distanza_km <= 30:
        return "vicino", 7
    elif distanza_km <= 100:
        return "medio", 5
    elif distanza_km <= 300:
        return "lontano", 3
    else:
        return "molto_lontano", 1


# === SISTEMA CALCOLO CICLI SEPARATO ===

import hashlib
import json
from datetime import datetime


class CycleFinder:
    """
    Classe per trovare cicli di scambio usando algoritmo DFS
    Ottimizzata per il sistema di calcolo separato
    SUPPORTA CALCOLO INCREMENTALE: ricalcola solo cicli impattati da modifiche
    """

    def __init__(self):
        self.grafo = {}  # dict: user_id -> [list di user_id con cui può scambiare]
        self.cicli_trovati = []
        self.cicli_hash_set = set()  # Per evitare duplicati

    def get_annunci_modificati(self, timestamp_ultimo_calcolo):
        """
        Trova gli annunci modificati dall'ultimo calcolo

        Args:
            timestamp_ultimo_calcolo: DateTime dell'ultimo calcolo completo

        Returns:
            QuerySet di Annuncio modificati
        """
        from .models import Annuncio

        annunci_modificati = Annuncio.objects.filter(
            last_modified__gt=timestamp_ultimo_calcolo,
            attivo=True
        )

        print(f"[{datetime.now()}] 📋 Trovati {annunci_modificati.count()} annunci modificati dal {timestamp_ultimo_calcolo}")
        return annunci_modificati

    def get_utenti_impattati(self, annunci_modificati):
        """
        Trova tutti gli utenti che potrebbero essere impattati dalle modifiche
        Include:
        - Utenti proprietari degli annunci modificati
        - Utenti che hanno annunci compatibili con quelli modificati

        Args:
            annunci_modificati: QuerySet di annunci modificati

        Returns:
            set di user_id impattati
        """
        utenti_impattati = set()

        # 1. Utenti proprietari degli annunci modificati
        for annuncio in annunci_modificati:
            utenti_impattati.add(annuncio.utente.id)

        # 2. Utenti che potrebbero scambiare con questi annunci
        # (annunci compatibili)
        for annuncio_mod in annunci_modificati:
            utenti_tutti = User.objects.filter(annuncio__attivo=True).distinct()

            for utente in utenti_tutti:
                if utente.id == annuncio_mod.utente.id:
                    continue

                # Controlla se c'è match tra questo utente e l'annuncio modificato
                if self._utente_compatibile_con_annuncio(utente, annuncio_mod):
                    utenti_impattati.add(utente.id)

        print(f"[{datetime.now()}] 👥 Identificati {len(utenti_impattati)} utenti impattati dalle modifiche")
        return utenti_impattati

    def _utente_compatibile_con_annuncio(self, utente, annuncio):
        """
        Verifica se un utente ha annunci compatibili con l'annuncio dato
        """
        if annuncio.tipo == 'offro':
            # L'annuncio offre qualcosa, cerchiamo chi lo cerca
            richieste_utente = Annuncio.objects.filter(utente=utente, tipo='cerco', attivo=True)
            for richiesta in richieste_utente:
                compatible, tipo_match = oggetti_compatibili_con_tipo(annuncio, richiesta)
                if compatible and tipo_match in ['specifico', 'parziale']:
                    return True
        else:
            # L'annuncio cerca qualcosa, cerchiamo chi lo offre
            offerte_utente = Annuncio.objects.filter(utente=utente, tipo='offro', attivo=True)
            for offerta in offerte_utente:
                compatible, tipo_match = oggetti_compatibili_con_tipo(offerta, annuncio)
                if compatible and tipo_match in ['specifico', 'parziale']:
                    return True

        return False

    def invalida_cicli_con_utenti(self, utenti_ids):
        """
        Marca come non validi tutti i cicli che coinvolgono gli utenti specificati

        Args:
            utenti_ids: set/list di user_id impattati

        Returns:
            int: Numero di cicli invalidati
        """
        from .models import CicloScambio
        from django.conf import settings

        count_invalidati = 0

        # Controlla quale database stiamo usando
        is_postgres = 'postgresql' in settings.DATABASES['default']['ENGINE']

        for user_id in utenti_ids:
            if is_postgres:
                # PostgreSQL: usa __contains nativo per JSON
                cicli = CicloScambio.objects.filter(valido=True, users__contains=user_id)
            else:
                # SQLite: usa __icontains come fallback (meno efficiente ma funziona)
                cicli = CicloScambio.objects.filter(valido=True, users__icontains=f'"{user_id}"')

            count = cicli.count()

            if count > 0:
                cicli.update(valido=False)
                count_invalidati += count

        print(f"[{datetime.now()}] ❌ Invalidati {count_invalidati} cicli impattati")
        return count_invalidati

    def trova_cicli_per_utenti(self, utenti_ids, max_length=6):
        """
        Trova cicli che coinvolgono specifici utenti (per calcolo incrementale)

        Args:
            utenti_ids: set/list di user_id per cui ricalcolare i cicli
            max_length: Lunghezza massima dei cicli

        Returns:
            list: Cicli trovati
        """
        print(f"[{datetime.now()}] 🔍 Calcolo incrementale per {len(utenti_ids)} utenti...")

        self.cicli_trovati.clear()
        self.cicli_hash_set.clear()

        if not self.grafo:
            print(f"[{datetime.now()}] ⚠️ Grafo vuoto, costruisco il grafo completo")
            self.costruisci_grafo()

        # Trova cicli che iniziano da ciascuno degli utenti impattati
        for user_id in utenti_ids:
            if user_id in self.grafo:
                self._trova_cicli_da_nodo(user_id, [user_id], max_length)

        print(f"[{datetime.now()}] ✅ Calcolo incrementale: trovati {len(self.cicli_trovati)} nuovi cicli")
        return self.cicli_trovati

    def costruisci_grafo(self):
        """
        Costruisce il grafo delle compatibilità dagli annunci attivi
        """
        print(f"[{datetime.now()}] 🔨 Costruzione grafo compatibilità...")

        self.grafo.clear()
        utenti = User.objects.filter(annuncio__attivo=True).distinct()

        for utente_a in utenti:
            if utente_a.id not in self.grafo:
                self.grafo[utente_a.id] = []

            for utente_b in utenti:
                if utente_a.id != utente_b.id:
                    # Verifica se A può scambiare con B
                    if self._c_e_match_tra_utenti(utente_a, utente_b):
                        self.grafo[utente_a.id].append(utente_b.id)

        # Rimuovi nodi senza collegamenti
        self.grafo = {k: v for k, v in self.grafo.items() if v}

        print(f"[{datetime.now()}] ✅ Grafo costruito: {len(self.grafo)} utenti, "
              f"{sum(len(v) for v in self.grafo.values())} collegamenti")

    def _c_e_match_tra_utenti(self, utente_a, utente_b):
        """
        Verifica se due utenti possono scambiare direttamente.
        Include controlli per metodo di scambio e distanza geografica.
        """
        offerte_a = Annuncio.objects.filter(utente=utente_a, tipo='offro', attivo=True)
        richieste_b = Annuncio.objects.filter(utente=utente_b, tipo='cerco', attivo=True)

        # Calcola distanza geografica tra i due utenti
        distanza_km, _ = calcola_distanza_geografica(utente_a, utente_b)

        for offerta in offerte_a:
            for richiesta in richieste_b:
                # Usa solo compatibilità titoli
                compatible, tipo_match = oggetti_compatibili_con_tipo(offerta, richiesta)
                # Accetta match specifico, parziale o sinonimo (non categoria o generico)
                if compatible and tipo_match in ['specifico', 'parziale', 'sinonimo']:
                    # Verifica metodo scambio
                    metodo_ok, _ = verifica_compatibilita_metodo_scambio(offerta, richiesta)
                    if not metodo_ok:
                        continue

                    # Verifica distanza
                    distanza_ok, _ = verifica_compatibilita_distanza(offerta, richiesta, distanza_km)
                    if not distanza_ok:
                        continue

                    return True
        return False

    def trova_tutti_cicli(self, max_length=6):
        """
        Trova tutti i cicli possibili fino a max_length utenti
        """
        print(f"[{datetime.now()}] 🔍 Ricerca cicli (max lunghezza: {max_length})...")

        self.cicli_trovati.clear()
        self.cicli_hash_set.clear()

        if not self.grafo:
            print(f"[{datetime.now()}] ⚠️ Grafo vuoto, nessun ciclo possibile")
            return []

        # Per ogni nodo, cerca cicli che iniziano da quel nodo
        for start_node in self.grafo.keys():
            self._trova_cicli_da_nodo(start_node, [start_node], max_length)

        print(f"[{datetime.now()}] ✅ Trovati {len(self.cicli_trovati)} cicli unici")
        return self.cicli_trovati

    def trova_scambi_diretti(self):
        """
        Trova tutti gli scambi diretti (lunghezza 2) usando il grafo
        """
        print(f"[{datetime.now()}] 🔍 Ricerca scambi diretti...")

        scambi_diretti = []
        scambi_hash_set = set()

        if not self.grafo:
            print(f"[{datetime.now()}] ⚠️ Grafo vuoto, nessuno scambio diretto possibile")
            return []

        # Per ogni coppia di utenti nel grafo
        for user_a in self.grafo.keys():
            for user_b in self.grafo.get(user_a, []):
                # Verifica se è uno scambio bidirezionale (A->B e B->A)
                if user_a in self.grafo.get(user_b, []):
                    # Crea il ciclo di lunghezza 2
                    ciclo = [user_a, user_b]
                    ciclo_normalizzato = self._normalizza_ciclo(ciclo)
                    ciclo_hash = self._hash_ciclo(ciclo_normalizzato)

                    if ciclo_hash not in scambi_hash_set:
                        scambi_hash_set.add(ciclo_hash)

                        dettagli = self._get_dettagli_ciclo(ciclo_normalizzato)
                        scambio_completo = {
                            'users': ciclo_normalizzato,
                            'lunghezza': 2,
                            'dettagli': dettagli,
                            'hash_ciclo': ciclo_hash
                        }
                        scambi_diretti.append(scambio_completo)

        print(f"[{datetime.now()}] ✅ Trovati {len(scambi_diretti)} scambi diretti unici")
        return scambi_diretti

    def _trova_cicli_da_nodo(self, current_node, path, max_length):
        """
        DFS ricorsivo per trovare cicli da un nodo specifico
        """
        if len(path) > max_length:
            return

        # Se siamo tornati al nodo di partenza e abbiamo almeno 2 utenti (include scambi diretti)
        if len(path) >= 2 and current_node in self.grafo:
            if path[0] in self.grafo[current_node]:
                # Ciclo trovato! Normalizza e aggiungi se unico
                ciclo_normalizzato = self._normalizza_ciclo(path)
                ciclo_hash = self._hash_ciclo(ciclo_normalizzato)

                if ciclo_hash not in self.cicli_hash_set:
                    self.cicli_hash_set.add(ciclo_hash)

                    dettagli = self._get_dettagli_ciclo(ciclo_normalizzato)
                    ciclo_completo = {
                        'users': ciclo_normalizzato,
                        'lunghezza': len(ciclo_normalizzato),
                        'dettagli': dettagli,
                        'hash_ciclo': ciclo_hash
                    }
                    self.cicli_trovati.append(ciclo_completo)
                # NON fare return qui - continua a cercare cicli più lunghi

        # Continua la ricerca
        if current_node in self.grafo:
            for next_node in self.grafo[current_node]:
                if next_node not in path:  # Evita cicli interni
                    self._trova_cicli_da_nodo(next_node, path + [next_node], max_length)

    def _normalizza_ciclo(self, ciclo):
        """
        Normalizza un ciclo per evitare duplicati
        [1,3,7] = [3,7,1] = [7,1,3] tutti diventano [1,3,7]
        """
        if not ciclo:
            return []

        # Trova l'indice dell'elemento minimo
        min_idx = ciclo.index(min(ciclo))

        # Ruota il ciclo per iniziare dall'elemento minimo
        return ciclo[min_idx:] + ciclo[:min_idx]

    def _hash_ciclo(self, ciclo):
        """
        Calcola hash MD5 di un ciclo per identificazione unica
        """
        ciclo_str = ','.join(map(str, sorted(ciclo)))
        return hashlib.md5(ciclo_str.encode()).hexdigest()

    def _get_dettagli_ciclo(self, user_ids):
        """
        Ottiene i dettagli completi del ciclo (oggetti scambiati, etc.)
        """
        dettagli = {
            'scambi': [],
            'oggetti': [],
            'timestamp': datetime.now().isoformat()
        }

        for i in range(len(user_ids)):
            user_da = user_ids[i]
            user_a = user_ids[(i + 1) % len(user_ids)]

            # Trova cosa scambia user_da con user_a
            scambio = self._trova_oggetto_scambiato(user_da, user_a)
            if scambio:
                dettagli['scambi'].append(scambio)
                dettagli['oggetti'].extend(scambio['oggetti'])

        return dettagli

    def _trova_oggetto_scambiato(self, user_id_da, user_id_a):
        """
        Trova quale oggetto user_da dà a user_a
        """
        try:
            utente_da = User.objects.get(id=user_id_da)
            utente_a = User.objects.get(id=user_id_a)

            offerte_da = Annuncio.objects.filter(utente=utente_da, tipo='offro', attivo=True)
            richieste_a = Annuncio.objects.filter(utente=utente_a, tipo='cerco', attivo=True)

            # Calcola distanza per usare logica avanzata
            try:
                profile_da = utente_da.userprofile
                profile_a = utente_a.userprofile

                if profile_da.latitudine and profile_da.longitudine and profile_a.latitudine and profile_a.longitudine:
                    from math import radians, sin, cos, sqrt, atan2

                    lat1, lon1 = radians(profile_da.latitudine), radians(profile_da.longitudine)
                    lat2, lon2 = radians(profile_a.latitudine), radians(profile_a.longitudine)

                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    distanza_km = 6371 * c
                else:
                    distanza_km = 50
            except:
                distanza_km = 50

            for offerta in offerte_da:
                for richiesta in richieste_a:
                    # Usa logica avanzata con soglia di qualità
                    compatible, punteggio, _ = oggetti_compatibili_avanzato(offerta, richiesta, distanza_km)
                    if compatible and punteggio >= 20:  # Soglia minima di qualità (ridotta)
                        return {
                            'da_user': user_id_da,
                            'a_user': user_id_a,
                            'oggetti': [
                                {
                                    'offerto': {
                                        'id': offerta.id,
                                        'titolo': offerta.titolo,
                                        'categoria': offerta.categoria.nome
                                    },
                                    'richiesto': {
                                        'id': richiesta.id,
                                        'titolo': richiesta.titolo,
                                        'categoria': richiesta.categoria.nome
                                    }
                                }
                            ]
                        }
        except User.DoesNotExist:
            pass

        return None


# === FUNZIONI HELPER PER IL CALCOLO CICLI ===

def costruisci_grafo():
    """
    Funzione helper per costruire il grafo (usata dal management command)
    """
    finder = CycleFinder()
    finder.costruisci_grafo()
    return finder.grafo


def get_dettagli_ciclo(user_ids):
    """
    Funzione helper per ottenere dettagli di un ciclo (usata dal management command)
    """
    finder = CycleFinder()
    return finder._get_dettagli_ciclo(user_ids)


# ===== FUNZIONI OTTIMIZZATE CHE USANO CICLI PRE-CALCOLATI =====

def get_cicli_precalcolati():
    """
    Funzione ottimizzata che legge i cicli pre-calcolati dal database invece di fare brute-force.
    Sostituisce le vecchie funzioni trova_scambi_diretti() e trova_catene_scambio().

    Returns:
        dict: {
            'scambi_diretti': [],     # Cicli di lunghezza 2
            'catene': [],            # Cicli di lunghezza 3+
            'totale': int,
            'tempo': float
        }
    """
    import time
    from .models import CicloScambio

    start_time = time.time()

    print("📊 Caricando cicli pre-calcolati dal database...")

    # Carica tutti i cicli validi
    cicli_db = CicloScambio.objects.filter(valido=True).order_by('-calcolato_at')

    scambi_diretti = []
    catene_lunghe = []

    for ciclo_db in cicli_db:
        try:
            # Converti il ciclo dal database al formato compatibile con le views
            ciclo_convertito = converti_ciclo_db_a_view_format(ciclo_db)

            if ciclo_convertito:
                if ciclo_db.lunghezza == 2:
                    scambi_diretti.append(ciclo_convertito)
                else:
                    catene_lunghe.append(ciclo_convertito)

        except Exception as e:
            print(f"⚠️ Errore conversione ciclo {ciclo_db.id}: {e}")
            continue

    elapsed = time.time() - start_time
    totale = len(scambi_diretti) + len(catene_lunghe)

    print(f"✅ Caricati {totale} cicli pre-calcolati in {elapsed:.3f}s ({len(scambi_diretti)} diretti, {len(catene_lunghe)} catene)")

    return {
        'scambi_diretti': scambi_diretti,
        'catene': catene_lunghe,
        'totale': totale,
        'tempo': elapsed
    }


def converti_ciclo_db_a_view_format(ciclo_db):
    """
    Converte un CicloScambio dal database al formato richiesto dalle views.

    Args:
        ciclo_db: Istanza CicloScambio dal database

    Returns:
        dict: Ciclo nel formato compatibile con le views esistenti
    """
    from django.contrib.auth.models import User
    from .models import Annuncio

    try:
        # Carica gli utenti del ciclo
        user_ids = ciclo_db.users
        utenti = User.objects.filter(id__in=user_ids)

        if len(utenti) != len(user_ids):
            print(f"⚠️ Alcuni utenti del ciclo {ciclo_db.id} non esistono più")
            return None

        # Crea un dizionario per accesso veloce agli utenti per ID
        utenti_dict = {u.id: u for u in utenti}

        # Usa i dettagli già processati dal database
        dettagli = ciclo_db.dettagli

        # Calcola categoria qualità basata sui dettagli
        categoria_qualita = calcola_categoria_qualita_da_dettagli(dettagli)

        # Verifica se il ciclo usa sinonimi controllando i tipi di match
        usa_sinonimi = False
        if 'scambi' in dettagli:
            for scambio in dettagli['scambi']:
                oggetti = scambio.get('oggetti', [])
                for oggetto in oggetti:
                    # Verifica se c'è un match tramite sinonimi ricalcolando
                    try:
                        offerto_id = oggetto.get('offerto', {}).get('id')
                        richiesto_id = oggetto.get('richiesto', {}).get('id')

                        if offerto_id and richiesto_id:
                            offerta_ann = Annuncio.objects.get(id=offerto_id)
                            richiesta_ann = Annuncio.objects.get(id=richiesto_id)
                            _, tipo_match = oggetti_compatibili_con_tipo(offerta_ann, richiesta_ann)
                            if tipo_match == 'sinonimo':
                                usa_sinonimi = True
                                break
                    except:
                        pass
                if usa_sinonimi:
                    break

        # Costruisci il mapping utente -> offerte/richieste dai dettagli scambi
        user_offers = {}
        user_requests = {}

        if 'scambi' in dettagli:
            for scambio in dettagli['scambi']:
                da_user = scambio.get('da_user')
                a_user = scambio.get('a_user')
                oggetti = scambio.get('oggetti', [])

                for oggetto in oggetti:
                    # L'utente da_user offre 'offerto' e l'utente a_user cerca 'richiesto'
                    if 'offerto' in oggetto and da_user:
                        try:
                            offerta = Annuncio.objects.get(id=oggetto['offerto']['id'])
                            user_offers[da_user] = offerta
                        except Annuncio.DoesNotExist:
                            pass

                    if 'richiesto' in oggetto and a_user:
                        try:
                            richiesta = Annuncio.objects.get(id=oggetto['richiesto']['id'])
                            user_requests[a_user] = richiesta
                        except Annuncio.DoesNotExist:
                            pass

        # NUOVO: Riordina gli utenti secondo la sequenza di scambio
        # La sequenza corretta è: A offre a B, B offre a C, C offre a A
        # Quindi dobbiamo seguire i link da_user -> a_user
        utenti_ordinati = []
        if 'scambi' in dettagli and dettagli['scambi']:
            # Crea una mappa da_user -> a_user per seguire la catena
            scambi_map = {}
            for scambio in dettagli['scambi']:
                da_user = scambio.get('da_user')
                a_user = scambio.get('a_user')
                if da_user and a_user:
                    scambi_map[da_user] = a_user

            # Parti dal primo utente e segui la catena
            if scambi_map:
                utente_corrente = list(scambi_map.keys())[0]
                visitati = set()

                while utente_corrente not in visitati and utente_corrente in utenti_dict:
                    visitati.add(utente_corrente)
                    utenti_ordinati.append({
                        'user': utenti_dict[utente_corrente],
                        'offerta': user_offers.get(utente_corrente),
                        'richiede': user_requests.get(utente_corrente)
                    })

                    # Vai all'utente successivo
                    if utente_corrente in scambi_map:
                        utente_corrente = scambi_map[utente_corrente]
                    else:
                        break

        # Fallback: se non riusciamo a ordinare, usa l'ordine originale
        if not utenti_ordinati:
            utenti_ordinati = []
            for user_id in user_ids:
                if user_id in utenti_dict:
                    utenti_ordinati.append({
                        'user': utenti_dict[user_id],
                        'offerta': user_offers.get(user_id),
                        'richiede': user_requests.get(user_id)
                    })

        # Costruisci annunci_coinvolti nell'ordine della sequenza di scambio
        # Ordine: A offre X, B cerca X, B offre Y, C cerca Y, C offre Z, A cerca Z
        annunci_coinvolti = []
        num_utenti = len(utenti_ordinati)

        for i in range(num_utenti):
            utente_corrente = utenti_ordinati[i]
            utente_successivo = utenti_ordinati[(i + 1) % num_utenti]

            # 1. Utente corrente OFFRE qualcosa
            if utente_corrente['offerta']:
                annunci_coinvolti.append({
                    'annuncio': utente_corrente['offerta'],
                    'ruolo': 'offre',
                    'utente': utente_corrente['user'].username
                })

            # 2. Utente successivo CERCA quella cosa
            if utente_successivo['richiede']:
                annunci_coinvolti.append({
                    'annuncio': utente_successivo['richiede'],
                    'ruolo': 'richiede',
                    'utente': utente_successivo['user'].username
                })

        ciclo_output = {
            'utenti': utenti_ordinati,
            'dettagli': dettagli,
            'categoria_qualita': categoria_qualita,
            'punteggio_qualita': dettagli.get('punteggio_qualita', 0),
            'lunghezza': ciclo_db.lunghezza,
            'id_ciclo': str(ciclo_db.id),
            'calcolato_at': ciclo_db.calcolato_at,
            'annunci_coinvolti': annunci_coinvolti,
            'usa_sinonimi': usa_sinonimi,  # Flag per filtraggio UI
            'da_database': True  # Flag per identificare cicli pre-calcolati
        }

        return ciclo_output

    except Exception as e:
        print(f"⚠️ Errore conversione ciclo {ciclo_db.id}: {e}")
        return None


def calcola_categoria_qualita_da_dettagli(dettagli):
    """
    Determina la categoria di qualità di un ciclo basandosi sui suoi dettagli.

    Args:
        dettagli: Dizionario con i dettagli del ciclo

    Returns:
        str: 'alta' o 'generica'
    """
    # Logica semplificata per determinare la qualità
    # Puoi espandere questa logica secondo le tue esigenze

    if 'score_qualita' in dettagli:
        return 'alta' if dettagli['score_qualita'] > 0.7 else 'generica'

    # Fallback: analizza i match tra annunci
    if 'annunci' in dettagli:
        match_perfetti = 0
        totale_match = 0

        for annuncio_info in dettagli['annunci']:
            if 'compatibilita_score' in annuncio_info:
                totale_match += 1
                if annuncio_info['compatibilita_score'] > 0.8:
                    match_perfetti += 1

        if totale_match > 0:
            percentuale_perfetti = match_perfetti / totale_match
            return 'alta' if percentuale_perfetti > 0.6 else 'generica'

    # Default
    return 'generica'


def trova_scambi_diretti_ottimizzato():
    """
    Versione ottimizzata che sostituisce trova_scambi_diretti().
    Legge solo i cicli di lunghezza 2 dal database.
    """
    risultato = get_cicli_precalcolati()
    return risultato['scambi_diretti']


def calcola_qualita_ciclo(ciclo, return_tipo_match=False):
    """
    Calcola la qualità di un ciclo pre-calcolato dal database.

    Args:
        ciclo: Ciclo in formato dict dalla funzione converti_ciclo_db_a_view_format
        return_tipo_match: Se True, restituisce anche se ha match solo per categoria

    Returns:
        int o tuple: Punteggio qualità del ciclo, oppure (punteggio, ha_solo_categoria)
    """
    if not ciclo.get('utenti'):
        return (0, True) if return_tipo_match else 0

    punteggio_totale = 0
    num_scambi = 0
    ha_match_titoli = True  # Assume True inizialmente, diventa False se trova match generici

    utenti = ciclo['utenti']
    num_utenti = len(utenti)

    # Calcola la qualità per ogni scambio nel ciclo
    # L'utente i offre qualcosa all'utente (i+1) % num_utenti
    for i in range(num_utenti):
        utente_corrente = utenti[i]
        utente_successivo = utenti[(i + 1) % num_utenti]

        # L'offerta dell'utente corrente deve matchare con la richiesta dell'utente successivo
        if not utente_corrente.get('offerta') or not utente_successivo.get('richiede'):
            continue

        offerta = utente_corrente['offerta']
        richiesta = utente_successivo['richiede']

        # Usa la funzione avanzata per calcolare qualità
        try:
            compatible, punteggio, _ = oggetti_compatibili_avanzato(offerta, richiesta, distanza_km=50)
            if compatible:
                punteggio_totale += punteggio

            # Verifica il tipo di match
            _, tipo_match = oggetti_compatibili_con_tipo(offerta, richiesta)
            # Se anche solo UNO scambio è 'categoria' o 'generico', l'intera catena è generica
            if tipo_match in ['categoria', 'generico']:
                ha_match_titoli = False

            num_scambi += 1
        except:
            # Se fallisce, salta questo scambio
            continue

    # Media dei punteggi degli scambi nel ciclo
    punteggio = punteggio_totale // max(1, num_scambi) if num_scambi > 0 else 0

    if return_tipo_match:
        return punteggio, ha_match_titoli
    return punteggio


def trova_catene_scambio_ottimizzato(max_lunghezza=6, solo_alta_qualita=True, soglia_qualita=20):
    """
    Versione ottimizzata che sostituisce trova_catene_scambio().
    Legge i cicli pre-calcolati dal database e filtra per lunghezza e qualità.

    Args:
        max_lunghezza: Lunghezza massima delle catene da restituire
        solo_alta_qualita: Se True, mostra solo catene con parole in comune (≥soglia_qualita)
        soglia_qualita: Punteggio minimo per considerare una catena di alta qualità (default: 20)
    """
    risultato = get_cicli_precalcolati()
    catene = risultato['catene']

    # Filtra per lunghezza se specificata
    if max_lunghezza:
        catene = [
            catena for catena in catene
            if catena['lunghezza'] <= max_lunghezza
        ]

    # Filtra per qualità se richiesto
    if solo_alta_qualita:
        catene_alta_qualita = []
        for catena in catene:
            qualita = calcola_qualita_ciclo(catena)
            if qualita >= soglia_qualita:
                # Aggiorna il punteggio nel ciclo per uso successivo
                catena['punteggio_qualita'] = qualita
                catene_alta_qualita.append(catena)
        return catene_alta_qualita

    return catene


def filtra_catene_per_utente_ottimizzato(scambi_diretti, catene, utente):
    """
    Versione ottimizzata di filtra_catene_per_utente che lavora sui cicli pre-calcolati.
    """
    scambi_diretti_utente = []
    catene_lunghe_utente = []

    # Filtra scambi diretti per utente
    for scambio in scambi_diretti:
        if any(u['user'].id == utente.id for u in scambio['utenti']):
            scambi_diretti_utente.append(scambio)

    # Filtra catene lunghe per utente
    for catena in catene:
        if any(u['user'].id == utente.id for u in catena['utenti']):
            catene_lunghe_utente.append(catena)

    print(f"🎯 Filtrato per {utente.username}: {len(scambi_diretti_utente)} scambi diretti, {len(catene_lunghe_utente)} catene")

    return scambi_diretti_utente, catene_lunghe_utente


def trova_catene_per_annuncio_ottimizzato(annuncio, max_lunghezza=6, includi_generiche=True):
    """
    Versione ottimizzata che trova cicli pre-calcolati contenenti un annuncio specifico.
    Sostituisce trova_catene_per_annuncio() per evitare brute-force.

    Args:
        annuncio: Istanza Annuncio per cui cercare catene
        max_lunghezza: Lunghezza massima delle catene
        includi_generiche: Se True, include anche catene generiche (punteggio < 20)

    Returns:
        list: Cicli che coinvolgono l'annuncio specificato
    """
    import time
    start_time = time.time()

    print(f"🔍 Ricerca ottimizzata per annuncio: {annuncio.titolo} (ID: {annuncio.id})")

    # Carica tutti i cicli pre-calcolati
    risultato = get_cicli_precalcolati()
    tutti_cicli = risultato['scambi_diretti'] + risultato['catene']

    cicli_per_annuncio = []

    for ciclo in tutti_cicli:
        # Controlla se l'utente dell'annuncio è nel ciclo
        if any(u['user'].id == annuncio.utente.id for u in ciclo['utenti']):
            # Verifica se l'annuncio è tra quelli del ciclo analizzando i dettagli
            if controlla_annuncio_in_ciclo(annuncio, ciclo):
                if max_lunghezza is None or ciclo['lunghezza'] <= max_lunghezza:
                    # Filtra per qualità se richiesto
                    if not includi_generiche:
                        qualita = calcola_qualita_ciclo(ciclo)
                        if qualita < 20:
                            continue  # Salta catene generiche
                        ciclo['punteggio_qualita'] = qualita

                    cicli_per_annuncio.append(ciclo)

    elapsed = time.time() - start_time
    print(f"✅ Trovati {len(cicli_per_annuncio)} cicli per annuncio in {elapsed:.3f}s")

    return cicli_per_annuncio


def controlla_annuncio_in_ciclo(annuncio, ciclo):
    """
    Controlla se un annuncio specifico è coinvolto in un ciclo pre-calcolato.

    Args:
        annuncio: Istanza Annuncio da cercare
        ciclo: Ciclo convertito dal database

    Returns:
        bool: True se l'annuncio è coinvolto nel ciclo
    """
    try:
        # Controlla nei dettagli del ciclo se c'è riferimento all'annuncio
        dettagli = ciclo.get('dettagli', {})

        # Cerca nelle informazioni degli annunci nel ciclo
        if 'annunci' in dettagli:
            for annuncio_info in dettagli['annunci']:
                if annuncio_info.get('id') == annuncio.id:
                    return True

        # Fallback: se l'utente è nel ciclo e ha lo stesso tipo/categoria dell'annuncio
        if any(u['user'].id == annuncio.utente.id for u in ciclo['utenti']):
            # Controllo semplificato basato sulla presenza dell'utente
            # In futuro si può migliorare analizzando meglio i dettagli
            return True

        return False

    except Exception as e:
        print(f"⚠️ Errore controllo annuncio in ciclo: {e}")
        # In caso di errore, assume che l'annuncio sia coinvolto se l'utente è presente
        return any(u['user'].id == annuncio.utente.id for u in ciclo['utenti'])
