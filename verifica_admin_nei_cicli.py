#!/usr/bin/env python
"""
Verifica se admin è presente nei cicli del database
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import CicloScambio, Annuncio
from django.contrib.auth.models import User

print("=" * 80)
print("🔍 VERIFICA ADMIN NEI CICLI DB")
print("=" * 80)

try:
    admin = User.objects.get(username='admin')
    print(f"\n✅ Admin trovato (ID: {admin.id})")
except User.DoesNotExist:
    print("❌ Admin non trovato!")
    exit(1)

# Verifica annunci admin
annunci_admin = Annuncio.objects.filter(utente=admin)
print(f"\n📊 Annunci di admin:")
print(f"   Totali: {annunci_admin.count()}")
print(f"   Attivi: {annunci_admin.filter(attivo=True).count()}")
print(f"   Inattivi: {annunci_admin.filter(attivo=False).count()}")

print(f"\n   Dettagli:")
for ann in annunci_admin:
    status = "✅" if ann.attivo else "❌"
    print(f"      {status} {ann.tipo}: '{ann.titolo}' (ID: {ann.id})")

# Verifica cicli
cicli_validi = CicloScambio.objects.filter(valido=True)
print(f"\n🔄 Cicli validi nel DB: {cicli_validi.count()}")

# Conta cicli che includono admin
cicli_con_admin = 0
cicli_dettagli = []

for ciclo in cicli_validi:
    if admin.id in ciclo.users:
        cicli_con_admin += 1
        cicli_dettagli.append({
            'id': ciclo.id,
            'users': ciclo.users,
            'calcolato': ciclo.calcolato_at
        })

print(f"🎯 Cicli che includono admin (ID {admin.id}): {cicli_con_admin}")

if cicli_con_admin == 0:
    print(f"\n❌ PROBLEMA CRITICO: Admin non è in NESSUN ciclo del database!")
    print(f"\n💡 POSSIBILI CAUSE:")
    print(f"   1. I cicli sono stati calcolati PRIMA che admin creasse gli annunci")
    print(f"   2. Gli annunci di admin erano inattivi quando i cicli sono stati calcolati")
    print(f"   3. Il CycleCalculator ha un bug che esclude admin")
    print(f"   4. I cicli nel DB sono obsoleti")

    print(f"\n🔧 SOLUZIONE:")
    print(f"   1. Verifica che tutti gli annunci di admin siano ATTIVI")
    print(f"   2. Ricalcola i cicli eseguendo il CycleCalculator")
    print(f"   3. Oppure invalida e ricalcola con: python manage.py calcola_cicli --force")
else:
    print(f"\n✅ Admin è presente in {cicli_con_admin} cicli")

    # Mostra primi 5 cicli
    print(f"\n   Primi 5 cicli con admin:")
    for ciclo_info in cicli_dettagli[:5]:
        print(f"      - Ciclo ID {ciclo_info['id']}")
        print(f"        Users: {ciclo_info['users']}")
        print(f"        Calcolato: {ciclo_info['calcolato']}")

# Verifica quando sono stati calcolati i cicli
if cicli_validi.exists():
    ciclo_recente = cicli_validi.order_by('-calcolato_at').first()
    print(f"\n📅 Ciclo più recente:")
    print(f"   ID: {ciclo_recente.id}")
    print(f"   Calcolato: {ciclo_recente.calcolato_at}")

# Verifica annunci admin più recenti
if annunci_admin.exists():
    annuncio_recente = annunci_admin.order_by('-data_creazione').first()
    print(f"\n📅 Annuncio admin più recente:")
    print(f"   Titolo: '{annuncio_recente.titolo}'")
    print(f"   Creato: {annuncio_recente.data_creazione}")
    print(f"   Attivo: {'✅' if annuncio_recente.attivo else '❌'}")

    # Confronta date
    if cicli_validi.exists():
        if annuncio_recente.data_creazione > ciclo_recente.calcolato_at:
            print(f"\n   ⚠️  L'annuncio è PIÙ RECENTE del ciclo più recente!")
            print(f"   I cicli sono OBSOLETI e vanno ricalcolati!")

print("\n" + "=" * 80)
print("🏁 VERIFICA COMPLETATA")
print("=" * 80)

if cicli_con_admin == 0:
    print("\n🚨 AZIONE RICHIESTA:")
    print("   Esegui il CycleCalculator per ricalcolare i cicli con i dati aggiornati")
