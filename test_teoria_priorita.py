#!/usr/bin/env python
"""
Test teoria: Il CycleFinder trova prima i cicli con match categoria,
e poi quelli con match titolo non vengono trovati perché gli utenti
sono già "consumati" nei cicli categoria.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio
from django.contrib.auth.models import User
from scambi.matching import CycleFinder, calcola_qualita_ciclo

print("=" * 80)
print("🧪 TEST TEORIA: Priorità cicli categoria vs titolo")
print("=" * 80)

# Costruisci il grafo
finder = CycleFinder()
finder.costruisci_grafo()

print(f"\nGrafo costruito:")
print(f"   Nodi: {len(finder.grafo)}")
print(f"   Collegamenti: {sum(len(v) for v in finder.grafo.values())}")

# Trova TUTTI i cicli
print(f"\n🔍 Ricerca TUTTI i cicli...")
tutti_cicli = finder.trova_tutti_cicli(max_length=6)

print(f"Cicli trovati: {len(tutti_cicli)}")

# Analizza per qualità
cicli_per_qualita = {
    'alta': [],  # match titolo
    'bassa': []  # solo categoria
}

for ciclo in tutti_cicli:
    punteggio, ha_match_titoli = calcola_qualita_ciclo(ciclo, return_tipo_match=True)

    if ha_match_titoli:
        cicli_per_qualita['alta'].append(ciclo)
    else:
        cicli_per_qualita['bassa'].append(ciclo)

print(f"\n📊 Distribuzione per qualità:")
print(f"   Alta qualità (match titolo): {len(cicli_per_qualita['alta'])}")
print(f"   Bassa qualità (solo categoria): {len(cicli_per_qualita['bassa'])}")

# Analizza utenti coinvolti
utenti_in_cicli_alta = set()
utenti_in_cicli_bassa = set()

for ciclo in cicli_per_qualita['alta']:
    for u in ciclo['utenti']:
        utenti_in_cicli_alta.add(u['user'].id)

for ciclo in cicli_per_qualita['bassa']:
    for u in ciclo['utenti']:
        utenti_in_cicli_bassa.add(u['user'].id)

print(f"\n👥 Utenti coinvolti:")
print(f"   In cicli alta qualità: {len(utenti_in_cicli_alta)}")
print(f"   In cicli bassa qualità: {len(utenti_in_cicli_bassa)}")
print(f"   In entrambi: {len(utenti_in_cicli_alta & utenti_in_cicli_bassa)}")

# Mostra esempi
if len(cicli_per_qualita['alta']) > 0:
    print(f"\n✅ Esempio ciclo ALTA qualità:")
    ciclo = cicli_per_qualita['alta'][0]
    for u in ciclo['utenti']:
        offerta = u.get('offerta')
        richiesta = u.get('richiede')
        if offerta and richiesta:
            print(f"   {u['user'].username}: offre '{offerta.titolo}' → cerca '{richiesta.titolo}'")

if len(cicli_per_qualita['bassa']) > 0:
    print(f"\n⚠️  Esempio ciclo BASSA qualità:")
    ciclo = cicli_per_qualita['bassa'][0]
    for u in ciclo['utenti']:
        offerta = u.get('offerta')
        richiesta = u.get('richiede')
        if offerta and richiesta:
            print(f"   {u['user'].username}: offre '{offerta.titolo}' → cerca '{richiesta.titolo}'")

# TEORIA: Verifica se ci sono utenti che hanno cicli solo bassa qualità
utenti_solo_bassa = utenti_in_cicli_bassa - utenti_in_cicli_alta

if utenti_solo_bassa:
    print(f"\n⚠️  PROBLEMA: {len(utenti_solo_bassa)} utenti hanno SOLO cicli bassa qualità!")
    print(f"   Questi utenti non vedranno NESSUNA catena!")

    for user_id in list(utenti_solo_bassa)[:3]:  # Primi 3
        try:
            user = User.objects.get(id=user_id)
            print(f"      - {user.username}")
        except:
            pass
else:
    print(f"\n✅ Tutti gli utenti in cicli bassa hanno anche cicli alta qualità")

print("\n" + "=" * 80)
print("🔍 DIAGNOSI")
print("=" * 80)

if len(cicli_per_qualita['alta']) == 0 and len(cicli_per_qualita['bassa']) > 0:
    print("\n❌ TEORIA CONFERMATA!")
    print("   Il CycleFinder trova SOLO cicli con match categoria.")
    print("   I cicli con match titolo NON vengono trovati.")
    print("\n   CAUSA POSSIBILE:")
    print("   - Gli utenti sono 'consumati' nei cicli categoria")
    print("   - L'algoritmo DFS esplora prima i match categoria")
    print("   - Quando arriva ai match titolo, gli utenti sono già usati")
    print("\n   SOLUZIONE:")
    print("   - Modificare l'algoritmo DFS per dare PRIORITÀ ai match titolo")
    print("   - Oppure trovare TUTTI i cicli senza deduplicazione per utente")

elif len(cicli_per_qualita['alta']) > 0:
    print("\n✅ OK! Il CycleFinder trova sia cicli alta che bassa qualità")
    print("   Il filtro nella view dovrebbe mostrare solo quelli alta qualità")

print("\n" + "=" * 80)
