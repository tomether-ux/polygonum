#!/usr/bin/env python
"""
Script per verificare se i limiti premium/free hanno causato la disattivazione di annunci
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio, UserProfile
from django.contrib.auth.models import User

print("=" * 80)
print("🔍 VERIFICA LIMITI ANNUNCI E STATUS PREMIUM")
print("=" * 80)

# Controlla admin e hhh
for username in ['admin', 'hhh']:
    try:
        user = User.objects.get(username=username)
        profilo, created = UserProfile.objects.get_or_create(user=user)

        print(f"\n{'='*70}")
        print(f"👤 UTENTE: {username} (ID: {user.id})")
        print(f"{'='*70}")

        # Status premium
        if profilo.is_premium:
            print(f"   ⭐ STATUS: PREMIUM")
            if profilo.premium_scadenza:
                print(f"   Scadenza: {profilo.premium_scadenza}")
        else:
            print(f"   🆓 STATUS: FREE")

        # Conta annunci
        annunci_offro_attivi = Annuncio.objects.filter(utente=user, tipo='offro', attivo=True).count()
        annunci_cerco_attivi = Annuncio.objects.filter(utente=user, tipo='cerco', attivo=True).count()
        annunci_offro_inattivi = Annuncio.objects.filter(utente=user, tipo='offro', attivo=False).count()
        annunci_cerco_inattivi = Annuncio.objects.filter(utente=user, tipo='cerco', attivo=False).count()

        print(f"\n   📊 ANNUNCI OFFRO:")
        print(f"      Attivi: {annunci_offro_attivi}")
        print(f"      Inattivi: {annunci_offro_inattivi}")
        limite_offro = profilo.get_limite_annunci('offro')
        if limite_offro:
            print(f"      Limite: {limite_offro}")
            if annunci_offro_attivi > limite_offro:
                print(f"      ⚠️  SUPERATO IL LIMITE! ({annunci_offro_attivi}/{limite_offro})")
        else:
            print(f"      Limite: Illimitato (Premium)")

        print(f"\n   📊 ANNUNCI CERCO:")
        print(f"      Attivi: {annunci_cerco_attivi}")
        print(f"      Inattivi: {annunci_cerco_inattivi}")
        limite_cerco = profilo.get_limite_annunci('cerco')
        if limite_cerco:
            print(f"      Limite: {limite_cerco}")
            if annunci_cerco_attivi > limite_cerco:
                print(f"      ⚠️  SUPERATO IL LIMITE! ({annunci_cerco_attivi}/{limite_cerco})")
        else:
            print(f"      Limite: Illimitato (Premium)")

        # Mostra dettagli annunci
        print(f"\n   📋 DETTAGLI ANNUNCI:")

        annunci_offro = Annuncio.objects.filter(utente=user, tipo='offro').order_by('-attivo', '-data_creazione')
        if annunci_offro:
            print(f"\n      OFFRO:")
            for i, ann in enumerate(annunci_offro, 1):
                status = "✅ ATTIVO" if ann.attivo else "❌ INATTIVO"
                print(f"         {i}. [{status}] '{ann.titolo}' (ID: {ann.id})")
                if 'synth' in ann.titolo.lower():
                    print(f"            🎹 ← Questo contiene 'synth'!")

        annunci_cerco = Annuncio.objects.filter(utente=user, tipo='cerco').order_by('-attivo', '-data_creazione')
        if annunci_cerco:
            print(f"\n      CERCO:")
            for i, ann in enumerate(annunci_cerco, 1):
                status = "✅ ATTIVO" if ann.attivo else "❌ INATTIVO"
                print(f"         {i}. [{status}] '{ann.titolo}' (ID: {ann.id})")
                if 'synth' in ann.titolo.lower():
                    print(f"            🎹 ← Questo contiene 'synth'!")

        # DIAGNOSI
        print(f"\n   🔍 DIAGNOSI:")
        totale_attivi = annunci_offro_attivi + annunci_cerco_attivi
        totale_inattivi = annunci_offro_inattivi + annunci_cerco_inattivi

        if not profilo.is_premium:
            if annunci_offro_attivi > 5 or annunci_cerco_attivi > 5:
                print(f"      ❌ PROBLEMA: L'utente FREE ha più di 5 annunci attivi!")
                print(f"         Questo NON dovrebbe essere possibile con i limiti implementati.")

            if totale_inattivi > 0:
                print(f"      ⚠️  L'utente ha {totale_inattivi} annunci INATTIVI")
                print(f"         Potrebbero essere stati disattivati per rispettare i limiti.")

                # Controlla se l'annuncio synth è tra quelli inattivi
                synth_inattivi = Annuncio.objects.filter(
                    utente=user,
                    attivo=False,
                    titolo__icontains='synth'
                )
                if synth_inattivi.exists():
                    print(f"\n      🎹 TROVATO ANNUNCIO 'SYNTH' INATTIVO!")
                    for ann in synth_inattivi:
                        print(f"         - '{ann.titolo}' (ID: {ann.id}, tipo: {ann.tipo})")
                        print(f"         ⚠️  Questo potrebbe essere il problema!")

    except User.DoesNotExist:
        print(f"\n❌ Utente '{username}' non trovato")

print("\n" + "=" * 80)
print("🏁 VERIFICA COMPLETATA")
print("=" * 80)

print("\n💡 POSSIBILI CAUSE DEL PROBLEMA:")
print("   1. Admin è FREE e ha superato il limite di 5 annunci")
print("   2. Admin ha dovuto disattivare l'annuncio 'synth' per rispettare i limiti")
print("   3. Il sistema di limiti ha automaticamente disattivato alcuni annunci")
print("   4. L'implementazione dei limiti ha un bug che disattiva annunci esistenti")
