#!/usr/bin/env python
"""
Script per rendere un utente PREMIUM
Uso: python make_user_premium.py
"""

import os
import sys
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import UserProfile
from django.contrib.auth.models import User
from django.utils import timezone

print("=" * 80)
print("⭐ RENDI UTENTE PREMIUM")
print("=" * 80)

# Chiedi username
username = input("\nInserisci username da rendere Premium (premi INVIO per 'admin'): ").strip() or "admin"

try:
    user = User.objects.get(username=username)
    print(f"\n✅ Utente trovato: {user.username} (ID: {user.id})")
except User.DoesNotExist:
    print(f"\n❌ Errore: Utente '{username}' non trovato!")
    sys.exit(1)

# Ottieni o crea profilo
profilo, created = UserProfile.objects.get_or_create(user=user)

if created:
    print(f"   📝 Profilo creato per {user.username}")
else:
    print(f"   📝 Profilo esistente trovato")

# Verifica status attuale
if profilo.is_premium:
    print(f"\n   ℹ️  L'utente è già PREMIUM")
    if profilo.premium_scadenza:
        print(f"   Scadenza attuale: {profilo.premium_scadenza}")
        risposta = input("\n   Vuoi estendere l'abbonamento? (s/n): ").strip().lower()
        if risposta != 's':
            print("\n   Operazione annullata.")
            sys.exit(0)
else:
    print(f"\n   ℹ️  L'utente è attualmente FREE")

# Chiedi durata
print("\n📅 Durata abbonamento:")
print("   1. 1 mese")
print("   2. 3 mesi")
print("   3. 6 mesi")
print("   4. 1 anno")
print("   5. Illimitato (per utenti di test)")

scelta = input("\nScegli (1-5) [default: 5]: ").strip() or "5"

mesi_map = {
    '1': 1,
    '2': 3,
    '3': 6,
    '4': 12,
    '5': 999  # Praticamente illimitato
}

mesi = mesi_map.get(scelta, 999)

# Calcola scadenza
if profilo.premium_scadenza and profilo.is_premium:
    # Estendi dalla scadenza esistente
    nuova_scadenza = profilo.premium_scadenza + timedelta(days=30*mesi)
    print(f"\n   ✅ Estensione da {profilo.premium_scadenza.date()}")
else:
    # Nuova sottoscrizione
    nuova_scadenza = timezone.now() + timedelta(days=30*mesi)
    print(f"\n   ✅ Nuova sottoscrizione da oggi")

# Conferma
print(f"\n{'='*70}")
print(f"📋 RIEPILOGO:")
print(f"   Utente: {user.username}")
print(f"   Status: {'Estensione' if profilo.is_premium else 'Nuovo'} abbonamento Premium")
print(f"   Durata: {mesi} mesi")
print(f"   Scadenza: {nuova_scadenza.date()}")
print(f"{'='*70}")

conferma = input("\n✅ Confermi? (s/n): ").strip().lower()

if conferma == 's':
    # Applica modifiche
    profilo.is_premium = True
    profilo.premium_scadenza = nuova_scadenza
    profilo.save()

    print(f"\n🎉 SUCCESSO!")
    print(f"   {user.username} è ora PREMIUM fino al {nuova_scadenza.date()}")
    print(f"\n   📊 Benefici attivati:")
    print(f"      ✅ Annunci illimitati")
    print(f"      ✅ Badge Premium")
    print(f"      ✅ Priorità nelle catene")
    print(f"      ✅ Nessuna pubblicità")
else:
    print("\n❌ Operazione annullata.")

print("\n" + "=" * 80)
