#!/usr/bin/env python
"""
Diagnosi del problema 'basso' per produzione
Spiega perché 'basso' blocca le catene con 'synth'
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio
from scambi.matching import (
    trova_catene_scambio_ottimizzato,
    calcola_qualita_ciclo
)

print("=" * 80)
print("🔍 DIAGNOSI: Perché 'basso' blocca le catene 'synth'?")
print("=" * 80)

# Controlla se basso è attivo
basso_attivo = Annuncio.objects.filter(titolo__iexact='basso', attivo=True).exists()
synth_count = Annuncio.objects.filter(titolo__icontains='synth', attivo=True).count()

print(f"\n📊 Situazione attuale:")
print(f"   'basso' attivo: {'✅ SI' if basso_attivo else '❌ NO (disattivato)'}")
print(f"   Annunci 'synth' attivi: {synth_count}")

# Calcola catene
print(f"\n🔍 Calcolo catene con trova_catene_scambio_ottimizzato()...")
catene = trova_catene_scambio_ottimizzato()
print(f"   Catene totali trovate: {len(catene)}")

# Analizza qualità
catene_buone = []
catene_generiche = []

for c in catene:
    _, ha_match = calcola_qualita_ciclo(c, return_tipo_match=True)
    if ha_match:
        catene_buone.append(c)
    else:
        catene_generiche.append(c)

print(f"\n📊 Analisi qualità:")
print(f"   Catene con match titoli (BUONE): {len(catene_buone)}")
print(f"   Catene solo categoria (GENERICHE/BLOCCATE): {len(catene_generiche)}")

# Mostra alcune catene
if catene_generiche:
    print(f"\n   Esempio catena GENERICA (viene bloccata):")
    c = catene_generiche[0]
    for u in c.get('utenti', []):
        offerta = u.get('offerta')
        richiesta = u.get('richiede')
        if offerta and richiesta:
            print(f"      {u['nome']}: offre '{offerta.titolo}' → cerca '{richiesta.titolo}'")

if catene_buone:
    print(f"\n   Esempio catena BUONA (dovrebbe essere visibile):")
    c = catene_buone[0]
    for u in c.get('utenti', []):
        offerta = u.get('offerta')
        richiesta = u.get('richiede')
        if offerta and richiesta:
            print(f"      {u['nome']}: offre '{offerta.titolo}' → cerca '{richiesta.titolo}'")

print("\n" + "=" * 80)
print("💡 SPIEGAZIONE DEL PROBLEMA")
print("=" * 80)

if basso_attivo:
    print("""
QUANDO 'BASSO' È ATTIVO:

Il problema NON è nel filtro qualità (che funziona correttamente),
ma nell'ALGORITMO trova_catene_scambio_ottimizzato().

IPOTESI 1: 'basso' crea cicli SOLO con match categoria
   - L'algoritmo trova cicli che includono 'basso'
   - Questi cicli hanno SOLO match categoria (generico)
   - Il filtro li blocca (correttamente)
   - Ma l'algoritmo NON trova le catene con 'synth' perché:
     a) Gli utenti sono già "consumati" nei cicli con 'basso'
     b) L'algoritmo ha un limite sul numero di catene per utente
     c) Le catene con 'basso' hanno priorità e mascherano quelle con 'synth'

IPOTESI 2: Problema di deduplicazione
   - L'algoritmo trova sia catene con 'basso' che con 'synth'
   - Ma la deduplicazione rimuove le catene 'synth' perché coinvolgono
     gli stessi utenti delle catene 'basso'

IPOTESI 3: Problema nel ciclo di ricerca DFS
   - L'algoritmo esplora prima i match con 'basso' (categoria)
   - Quando trova un ciclo valido, si ferma
   - Non esplora altre possibilità con 'synth' (match titolo)

SOLUZIONE TEMPORANEA:
   ✅ Disattivare 'basso' fa ricomparire le catene 'synth'

SOLUZIONE PERMANENTE:
   Modificare trova_catene_scambio_ottimizzato() per:
   1. Dare priorità ai match titolo rispetto ai match categoria
   2. Trovare TUTTE le catene possibili, non fermarsi alla prima
   3. Non deduplic are catene con qualità diverse
""")
else:
    print("""
QUANDO 'BASSO' È DISATTIVATO:

✅ Le catene con 'synth' vengono trovate correttamente
✅ Il filtro qualità funziona come previsto

Il problema era che 'basso' (con solo match categoria) interferiva
con la ricerca delle catene con match titolo.

RACCOMANDAZIONE:
   Se vuoi riattivare 'basso', devi prima correggere l'algoritmo
   trova_catene_scambio_ottimizzato() per gestire correttamente
   la priorità tra match titolo e match categoria.
""")

print("=" * 80)
print("\n🔧 PROSSIMI STEP:")
print("   1. Confermare quale ipotesi è corretta")
print("   2. Modificare trova_catene_scambio_ottimizzato() nel CycleCalculator")
print("   3. Ricalcolare i cicli con la nuova logica")
print("   4. Riattivare 'basso' e verificare che funzioni")

print("\n" + "=" * 80)
