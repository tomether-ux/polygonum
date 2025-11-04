#!/usr/bin/env python
"""
Analizza perché l'annuncio 'basso' blocca tutte le catene
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio, CicloScambio
from django.contrib.auth.models import User
from scambi.matching import (
    trova_catene_scambio_ottimizzato,
    calcola_qualita_ciclo,
    oggetti_compatibili_con_tipo
)

print("=" * 80)
print("🔍 ANALISI ANNUNCIO 'BASSO' E BLOCKING")
print("=" * 80)

# Trova l'annuncio 'basso'
try:
    basso = Annuncio.objects.get(titolo__iexact='basso', attivo=True)
    print(f"\n✅ Annuncio 'basso' trovato:")
    print(f"   ID: {basso.id}")
    print(f"   Tipo: {basso.tipo}")
    print(f"   Utente: {basso.utente.username}")
    print(f"   Categoria: {basso.categoria}")
    print(f"   Attivo: {basso.attivo}")
except Annuncio.DoesNotExist:
    print("\n❌ Annuncio 'basso' non trovato o disattivato")
    print("   (Questo è normale se l'hai appena disattivato)")
    basso = None

# Trova gli annunci 'synth'
print("\n" + "=" * 80)
print("🎹 ANNUNCI 'SYNTH'")
print("=" * 80)

synth_annunci = Annuncio.objects.filter(titolo__icontains='synth', attivo=True)
print(f"\nAnnunci 'synth' attivi: {synth_annunci.count()}")

synth_offro = []
synth_cerco = []

for ann in synth_annunci:
    print(f"\n   {ann.utente.username} {ann.tipo}: '{ann.titolo}' (ID: {ann.id})")
    print(f"   Categoria: {ann.categoria}")

    if ann.tipo == 'offro':
        synth_offro.append(ann)
    else:
        synth_cerco.append(ann)

# TEST 1: Compatibilità tra synth
print("\n" + "=" * 80)
print("TEST 1: Compatibilità tra annunci 'synth'")
print("=" * 80)

if synth_offro and synth_cerco:
    for offro in synth_offro:
        for cerco in synth_cerco:
            if offro.utente != cerco.utente:
                compatibile, tipo_match = oggetti_compatibili_con_tipo(offro, cerco)

                print(f"\n   {offro.utente.username} offre '{offro.titolo}' → {cerco.utente.username} cerca '{cerco.titolo}'")
                print(f"   Compatibile: {compatibile}")
                print(f"   Tipo match: {tipo_match}")

                if compatibile:
                    print(f"   ✅ MATCH VALIDO!")
                else:
                    print(f"   ❌ NON compatibile")

# TEST 2: Compatibilità con 'basso'
if basso:
    print("\n" + "=" * 80)
    print("TEST 2: Compatibilità di 'basso' con altri annunci")
    print("=" * 80)

    # Trova annunci che potrebbero matchare con basso
    altri_annunci = Annuncio.objects.filter(attivo=True).exclude(id=basso.id)

    matches_basso = []

    for ann in altri_annunci:
        # Se basso è offro, cerca annunci cerco
        # Se basso è cerco, cerca annunci offro
        tipo_opposto = 'cerco' if basso.tipo == 'offro' else 'offro'

        if ann.tipo == tipo_opposto:
            compatibile, tipo_match = oggetti_compatibili_con_tipo(basso, ann)

            if compatibile:
                matches_basso.append({
                    'annuncio': ann,
                    'tipo_match': tipo_match
                })

    print(f"\n'basso' ({basso.tipo}) matcha con {len(matches_basso)} annunci:")
    for m in matches_basso:
        ann = m['annuncio']
        print(f"   - {ann.utente.username} {ann.tipo}: '{ann.titolo}' (match: {m['tipo_match']})")

# TEST 3: Catene con e senza basso
print("\n" + "=" * 80)
print("TEST 3: Catene prima e dopo disattivazione 'basso'")
print("=" * 80)

# Calcola catene
catene = trova_catene_scambio_ottimizzato()
print(f"\nCatene totali trovate: {len(catene)}")

# Analizza quali catene includono admin
admin = User.objects.get(username='admin')
catene_admin = [c for c in catene if any(u['user'].id == admin.id for u in c.get('utenti', []))]

print(f"Catene che includono admin: {len(catene_admin)}")

# Analizza qualità delle catene admin
catene_admin_buone = []
catene_admin_generiche = []

for c in catene_admin:
    punteggio, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)

    if ha_match_titoli:
        catene_admin_buone.append(c)
    else:
        catene_admin_generiche.append(c)

print(f"\n   Con match titoli (BUONE): {len(catene_admin_buone)}")
print(f"   Solo categoria (GENERICHE): {len(catene_admin_generiche)}")

# Mostra dettagli catene generiche
if catene_admin_generiche:
    print(f"\n   📋 Catene GENERICHE (bloccate dal filtro):")

    for i, c in enumerate(catene_admin_generiche[:3], 1):
        print(f"\n      Catena {i}:")
        for u in c.get('utenti', []):
            offerta = u.get('offerta')
            richiesta = u.get('richiede')

            if offerta and richiesta:
                print(f"         {u['nome']}: offre '{offerta.titolo}' → cerca '{richiesta.titolo}'")

                # Controlla se c'è 'basso'
                if 'basso' in offerta.titolo.lower() or 'basso' in richiesta.titolo.lower():
                    print(f"         🎯 CONTIENE 'BASSO'!")

# Mostra dettagli catene buone
if catene_admin_buone:
    print(f"\n   ✅ Catene BUONE (dovrebbero essere visibili):")

    for i, c in enumerate(catene_admin_buone[:3], 1):
        print(f"\n      Catena {i}:")
        for u in c.get('utenti', []):
            offerta = u.get('offerta')
            richiesta = u.get('richiede')

            if offerta and richiesta:
                print(f"         {u['nome']}: offre '{offerta.titolo}' → cerca '{richiesta.titolo}'")

                # Verifica match
                compatibile, tipo_match = oggetti_compatibili_con_tipo(offerta, richiesta)
                print(f"         Match: {tipo_match}")

# TEST 4: Verifica se basso compare nelle catene buone
if basso and catene_admin_buone:
    print(f"\n   🔍 Verifica se 'basso' compare nelle catene BUONE:")

    basso_nelle_buone = False
    for c in catene_admin_buone:
        for u in c.get('utenti', []):
            offerta = u.get('offerta')
            richiesta = u.get('richiede')

            if offerta and (offerta.id == basso.id or 'basso' in offerta.titolo.lower()):
                basso_nelle_buone = True
                print(f"      ❗ 'basso' trovato in catena buona!")
                break

            if richiesta and (richiesta.id == basso.id or 'basso' in richiesta.titolo.lower()):
                basso_nelle_buone = True
                print(f"      ❗ 'basso' trovato in catena buona!")
                break

    if not basso_nelle_buone:
        print(f"      ✅ 'basso' NON è nelle catene buone (corretto)")

print("\n" + "=" * 80)
print("🏁 DIAGNOSI FINALE")
print("=" * 80)

if basso:
    print("\n⚠️  'basso' è ATTIVO")
    print(f"   Catene admin totali: {len(catene_admin)}")
    print(f"   Catene admin buone: {len(catene_admin_buone)}")
    print(f"   Catene admin generiche (bloccate): {len(catene_admin_generiche)}")

    if len(catene_admin_generiche) > 0 and len(catene_admin_buone) == 0:
        print("\n   ❌ PROBLEMA CONFERMATO:")
        print("      'basso' crea catene GENERICHE che vengono filtrate,")
        print("      ma non dovrebbe bloccare le catene BUONE con 'synth'!")
        print("\n   💡 POSSIBILE CAUSA:")
        print("      - Trova_catene_scambio_ottimizzato() restituisce SOLO catene generiche")
        print("      - Le catene con 'synth' NON vengono trovate dall'algoritmo")
        print("      - Il problema è nell'ALGORITMO, non nel FILTRO!")
else:
    print("\n✅ 'basso' è DISATTIVATO")
    print(f"   Catene admin buone: {len(catene_admin_buone)}")

    if len(catene_admin_buone) > 0:
        print("\n   ✅ Le catene 'synth' sono tornate!")
        print("      Quando 'basso' era attivo, l'algoritmo non trovava le catene 'synth'")

print("\n" + "=" * 80)
