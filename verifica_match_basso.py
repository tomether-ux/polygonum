#!/usr/bin/env python
"""
Verifica esattamente che tipo di match ha 'basso' con altri annunci
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio
from scambi.matching import oggetti_compatibili_con_tipo

print("=" * 80)
print("🔍 VERIFICA MATCH 'BASSO'")
print("=" * 80)

# Trova 'basso'
try:
    basso = Annuncio.objects.get(titolo__iexact='basso')
    print(f"\n✅ Annuncio 'basso' trovato:")
    print(f"   ID: {basso.id}")
    print(f"   Tipo: {basso.tipo}")
    print(f"   Utente: {basso.utente.username}")
    print(f"   Categoria: {basso.categoria}")
    print(f"   Attivo: {basso.attivo}")
except Annuncio.DoesNotExist:
    print("\n❌ Annuncio 'basso' non trovato")
    exit(0)

# Trova tutti gli altri annunci attivi
altri_annunci = Annuncio.objects.filter(attivo=True).exclude(id=basso.id)

print(f"\n📊 Verifica compatibilità 'basso' con {altri_annunci.count()} annunci attivi:")
print(f"   (controllando se avrebbe fatto parte del grafo CycleFinder)")

# Determina il tipo opposto
tipo_opposto = 'cerco' if basso.tipo == 'offro' else 'offro'

annunci_compatibili = altri_annunci.filter(tipo=tipo_opposto)

match_specifico = []
match_parziale = []
match_sinonimo = []
match_categoria = []
match_generico = []

for ann in annunci_compatibili:
    if basso.tipo == 'offro':
        compatibile, tipo_match = oggetti_compatibili_con_tipo(basso, ann)
    else:
        compatibile, tipo_match = oggetti_compatibili_con_tipo(ann, basso)

    if compatibile:
        entry = f"{ann.utente.username} {ann.tipo}: '{ann.titolo}'"

        if tipo_match == 'specifico':
            match_specifico.append(entry)
        elif tipo_match == 'parziale':
            match_parziale.append(entry)
        elif tipo_match == 'sinonimo':
            match_sinonimo.append(entry)
        elif tipo_match == 'categoria':
            match_categoria.append(entry)
        elif tipo_match == 'generico':
            match_generico.append(entry)

print("\n" + "=" * 80)
print("📊 RISULTATI")
print("=" * 80)

if match_specifico:
    print(f"\n✅ Match SPECIFICO ({len(match_specifico)}):")
    for m in match_specifico:
        print(f"   - {m}")

if match_parziale:
    print(f"\n✅ Match PARZIALE ({len(match_parziale)}):")
    for m in match_parziale:
        print(f"   - {m}")

if match_sinonimo:
    print(f"\n✅ Match SINONIMO ({len(match_sinonimo)}):")
    for m in match_sinonimo:
        print(f"   - {m}")

if match_categoria:
    print(f"\n⚠️  Match CATEGORIA ({len(match_categoria)}):")
    for m in match_categoria:
        print(f"   - {m}")

if match_generico:
    print(f"\n⚠️  Match GENERICO ({len(match_generico)}):")
    for m in match_generico:
        print(f"   - {m}")

print("\n" + "=" * 80)
print("🎯 CONCLUSIONE")
print("=" * 80)

# Conta match che sarebbero accettati dal CycleFinder
match_accettati = len(match_specifico) + len(match_parziale) + len(match_sinonimo)
match_rifiutati = len(match_categoria) + len(match_generico)

print(f"\n📊 Match che CycleFinder ACCETTA (specifico/parziale/sinonimo): {match_accettati}")
print(f"📊 Match che CycleFinder RIFIUTA (categoria/generico): {match_rifiutati}")

if match_accettati > 0:
    print(f"\n✅ 'basso' SAREBBE NEL GRAFO di CycleFinder!")
    print(f"   Ha {match_accettati} collegamenti validi.")
    print(f"\n   Questo significa che:")
    print(f"   - Il CycleFinder costruisce cicli che includono 'basso'")
    print(f"   - Questi cicli vengono salvati nel DB")
    print(f"   - Ma la view li filtra perché non tutti gli scambi hanno match titolo")
else:
    print(f"\n❌ 'basso' NON SAREBBE NEL GRAFO di CycleFinder!")
    print(f"   Ha solo match categoria/generico.")
    print(f"\n   Questo significa che:")
    print(f"   - Il CycleFinder NON costruisce cicli con 'basso'")
    print(f"   - 'basso' è completamente ignorato dall'algoritmo")
    print(f"   - Il problema deve essere ALTROVE (non nel CycleFinder)")

print("\n" + "=" * 80)
