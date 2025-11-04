#!/usr/bin/env python
"""
Diagnosi completa: Perché 'basso' blocca le catene anche con il codice originale?
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio, CicloScambio
from scambi.matching import oggetti_compatibili_con_tipo

print("=" * 80)
print("🔍 DIAGNOSI COMPLETA: Perché 'basso' blocca tutto?")
print("=" * 80)

# 1. Trova 'basso'
try:
    basso = Annuncio.objects.get(titolo__iexact='basso', attivo=True)
    print(f"\n✅ 'basso' attivo trovato:")
    print(f"   ID: {basso.id}")
    print(f"   Utente: {basso.utente.username}")
    print(f"   Tipo: {basso.tipo}")
    print(f"   Categoria: {basso.categoria}")
except Annuncio.DoesNotExist:
    print("\n❌ 'basso' non è attivo")
    exit(0)

# 2. Verifica che tipo di match ha 'basso' con TUTTI gli altri annunci
print("\n" + "=" * 80)
print("ANALISI MATCH DI 'BASSO'")
print("=" * 80)

tipo_opposto = 'cerco' if basso.tipo == 'offro' else 'offro'
altri_annunci = Annuncio.objects.filter(attivo=True, tipo=tipo_opposto).exclude(id=basso.id)

print(f"\nAnalizzo {altri_annunci.count()} annunci {tipo_opposto} attivi...")

match_specifico = []
match_parziale = []
match_sinonimo = []
match_categoria = []
match_generico = []

for ann in altri_annunci:
    if basso.tipo == 'offro':
        compatibile, tipo_match = oggetti_compatibili_con_tipo(basso, ann)
    else:
        compatibile, tipo_match = oggetti_compatibili_con_tipo(ann, basso)

    if compatibile:
        entry = {
            'annuncio': ann,
            'tipo_match': tipo_match
        }

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

# Mostra risultati
print(f"\n📊 RISULTATI:")
print(f"   Match SPECIFICO (titolo esatto): {len(match_specifico)}")
print(f"   Match PARZIALE (parole comuni): {len(match_parziale)}")
print(f"   Match SINONIMO (parole simili): {len(match_sinonimo)}")
print(f"   Match CATEGORIA (stessa cat.): {len(match_categoria)}")
print(f"   Match GENERICO: {len(match_generico)}")

# Match accettati dal CycleFinder (solo specifico/parziale/sinonimo)
match_titolo = len(match_specifico) + len(match_parziale) + len(match_sinonimo)
print(f"\n🎯 Match che il CycleFinder ACCETTA: {match_titolo}")
print(f"⚠️  Match che il CycleFinder RIFIUTA: {len(match_categoria) + len(match_generico)}")

if match_titolo > 0:
    print(f"\n❗ PROBLEMA IDENTIFICATO!")
    print(f"   'basso' HA {match_titolo} match titolo validi!")
    print(f"   Quindi 'basso' ENTRA nel grafo del CycleFinder!")
    print(f"\n   Match con:")

    for m in match_specifico[:3]:
        print(f"      ✅ SPECIFICO: {m['annuncio'].utente.username} - '{m['annuncio'].titolo}'")

    for m in match_parziale[:3]:
        print(f"      ✅ PARZIALE: {m['annuncio'].utente.username} - '{m['annuncio'].titolo}'")

    for m in match_sinonimo[:3]:
        print(f"      ✅ SINONIMO: {m['annuncio'].utente.username} - '{m['annuncio'].titolo}'")

else:
    print(f"\n✅ 'basso' ha SOLO match categoria/generico")
    print(f"   Il CycleFinder lo esclude dal grafo (corretto)")

# 3. Verifica cicli nel DB
print("\n" + "=" * 80)
print("CICLI NEL DATABASE")
print("=" * 80)

cicli_validi = CicloScambio.objects.filter(valido=True)
print(f"\nCicli validi nel DB: {cicli_validi.count()}")

if cicli_validi.count() > 0:
    # Conta cicli che includono l'utente di 'basso'
    cicli_con_basso = [c for c in cicli_validi if basso.utente.id in c.users]

    print(f"Cicli che includono {basso.utente.username}: {len(cicli_con_basso)}")

    if len(cicli_con_basso) > 0:
        print(f"\n   Esempio ciclo con {basso.utente.username}:")
        ciclo = cicli_con_basso[0]
        print(f"      ID: {ciclo.id}")
        print(f"      Utenti: {ciclo.users}")
        print(f"      Lunghezza: {ciclo.lunghezza}")

# 4. Verifica annunci 'synth'
print("\n" + "=" * 80)
print("ANNUNCI 'SYNTH'")
print("=" * 80)

synth_annunci = Annuncio.objects.filter(titolo__icontains='synth', attivo=True)
print(f"\nAnnunci 'synth' attivi: {synth_annunci.count()}")

for ann in synth_annunci:
    print(f"   - {ann.utente.username} {ann.tipo}: '{ann.titolo}'")

# Verifica se ci sono cicli con synth
if cicli_validi.count() > 0:
    utenti_synth = [ann.utente.id for ann in synth_annunci]
    cicli_con_synth = [c for c in cicli_validi if any(uid in c.users for uid in utenti_synth)]

    print(f"\nCicli che includono utenti con 'synth': {len(cicli_con_synth)}")

    if len(cicli_con_synth) == 0:
        print(f"   ❌ PROBLEMA: Nessun ciclo include utenti con 'synth'!")

print("\n" + "=" * 80)
print("🎯 DIAGNOSI FINALE")
print("=" * 80)

if match_titolo > 0:
    print(f"\n❌ PROBLEMA: 'basso' HA match titolo!")
    print(f"   Il titolo 'basso' matcha con altri annunci per:")
    if match_specifico:
        print(f"      - {len(match_specifico)} match SPECIFICI")
    if match_parziale:
        print(f"      - {len(match_parziale)} match PARZIALI")
    if match_sinonimo:
        print(f"      - {len(match_sinonimo)} match SINONIMI")

    print(f"\n   CAUSA:")
    print(f"   'basso' viene incluso nel grafo → crea cicli → occupa gli utenti")
    print(f"   → i cicli con 'synth' non vengono trovati (deduplicazione)")

    print(f"\n   SOLUZIONE:")
    print(f"   1. Rinomina 'basso' in qualcosa di più specifico che non matcha")
    print(f"   2. Oppure disattivalo")

else:
    print(f"\n✅ 'basso' ha SOLO match categoria")
    print(f"   Il problema deve essere ALTROVE")

    if cicli_validi.count() == 0:
        print(f"\n   ⚠️  Il DB è VUOTO!")
        print(f"   Ricalcola i cicli per popolare il database")

print("\n" + "=" * 80)
