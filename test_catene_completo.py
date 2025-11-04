#!/usr/bin/env python
"""
Test completo del flusso di ricerca catene per capire dove si blocca
"""

import os
import django

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
print("🔍 TEST COMPLETO FLUSSO RICERCA CATENE")
print("=" * 80)

username = input("\nInserisci username da testare (INVIO per 'admin'): ").strip() or "admin"

try:
    user = User.objects.get(username=username)
    profilo = UserProfile.objects.get(user=user)
    print(f"\n✅ Utente: {user.username} (ID: {user.id})")
    print(f"   Status: {'⭐ PREMIUM' if profilo.is_premium else '🆓 FREE'}")
except User.DoesNotExist:
    print(f"❌ Utente '{username}' non trovato!")
    exit(1)

# Verifica annunci
annunci_user = Annuncio.objects.filter(utente=user, attivo=True)
print(f"\n📊 Annunci attivi: {annunci_user.count()}")
for ann in annunci_user:
    print(f"   - {ann.tipo}: '{ann.titolo}' (ID: {ann.id})")

if not annunci_user.exists():
    print("\n❌ Nessun annuncio attivo! L'utente non può vedere catene.")
    exit(0)

print("\n" + "=" * 80)
print("TEST 1: trova_scambi_diretti_ottimizzato()")
print("=" * 80)

try:
    scambi_diretti = trova_scambi_diretti_ottimizzato()
    print(f"✅ Scambi diretti trovati: {len(scambi_diretti)}")

    # Filtra per utente
    scambi_diretti_user = [s for s in scambi_diretti if any(u['user'].id == user.id for u in s['utenti'])]
    print(f"   Per {user.username}: {len(scambi_diretti_user)}")

    if len(scambi_diretti_user) > 0:
        print(f"\n   Esempio scambio:")
        s = scambi_diretti_user[0]
        for u in s['utenti']:
            print(f"      {u['nome']}: offre '{u.get('offerta').titolo if u.get('offerta') else 'N/A'}' → cerca '{u.get('richiede').titolo if u.get('richiede') else 'N/A'}'")
except Exception as e:
    print(f"❌ ERRORE: {e}")
    import traceback
    traceback.print_exc()
    scambi_diretti = []

print("\n" + "=" * 80)
print("TEST 2: trova_catene_scambio_ottimizzato()")
print("=" * 80)

try:
    catene = trova_catene_scambio_ottimizzato()
    print(f"✅ Catene trovate (totali): {len(catene)}")

    for lunghezza in range(3, 7):
        count = len([c for c in catene if len(c.get('utenti', [])) == lunghezza])
        print(f"   - Catene a {lunghezza}: {count}")
except Exception as e:
    print(f"❌ ERRORE: {e}")
    import traceback
    traceback.print_exc()
    catene = []

print("\n" + "=" * 80)
print("TEST 3: Calcolo qualità e filtro")
print("=" * 80)

catene_con_match_titoli = 0
catene_solo_categoria = 0

for c in catene:
    try:
        punteggio, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
        if ha_match_titoli:
            catene_con_match_titoli += 1
        else:
            catene_solo_categoria += 1
    except:
        pass

print(f"✅ Catene con match titoli (specifico/parziale/sinonimo): {catene_con_match_titoli}")
print(f"⚠️  Catene con solo match categoria/generico: {catene_solo_categoria}")

if catene_solo_categoria > 0 and catene_con_match_titoli == 0:
    print(f"\n   ⚠️  PROBLEMA: Tutte le catene hanno solo match categoria!")
    print(f"   Il filtro qualità le sta bloccando tutte.")

print("\n" + "=" * 80)
print("TEST 4: Filtro per utente")
print("=" * 80)

try:
    # Crea lista catene_specifiche solo con quelle che hanno match titoli
    catene_specifiche = []
    for c in catene:
        punteggio, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
        if ha_match_titoli:
            catene_specifiche.append(c)

    print(f"Catene dopo filtro qualità: {len(catene_specifiche)}")

    scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
        scambi_diretti, catene_specifiche, user
    )

    print(f"✅ Scambi diretti per {user.username}: {len(scambi_diretti_utente)}")
    print(f"✅ Catene lunghe per {user.username}: {len(catene_lunghe_utente)}")

    totale = len(scambi_diretti_utente) + len(catene_lunghe_utente)
    print(f"\n📊 TOTALE visualizzabile: {totale}")

    if totale == 0:
        print(f"\n❌ PROBLEMA: Nessuna catena dopo il filtro utente!")
except Exception as e:
    print(f"❌ ERRORE: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST 5: get_cicli_precalcolati() (DB)")
print("=" * 80)

try:
    cicli_db = get_cicli_precalcolati()
    print(f"✅ Cicli dal DB: {len(cicli_db)}")

    cicli_user = [c for c in cicli_db if any(u['user'].id == user.id for u in c['utenti'])]
    print(f"   Per {user.username}: {len(cicli_user)}")

    # Controlla qualità
    cicli_alta_qualita = 0
    cicli_generici = 0

    for c in cicli_user:
        _, ha_match = calcola_qualita_ciclo(c, return_tipo_match=True)
        if ha_match:
            cicli_alta_qualita += 1
        else:
            cicli_generici += 1

    print(f"   - Con match titoli: {cicli_alta_qualita}")
    print(f"   - Solo categoria: {cicli_generici}")

except Exception as e:
    print(f"❌ ERRORE: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST 6: Verifica DB cicli vs Algoritmo")
print("=" * 80)

cicli_validi_db = CicloScambio.objects.filter(valido=True)
print(f"Cicli nel DB (valido=True): {cicli_validi_db.count()}")

cicli_user_db = [c for c in cicli_validi_db if user.id in c.users]
print(f"Cicli nel DB per {user.username}: {len(cicli_user_db)}")

print(f"\n📊 CONFRONTO:")
print(f"   - Algoritmo trova_catene_scambio_ottimizzato: {len(catene)} catene")
print(f"   - DB get_cicli_precalcolati: {len(cicli_db)} cicli")
print(f"   - Dopo filtro qualità: {catene_con_match_titoli} catene")
print(f"   - Dopo filtro utente: {totale if 'totale' in locals() else 0} catene")

if cicli_validi_db.count() > 0 and totale == 0:
    print(f"\n⚠️  DIVERGENZA: Il DB ha cicli ma l'algoritmo non ne trova!")

print("\n" + "=" * 80)
print("🏁 DIAGNOSI")
print("=" * 80)

# Determina il problema
if cicli_validi_db.count() == 0:
    print("❌ PROBLEMA: Nessun ciclo nel database!")
    print("   SOLUZIONE: Esegui il CycleCalculator per calcolare i cicli")
elif len(catene) == 0:
    print("❌ PROBLEMA: trova_catene_scambio_ottimizzato() non trova catene!")
    print("   SOLUZIONE: La view /catene-scambio/ usa algoritmi vecchi, non usa get_cicli_precalcolati()")
elif catene_con_match_titoli == 0:
    print("❌ PROBLEMA: Tutte le catene vengono filtrate (solo match categoria)!")
    print("   SOLUZIONE: Gli annunci non hanno match sui titoli, solo categoria")
    print(f"\n   Verifica annunci 'synth':")
    synth_annunci = Annuncio.objects.filter(titolo__icontains='synth', attivo=True)
    print(f"   - Annunci 'synth' attivi: {synth_annunci.count()}")
    for ann in synth_annunci:
        print(f"      {ann.utente.username} {ann.tipo}: '{ann.titolo}'")
elif totale == 0:
    print("❌ PROBLEMA: Il filtro utente blocca tutte le catene!")
    print("   SOLUZIONE: Bug nella logica di filtraggio per utente")
else:
    print(f"✅ Tutto sembra OK! Dovresti vedere {totale} catene")

print("\n" + "=" * 80)
