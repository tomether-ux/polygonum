#!/usr/bin/env python
"""
Script per testare il matching tra gli annunci 'synth'
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio
from django.contrib.auth.models import User
from scambi.matching import oggetti_compatibili_con_tipo, oggetti_compatibili_avanzato

print("=" * 80)
print("🔍 TEST MATCHING ANNUNCI 'SYNTH'")
print("=" * 80)

# Trova gli utenti
try:
    admin = User.objects.get(username='admin')
    hhh = User.objects.get(username='hhh')
    print(f"\n✅ Utenti trovati: admin (ID: {admin.id}), hhh (ID: {hhh.id})")
except User.DoesNotExist as e:
    print(f"\n❌ Errore: {e}")
    exit(1)

# Trova gli annunci synth
annunci_synth = Annuncio.objects.filter(titolo__icontains='synth', attivo=True)

print(f"\n📊 Annunci 'synth' attivi trovati: {annunci_synth.count()}")

synth_admin_cerco = None
synth_hhh_offro = None

for ann in annunci_synth:
    print(f"\n   - {ann.tipo.upper()}: '{ann.titolo}' (utente: {ann.utente.username}, ID: {ann.id})")

    if ann.utente.username == 'admin' and ann.tipo == 'cerco':
        synth_admin_cerco = ann
        print(f"     ✅ Questo è il CERCO di admin")

    if ann.utente.username == 'hhh' and ann.tipo == 'offro':
        synth_hhh_offro = ann
        print(f"     ✅ Questo è l'OFFRO di hhh")

print("\n" + "=" * 80)
print("🧪 TEST MATCHING: hhh OFFRE synth → admin CERCA synth")
print("=" * 80)

if not synth_hhh_offro:
    print("\n❌ PROBLEMA: Non trovato annuncio OFFRO 'synth' di hhh!")
    print("   Verifica che esista un annuncio tipo='offro' con 'synth' nel titolo di utente 'hhh'")
else:
    print(f"\n✅ Annuncio OFFRO trovato:")
    print(f"   Titolo: '{synth_hhh_offro.titolo}'")
    print(f"   Descrizione: '{synth_hhh_offro.descrizione}'")
    print(f"   Categoria: {synth_hhh_offro.categoria.nome if synth_hhh_offro.categoria else 'Nessuna'}")

if not synth_admin_cerco:
    print("\n❌ PROBLEMA: Non trovato annuncio CERCO 'synth' di admin!")
    print("   Verifica che esista un annuncio tipo='cerco' con 'synth' nel titolo di utente 'admin'")
else:
    print(f"\n✅ Annuncio CERCO trovato:")
    print(f"   Titolo: '{synth_admin_cerco.titolo}'")
    print(f"   Descrizione: '{synth_admin_cerco.descrizione}'")
    print(f"   Categoria: {synth_admin_cerco.categoria.nome if synth_admin_cerco.categoria else 'Nessuna'}")

if synth_hhh_offro and synth_admin_cerco:
    print("\n" + "=" * 80)
    print("🔍 ESECUZIONE TEST MATCHING")
    print("=" * 80)

    try:
        # Test con oggetti_compatibili_con_tipo (restituisce anche tipo di match)
        print("\n1️⃣ Test con oggetti_compatibili_con_tipo():")
        compatibile, tipo_match = oggetti_compatibili_con_tipo(synth_hhh_offro, synth_admin_cerco)

        if compatibile:
            print(f"   ✅ MATCH TROVATO!")
            print(f"   Tipo di match: {tipo_match}")
        else:
            print(f"   ❌ NESSUN MATCH")
            print(f"   Tipo restituito: {tipo_match}")

        # Test con oggetti_compatibili_avanzato (più dettagliato)
        print("\n2️⃣ Test con oggetti_compatibili_avanzato():")
        compatibile_adv, punteggio, dettagli = oggetti_compatibili_avanzato(
            synth_hhh_offro, synth_admin_cerco, distanza_km=50
        )

        if compatibile_adv:
            print(f"   ✅ MATCH TROVATO!")
            print(f"   Punteggio: {punteggio}")
            print(f"   Dettagli: {dettagli}")
        else:
            print(f"   ❌ NESSUN MATCH")
            print(f"   Punteggio: {punteggio}")
            print(f"   Dettagli: {dettagli}")

    except Exception as e:
        print(f"\n❌ ERRORE durante test matching: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("🔍 DETTAGLI COMPLETI ANNUNCI PER DEBUG")
print("=" * 80)

if synth_hhh_offro:
    print(f"\n📋 OFFRO 'synth' di hhh (ID: {synth_hhh_offro.id}):")
    print(f"   Titolo esatto: '{synth_hhh_offro.titolo}'")
    print(f"   Descrizione: '{synth_hhh_offro.descrizione}'")
    print(f"   Tipo: {synth_hhh_offro.tipo}")
    print(f"   Categoria: {synth_hhh_offro.categoria}")
    print(f"   Attivo: {synth_hhh_offro.attivo}")
    print(f"   Città: {synth_hhh_offro.citta}")
    print(f"   Prezzo: {synth_hhh_offro.prezzo_stimato}")

if synth_admin_cerco:
    print(f"\n📋 CERCO 'synth' di admin (ID: {synth_admin_cerco.id}):")
    print(f"   Titolo esatto: '{synth_admin_cerco.titolo}'")
    print(f"   Descrizione: '{synth_admin_cerco.descrizione}'")
    print(f"   Tipo: {synth_admin_cerco.tipo}")
    print(f"   Categoria: {synth_admin_cerco.categoria}")
    print(f"   Attivo: {synth_admin_cerco.attivo}")
    print(f"   Città: {synth_admin_cerco.citta}")
    print(f"   Prezzo: {synth_admin_cerco.prezzo_stimato}")

print("\n" + "=" * 80)
print("🏁 TEST COMPLETATO")
print("=" * 80)
