#!/usr/bin/env python
"""
Script per debuggare step-by-step la visualizzazione delle catene in /catene-scambio/
Simula esattamente cosa fa la view quando l'utente clicca "Cerca catene"
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import CicloScambio, Annuncio, UserProfile
from django.contrib.auth.models import User
from scambi.matching import (
    trova_scambi_diretti_ottimizzato,
    trova_catene_scambio_ottimizzato,
    calcola_qualita_ciclo,
    filtra_catene_per_utente_ottimizzato,
    get_cicli_precalcolati
)

print("=" * 80)
print("🔍 DEBUG STEP-BY-STEP: /catene-scambio/")
print("=" * 80)

# Scegli un utente da testare (cambio con uno che dovrebbe vedere catene)
username = input("\nInserisci username da testare (premi INVIO per 'admin'): ").strip() or "admin"

try:
    user = User.objects.get(username=username)
    print(f"\n✅ Testando per utente: {user.username}")
except User.DoesNotExist:
    print(f"❌ Utente '{username}' non trovato!")
    sys.exit(1)

# Controlla annunci dell'utente
annunci_utente = Annuncio.objects.filter(utente=user, attivo=True)
print(f"\n📊 Annunci attivi dell'utente: {annunci_utente.count()}")
for ann in annunci_utente:
    print(f"   - {ann.tipo}: '{ann.titolo}' (ID: {ann.id})")

if not annunci_utente.exists():
    print("❌ L'utente non ha annunci attivi! Non può vedere catene.")
    sys.exit(0)

print("\n" + "=" * 80)
print("STEP 1: Carica scambi diretti (come fa la view)")
print("=" * 80)

try:
    scambi_diretti = trova_scambi_diretti_ottimizzato()
    print(f"✅ Scambi diretti trovati: {len(scambi_diretti)}")

    # Conta quanti coinvolgono l'utente
    scambi_diretti_utente = [s for s in scambi_diretti if any(u['user'].id == user.id for u in s['utenti'])]
    print(f"   Di cui coinvolgono {user.username}: {len(scambi_diretti_utente)}")

    if len(scambi_diretti_utente) > 0:
        print(f"\n   Esempio scambio diretto per {user.username}:")
        s = scambi_diretti_utente[0]
        for u in s['utenti']:
            print(f"      - {u['nome']}: offre '{u.get('offerta', {}).titolo if u.get('offerta') else 'N/A'}' → "
                  f"cerca '{u.get('richiede', {}).titolo if u.get('richiede') else 'N/A'}'")
except Exception as e:
    print(f"❌ ERRORE in trova_scambi_diretti_ottimizzato: {e}")
    import traceback
    traceback.print_exc()
    scambi_diretti = []

print("\n" + "=" * 80)
print("STEP 2: Carica catene lunghe (come fa la view)")
print("=" * 80)

try:
    catene = trova_catene_scambio_ottimizzato()
    print(f"✅ Catene lunghe trovate (prima del filtro qualità): {len(catene)}")

    # Conta per lunghezza
    for lunghezza in range(3, 7):
        count = len([c for c in catene if len(c.get('utenti', [])) == lunghezza])
        print(f"   - Catene a {lunghezza} utenti: {count}")

except Exception as e:
    print(f"❌ ERRORE in trova_catene_scambio_ottimizzato: {e}")
    import traceback
    traceback.print_exc()
    catene = []

print("\n" + "=" * 80)
print("STEP 3: Applica filtro qualità (come fa la view alle linee 303-310)")
print("=" * 80)

catene_specifiche = []
catene_filtrate = []

for c in catene:
    try:
        punteggio, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
        c['punteggio_qualita'] = punteggio

        if ha_match_titoli:
            catene_specifiche.append(c)
        else:
            catene_filtrate.append(c)
    except Exception as e:
        print(f"   ⚠️  Errore calcolando qualità per catena: {e}")

print(f"✅ Catene che passano il filtro (ha_match_titoli=True): {len(catene_specifiche)}")
print(f"⚠️  Catene FILTRATE (ha_match_titoli=False): {len(catene_filtrate)}")

if len(catene_filtrate) > 0 and len(catene_specifiche) == 0:
    print("\n   ⚠️  PROBLEMA: Tutte le catene vengono filtrate!")
    print(f"   Mostrando le prime {min(3, len(catene_filtrate))} catene filtrate:\n")

    for i, c in enumerate(catene_filtrate[:3]):
        print(f"   Catena {i+1}:")
        print(f"      - Utenti: {[u['nome'] for u in c['utenti']]}")
        print(f"      - Punteggio: {c.get('punteggio_qualita', 0)}")
        for u in c['utenti']:
            if u.get('offerta') and u.get('richiede'):
                print(f"      - {u['nome']}: '{u['offerta'].titolo}' → '{u['richiede'].titolo}'")

print("\n" + "=" * 80)
print("STEP 4: Filtra per utente (come fa la view alla linea 313-314)")
print("=" * 80)

try:
    scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
        scambi_diretti, catene_specifiche, user
    )

    print(f"✅ Scambi diretti per {user.username}: {len(scambi_diretti_utente)}")
    print(f"✅ Catene lunghe per {user.username}: {len(catene_lunghe_utente)}")

    tutte_catene_utente = scambi_diretti_utente + catene_lunghe_utente
    print(f"\n📊 TOTALE catene visualizzabili per {user.username}: {len(tutte_catene_utente)}")

    if len(tutte_catene_utente) == 0:
        print("\n❌ PROBLEMA: Nessuna catena visualizzabile dopo il filtraggio!")
    else:
        print(f"\n✅ L'utente dovrebbe vedere {len(tutte_catene_utente)} catene")

except Exception as e:
    print(f"❌ ERRORE in filtra_catene_per_utente_ottimizzato: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("STEP 5: CONFRONTO con get_cicli_precalcolati() (usato in /le-mie-catene/)")
print("=" * 80)

try:
    cicli_precalcolati = get_cicli_precalcolati()
    print(f"✅ Cicli pre-calcolati dal DB: {len(cicli_precalcolati)}")

    # Filtra per utente
    cicli_utente = [c for c in cicli_precalcolati if any(u['user'].id == user.id for u in c['utenti'])]
    print(f"✅ Cicli che coinvolgono {user.username}: {len(cicli_utente)}")

    print(f"\n📊 CONFRONTO:")
    print(f"   - Algoritmo vecchio (trova_catene_scambio_ottimizzato): {len(tutte_catene_utente)} catene")
    print(f"   - Cicli pre-calcolati (get_cicli_precalcolati): {len(cicli_utente)} catene")

    if len(cicli_utente) > len(tutte_catene_utente):
        print(f"\n   ⚠️  PROBLEMA: I cicli pre-calcolati trovano PIÙ catene!")
        print(f"   Differenza: {len(cicli_utente) - len(tutte_catene_utente)} catene mancanti")

except Exception as e:
    print(f"❌ ERRORE in get_cicli_precalcolati: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("🏁 DIAGNOSI COMPLETATA")
print("=" * 80)

# Riepilogo problemi
print("\n📋 RIEPILOGO:")
if len(tutte_catene_utente) == 0:
    if len(catene_filtrate) > 0:
        print("❌ PROBLEMA: Tutte le catene vengono filtrate dal controllo qualità (ha_match_titoli)")
        print("   SOLUZIONE: Modificare il filtro in views.py per includere anche match categoria/generici")
    elif len(catene) == 0:
        print("❌ PROBLEMA: trova_catene_scambio_ottimizzato() non trova catene")
        print("   SOLUZIONE: Usare get_cicli_precalcolati() invece degli algoritmi vecchi")
    elif len(scambi_diretti_utente) == 0:
        print("❌ PROBLEMA: filtra_catene_per_utente_ottimizzato() non trova catene per l'utente")
        print("   SOLUZIONE: Verificare la logica di filtraggio utente")
else:
    print(f"✅ La view dovrebbe mostrare {len(tutte_catene_utente)} catene per {user.username}")
    print("   Se online non le vedi, il problema è nel template o nel rendering")
