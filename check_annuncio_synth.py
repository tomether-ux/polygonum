#!/usr/bin/env python
"""
Script per verificare lo stato dell'annuncio 'synth'
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio
from django.contrib.auth.models import User

print("=" * 80)
print("🔍 VERIFICA ANNUNCIO 'SYNTH'")
print("=" * 80)

# Cerca tutti gli annunci con "synth" nel titolo
annunci_synth = Annuncio.objects.filter(titolo__icontains='synth')

print(f"\n📊 Annunci trovati con 'synth' nel titolo: {annunci_synth.count()}")

for ann in annunci_synth:
    print(f"\n{'='*60}")
    print(f"ID: {ann.id}")
    print(f"Titolo: '{ann.titolo}'")
    print(f"Descrizione: '{ann.descrizione}'")
    print(f"Tipo: {ann.tipo}")
    print(f"Categoria: {ann.categoria.nome if ann.categoria else 'Nessuna'}")
    print(f"Utente: {ann.utente.username}")
    print(f"ATTIVO: {'✅ SI' if ann.attivo else '❌ NO'}")
    print(f"Data creazione: {ann.data_creazione}")
    print(f"Prezzo stimato: {ann.prezzo_stimato}€")

# Cerca anche annunci di admin e hhh per verificare gli scambi
print("\n" + "=" * 80)
print("🔍 ANNUNCI DEGLI UTENTI COINVOLTI (admin e hhh)")
print("=" * 80)

for username in ['admin', 'hhh']:
    try:
        user = User.objects.get(username=username)
        annunci_user = Annuncio.objects.filter(utente=user).order_by('-data_creazione')

        print(f"\n👤 {username}:")
        print(f"   Totale annunci: {annunci_user.count()}")
        print(f"   Attivi: {annunci_user.filter(attivo=True).count()}")
        print(f"   Inattivi: {annunci_user.filter(attivo=False).count()}")

        print("\n   Dettagli annunci:")
        for ann in annunci_user:
            status = "✅ ATTIVO" if ann.attivo else "❌ INATTIVO"
            print(f"      - [{status}] {ann.tipo}: '{ann.titolo}' (ID: {ann.id})")

    except User.DoesNotExist:
        print(f"\n   ❌ Utente '{username}' non trovato")

print("\n" + "=" * 80)
