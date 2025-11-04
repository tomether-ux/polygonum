#!/usr/bin/env python
"""
Debug post-fix: Verifica perché riattivando 'basso' non trova più catene
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import CicloScambio, Annuncio, CalcoloMetadata
from django.contrib.auth.models import User
from scambi.matching import (
    CycleFinder,
    get_cicli_precalcolati,
    calcola_qualita_ciclo
)

print("=" * 80)
print("🔍 DEBUG POST-FIX: Perché non trova catene con 'basso' riattivato?")
print("=" * 80)

# 1. Verifica stato 'basso'
print("\n" + "=" * 80)
print("STEP 1: Stato annuncio 'basso'")
print("=" * 80)

try:
    basso = Annuncio.objects.get(titolo__iexact='basso')
    print(f"✅ 'basso' trovato:")
    print(f"   ID: {basso.id}")
    print(f"   Attivo: {basso.attivo}")
    print(f"   Utente: {basso.utente.username}")
    print(f"   Tipo: {basso.tipo}")
    print(f"   Categoria: {basso.categoria}")
except Annuncio.DoesNotExist:
    print("❌ 'basso' non trovato nel database")
    basso = None

# 2. Verifica annunci 'synth'
print("\n" + "=" * 80)
print("STEP 2: Annunci 'synth'")
print("=" * 80)

synth_annunci = Annuncio.objects.filter(titolo__icontains='synth', attivo=True)
print(f"Annunci 'synth' attivi: {synth_annunci.count()}")
for ann in synth_annunci:
    print(f"   - {ann.utente.username} {ann.tipo}: '{ann.titolo}'")

# 3. Verifica cicli nel DB
print("\n" + "=" * 80)
print("STEP 3: Cicli nel database")
print("=" * 80)

cicli_db_validi = CicloScambio.objects.filter(valido=True)
cicli_db_invalidi = CicloScambio.objects.filter(valido=False)

print(f"Cicli validi nel DB: {cicli_db_validi.count()}")
print(f"Cicli invalidi nel DB: {cicli_db_invalidi.count()}")

if cicli_db_validi.count() > 0:
    print(f"\nDistribuzione per lunghezza:")
    for lunghezza in range(2, 7):
        count = cicli_db_validi.filter(lunghezza=lunghezza).count()
        print(f"   Lunghezza {lunghezza}: {count} cicli")

# 4. Verifica metadata ultimo calcolo
print("\n" + "=" * 80)
print("STEP 4: Metadata calcolo")
print("=" * 80)

try:
    metadata = CalcoloMetadata.get_or_create_singleton()
    print(f"Ultimo calcolo completo: {metadata.ultimo_calcolo_completo}")
    print(f"Ultimo calcolo incrementale: {metadata.ultimo_calcolo_incrementale}")
    print(f"Cicli totali: {metadata.cicli_totali}")
    print(f"Tempo ultimo calcolo: {metadata.tempo_ultimo_calcolo:.2f}s")
except Exception as e:
    print(f"⚠️ Errore leggendo metadata: {e}")

# 5. Test costruzione grafo
print("\n" + "=" * 80)
print("STEP 5: Test costruzione grafo con nuovo codice")
print("=" * 80)

finder = CycleFinder()
finder.costruisci_grafo()

print(f"Nodi nel grafo: {len(finder.grafo)}")
print(f"Collegamenti totali: {sum(len(v) for v in finder.grafo.values())}")

# Verifica se 'basso' è nel grafo
if basso and basso.attivo:
    user_basso = basso.utente.id
    if user_basso in finder.grafo:
        print(f"\n✅ L'utente di 'basso' (ID {user_basso}) È nel grafo!")
        print(f"   Collegamenti: {len(finder.grafo[user_basso])}")
        print(f"   Può scambiare con:")
        for user_id in finder.grafo[user_basso][:5]:  # Primi 5
            try:
                user = User.objects.get(id=user_id)
                print(f"      - {user.username} (ID: {user_id})")
            except:
                print(f"      - User ID: {user_id}")
    else:
        print(f"\n❌ L'utente di 'basso' (ID {user_basso}) NON è nel grafo!")
        print(f"   Questo significa che 'basso' non ha collegamenti validi")

# 6. Test ricerca cicli
print("\n" + "=" * 80)
print("STEP 6: Test ricerca cicli (manuale)")
print("=" * 80)

print("Cerco cicli con il nuovo algoritmo...")
cicli_trovati = finder.trova_tutti_cicli(max_length=6)

print(f"\n✅ Cicli trovati dall'algoritmo: {len(cicli_trovati)}")

if len(cicli_trovati) > 0:
    # Analizza qualità
    cicli_buoni = 0
    cicli_generici = 0

    for ciclo in cicli_trovati:
        _, ha_match = calcola_qualita_ciclo(ciclo, return_tipo_match=True)
        if ha_match:
            cicli_buoni += 1
        else:
            cicli_generici += 1

    print(f"\n📊 Analisi qualità:")
    print(f"   Con match titoli (VISIBILI): {cicli_buoni}")
    print(f"   Solo categoria (NASCOSTI): {cicli_generici}")

    # Mostra esempio
    if cicli_buoni > 0:
        print(f"\n   Esempio ciclo BUONO:")
        for ciclo in cicli_trovati:
            _, ha_match = calcola_qualita_ciclo(ciclo, return_tipo_match=True)
            if ha_match:
                for u in ciclo['utenti']:
                    offerta = u.get('offerta')
                    richiesta = u.get('richiede')
                    if offerta and richiesta:
                        print(f"      {u['user'].username}: offre '{offerta.titolo}' → cerca '{richiesta.titolo}'")
                break
else:
    print("\n❌ PROBLEMA: Nessun ciclo trovato dall'algoritmo!")

# 7. Confronto DB vs Algoritmo
print("\n" + "=" * 80)
print("STEP 7: Confronto DB vs Algoritmo")
print("=" * 80)

print(f"Cicli nel DB (validi): {cicli_db_validi.count()}")
print(f"Cicli trovati dall'algoritmo: {len(cicli_trovati)}")

if cicli_db_validi.count() == 0 and len(cicli_trovati) > 0:
    print("\n⚠️  DIVERGENZA: L'algoritmo trova cicli ma il DB è vuoto!")
    print("   Possibili cause:")
    print("   1. Il CycleCalculator non è stato eseguito dopo la fix")
    print("   2. Il CycleCalculator ha avuto un errore durante il salvataggio")
    print("   3. I cicli sono stati invalidati ma non ricalcolati")

elif cicli_db_validi.count() > 0 and len(cicli_trovati) == 0:
    print("\n⚠️  DIVERGENZA: Il DB ha cicli ma l'algoritmo non ne trova!")
    print("   Possibili cause:")
    print("   1. Gli annunci attivi sono cambiati rispetto all'ultimo calcolo")
    print("   2. La nuova logica del grafo ha un bug")

elif cicli_db_validi.count() == 0 and len(cicli_trovati) == 0:
    print("\n❌ PROBLEMA CRITICO: Né DB né algoritmo trovano cicli!")
    print("   Verifica:")
    print(f"   - Annunci attivi totali: {Annuncio.objects.filter(attivo=True).count()}")
    print(f"   - Utenti con annunci: {User.objects.filter(annuncio__attivo=True).distinct().count()}")

# 8. Verifica get_cicli_precalcolati
print("\n" + "=" * 80)
print("STEP 8: Test get_cicli_precalcolati()")
print("=" * 80)

try:
    risultato = get_cicli_precalcolati()
    scambi_diretti = risultato['scambi_diretti']
    catene = risultato['catene']

    print(f"✅ Caricati dal DB:")
    print(f"   Scambi diretti: {len(scambi_diretti)}")
    print(f"   Catene lunghe: {len(catene)}")
    print(f"   Totale: {risultato['totale']}")
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("🏁 DIAGNOSI FINALE")
print("=" * 80)

# Determina il problema
if len(cicli_trovati) > 0 and cicli_db_validi.count() == 0:
    print("\n🔧 SOLUZIONE: Eseguire il CycleCalculator per salvare i cicli nel DB")
    print("   Il nuovo codice funziona, ma i cicli non sono stati salvati")
elif len(cicli_trovati) == 0:
    print("\n❌ PROBLEMA: L'algoritmo non trova cicli!")
    print("   Verifica che ci siano abbastanza annunci attivi compatibili")
    print("   Controlla che 'synth' e altri annunci siano attivi")
elif cicli_buoni == 0:
    print("\n⚠️  Tutti i cicli hanno solo match categoria!")
    print("   Verifica che gli annunci abbiano parole in comune nei titoli")

print("\n" + "=" * 80)
