#!/usr/bin/env python
"""
Debug del filtro utente che blocca tutte le catene
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio
from django.contrib.auth.models import User
from scambi.matching import (
    trova_catene_scambio_ottimizzato,
    calcola_qualita_ciclo,
    filtra_catene_per_utente_ottimizzato
)

print("=" * 80)
print("🐛 DEBUG FILTRO UTENTE")
print("=" * 80)

username = input("\nInserisci username (INVIO per 'admin'): ").strip() or "admin"

try:
    user = User.objects.get(username=username)
    print(f"\n✅ Utente: {user.username} (ID: {user.id})")
except User.DoesNotExist:
    print(f"❌ Utente non trovato!")
    exit(1)

# Trova catene
print("\n🔍 Caricamento catene...")
catene = trova_catene_scambio_ottimizzato()
print(f"Catene totali: {len(catene)}")

# Filtra per qualità
print("\n🔍 Applicazione filtro qualità...")
catene_specifiche = []
for c in catene:
    punteggio, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
    if ha_match_titoli:
        catene_specifiche.append(c)

print(f"Catene dopo filtro qualità: {len(catene_specifiche)}")

if len(catene_specifiche) == 0:
    print("\n❌ Nessuna catena dopo il filtro qualità!")
    exit(0)

# DEBUG: Analizza struttura catene
print("\n" + "=" * 80)
print("🔍 ANALISI STRUTTURA CATENE")
print("=" * 80)

for i, catena in enumerate(catene_specifiche[:3], 1):
    print(f"\n📋 Catena {i}:")
    print(f"   Chiavi: {catena.keys()}")

    if 'utenti' in catena:
        print(f"   Numero utenti: {len(catena['utenti'])}")

        for j, u in enumerate(catena['utenti'], 1):
            print(f"\n   Utente {j}:")
            print(f"      Chiavi: {u.keys()}")

            # Verifica presenza campo 'user'
            if 'user' in u:
                print(f"      ✅ Ha campo 'user': {u['user']}")
                print(f"      Tipo: {type(u['user'])}")

                # Se è un oggetto User
                if hasattr(u['user'], 'id'):
                    print(f"      ID: {u['user'].id}")
                    print(f"      Username: {u['user'].username}")

                    # Verifica match con utente target
                    if u['user'].id == user.id:
                        print(f"      🎯 MATCH! Questo è {user.username}")
            else:
                print(f"      ❌ NON ha campo 'user'!")
                print(f"      Campi disponibili: {list(u.keys())}")

# Ora prova il filtro
print("\n" + "=" * 80)
print("🔍 TEST FILTRO UTENTE")
print("=" * 80)

try:
    scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
        [], catene_specifiche, user
    )

    print(f"\n✅ Filtro completato:")
    print(f"   Scambi diretti: {len(scambi_diretti_utente)}")
    print(f"   Catene lunghe: {len(catene_lunghe_utente)}")

    if len(catene_lunghe_utente) == 0:
        print(f"\n❌ PROBLEMA: Nessuna catena dopo il filtro!")

        # DEBUG: Prova manualmente
        print(f"\n🔍 Provo manualmente il filtro...")
        catene_manuali = []

        for catena in catene_specifiche:
            print(f"\n   Catena con {len(catena.get('utenti', []))} utenti:")

            # Prova a trovare l'utente
            trovato = False
            for u in catena.get('utenti', []):
                try:
                    if 'user' in u:
                        print(f"      Utente: {u['user'].username} (ID: {u['user'].id})")

                        if u['user'].id == user.id:
                            print(f"      🎯 MATCH CON {user.username}!")
                            trovato = True
                    else:
                        print(f"      ⚠️  Utente senza campo 'user': {u.keys()}")
                except Exception as e:
                    print(f"      ❌ Errore: {e}")

            if trovato:
                catene_manuali.append(catena)
                print(f"      ✅ Catena aggiunta!")
            else:
                print(f"      ❌ Utente {user.username} non trovato in questa catena")

        print(f"\n   Catene trovate manualmente: {len(catene_manuali)}")

        if len(catene_manuali) > 0 and len(catene_lunghe_utente) == 0:
            print(f"\n   ⚠️  BUG CONFERMATO: Il filtro manuale trova catene, ma la funzione no!")
    else:
        print(f"\n✅ Filtro OK! Trovate {len(catene_lunghe_utente)} catene")

except Exception as e:
    print(f"\n❌ ERRORE durante filtro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("🏁 DEBUG COMPLETATO")
print("=" * 80)
