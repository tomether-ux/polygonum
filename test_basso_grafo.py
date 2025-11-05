#!/usr/bin/env python
"""
Test per capire perché 'basso' entra nel grafo
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio
from scambi.matching import oggetti_compatibili_con_tipo
from django.contrib.auth.models import User

print("=" * 80)
print("🧪 TEST: Perché 'basso' entra nel grafo?")
print("=" * 80)

# Trova 'basso'
basso = Annuncio.objects.get(titolo__iexact='basso', attivo=True)
admin = basso.utente

print(f"\n📋 'basso' Info:")
print(f"   Utente: {admin.username}")
print(f"   Tipo: {basso.tipo}")  # dovrebbe essere 'cerco'
print(f"   Titolo: {basso.titolo}")
print(f"   Categoria: {basso.categoria}")

# Test: admin offre qualcosa ad altri utenti?
print(f"\n" + "=" * 80)
print(f"TEST 1: {admin.username} OFFRE qualcosa?")
print("=" * 80)

offerte_admin = Annuncio.objects.filter(utente=admin, tipo='offro', attivo=True)
print(f"\nAnnunci 'offro' di {admin.username}: {offerte_admin.count()}")
for off in offerte_admin:
    print(f"   - '{off.titolo}'")

# Test: altri utenti offrono qualcosa che matcha con 'basso'?
print(f"\n" + "=" * 80)
print(f"TEST 2: Altri utenti OFFRONO qualcosa che matcha con 'basso'?")
print("=" * 80)

altri_utenti = User.objects.exclude(id=admin.id).filter(annuncio__attivo=True).distinct()
print(f"\nAltri utenti con annunci attivi: {altri_utenti.count()}")

match_trovati = []

for utente_b in altri_utenti:
    offerte_b = Annuncio.objects.filter(utente=utente_b, tipo='offro', attivo=True)

    for offerta_b in offerte_b:
        # Verifica se quello che B offre matcha con quello che admin cerca ('basso')
        compatible, tipo_match = oggetti_compatibili_con_tipo(offerta_b, basso)

        if compatible:
            match_trovati.append({
                'utente': utente_b.username,
                'offerta': offerta_b.titolo,
                'tipo_match': tipo_match
            })

            print(f"\n✅ MATCH: {utente_b.username} offre '{offerta_b.titolo}' → admin cerca 'basso'")
            print(f"   Tipo match: {tipo_match}")
            print(f"   Accettato dal grafo? {'SÌ' if tipo_match in ['specifico', 'parziale', 'sinonimo'] else 'NO'}")

if not match_trovati:
    print(f"\n❌ Nessun utente offre qualcosa compatibile con 'basso'")

print(f"\n" + "=" * 80)
print(f"TEST 3: admin PUÒ DARE qualcosa ad altri?")
print("=" * 80)

# Questo è il test normale: admin offre → altri cercano
# Se admin non offre nulla, non può dare niente

if offerte_admin.count() == 0:
    print(f"\n❌ {admin.username} non offre nulla → NON può dare niente ad altri")
    print(f"   Quindi admin può SOLO RICEVERE, non dare")

print(f"\n" + "=" * 80)
print(f"🔍 CONCLUSIONE")
print("=" * 80)

print(f"\nadmin entra nel grafo se:")
print(f"   1. admin può RICEVERE da almeno un utente (qualcuno gli offre qualcosa che matcha 'basso')")
print(f"   2. admin può DARE ad almeno un utente (admin offre qualcosa che altri cercano)")

print(f"\nMatch trovati per 'basso':")
print(f"   Utenti che offrono qualcosa compatibile con 'basso': {len(match_trovati)}")

if match_trovati:
    print(f"\n   Dettaglio:")
    for m in match_trovati:
        print(f"      - {m['utente']}: '{m['offerta']}' (tipo: {m['tipo_match']})")

    match_validi = [m for m in match_trovati if m['tipo_match'] in ['specifico', 'parziale', 'sinonimo']]
    print(f"\n   Match VALIDI (specifico/parziale/sinonimo): {len(match_validi)}")

    if match_validi:
        print(f"\n   ❗ PROBLEMA TROVATO!")
        print(f"   'basso' entra nel grafo perché {len(match_validi)} utenti offrono qualcosa")
        print(f"   che matcha con 'basso' (tipo match valido)!")
    else:
        print(f"\n   ✅ Tutti i match sono categoria/generico → 'basso' NON dovrebbe entrare")

print(f"\n" + "=" * 80)
