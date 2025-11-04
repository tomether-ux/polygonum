#!/usr/bin/env python
"""
Script per diagnosticare i cicli mancanti su Render.
Uso: python check_cicli_online.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import CicloScambio, Annuncio, UserProfile
from django.contrib.auth.models import User

print("=" * 80)
print("DIAGNOSI CICLI MANCANTI - RENDER")
print("=" * 80)

# 1. Stato generale
print("\n1. STATO DATABASE:")
total_users = User.objects.count()
cicli_validi = CicloScambio.objects.filter(valido=True)
print(f"   - Utenti totali: {total_users}")
print(f"   - Cicli validi: {cicli_validi.count()}")

# 2. Estrai tutti gli ID degli annunci referenziati nei cicli
print("\n2. ANNUNCI REFERENZIATI NEI CICLI:")
annunci_ids_nei_cicli = set()
for ciclo in cicli_validi:
    dettagli = ciclo.dettagli
    if 'scambi' in dettagli:
        for scambio in dettagli['scambi']:
            oggetti = scambio.get('oggetti', [])
            for oggetto in oggetti:
                if 'offerto' in oggetto and 'id' in oggetto['offerto']:
                    annunci_ids_nei_cicli.add(oggetto['offerto']['id'])
                if 'richiesto' in oggetto and 'id' in oggetto['richiesto']:
                    annunci_ids_nei_cicli.add(oggetto['richiesto']['id'])

print(f"   - Annunci totali referenziati: {len(annunci_ids_nei_cicli)}")

# 3. Controlla quali annunci esistono e quali sono attivi
annunci_esistenti = Annuncio.objects.filter(id__in=annunci_ids_nei_cicli)
annunci_dict = {a.id: a for a in annunci_esistenti}

annunci_mancanti = annunci_ids_nei_cicli - set(annunci_dict.keys())
annunci_inattivi = [a for a in annunci_dict.values() if not a.attivo]

print(f"   - Annunci trovati nel DB: {len(annunci_dict)}")
print(f"   - Annunci MANCANTI dal DB: {len(annunci_mancanti)}")
print(f"   - Annunci INATTIVI: {len(annunci_inattivi)}")

if annunci_mancanti:
    print(f"\n   ⚠️  ANNUNCI MANCANTI (referenziati ma non esistono):")
    for aid in list(annunci_mancanti)[:10]:
        print(f"      - ID {aid}")

if annunci_inattivi:
    print(f"\n   ⚠️  ANNUNCI INATTIVI (referenziati nei cicli ma disattivati):")
    for ann in annunci_inattivi[:10]:
        print(f"      - ID {ann.id}: '{ann.titolo}' (utente: {ann.utente.username})")

# 4. Per ogni utente, controlla quanti cicli ha nel DB
print("\n3. CICLI PER UTENTE:")
for user in User.objects.all()[:15]:  # Primi 15 utenti
    cicli_utente = [c for c in cicli_validi if user.id in c.users]
    if cicli_utente:
        profilo = UserProfile.objects.filter(user=user).first()
        premium_status = "PREMIUM" if profilo and profilo.is_premium else "FREE"

        # Conta annunci dell'utente
        annunci_offro_attivi = Annuncio.objects.filter(
            utente=user, tipo='offro', attivo=True
        ).count()
        annunci_cerco_attivi = Annuncio.objects.filter(
            utente=user, tipo='cerco', attivo=True
        ).count()
        annunci_offro_inattivi = Annuncio.objects.filter(
            utente=user, tipo='offro', attivo=False
        ).count()
        annunci_cerco_inattivi = Annuncio.objects.filter(
            utente=user, tipo='cerco', attivo=False
        ).count()

        print(f"\n   👤 {user.username} ({premium_status}):")
        print(f"      - Cicli nel DB: {len(cicli_utente)}")
        print(f"      - Annunci offro: {annunci_offro_attivi} attivi, {annunci_offro_inattivi} inattivi")
        print(f"      - Annunci cerco: {annunci_cerco_attivi} attivi, {annunci_cerco_inattivi} inattivi")

        # Se ci sono annunci inattivi, controlla se sono nei cicli
        if annunci_offro_inattivi > 0 or annunci_cerco_inattivi > 0:
            annunci_inattivi_utente = Annuncio.objects.filter(
                utente=user, attivo=False
            )
            for ann_inattivo in annunci_inattivi_utente:
                if ann_inattivo.id in annunci_ids_nei_cicli:
                    print(f"         ⚠️  Annuncio INATTIVO ma nei cicli: ID {ann_inattivo.id} '{ann_inattivo.titolo}'")

# 5. Controlla se ci sono cicli con troppi annunci inattivi
print("\n4. CICLI CON ANNUNCI INATTIVI:")
cicli_con_problemi = 0
for ciclo in cicli_validi[:20]:  # Primi 20 cicli
    annunci_ciclo = set()
    dettagli = ciclo.dettagli
    if 'scambi' in dettagli:
        for scambio in dettagli['scambi']:
            oggetti = scambio.get('oggetti', [])
            for oggetto in oggetti:
                if 'offerto' in oggetto and 'id' in oggetto['offerto']:
                    annunci_ciclo.add(oggetto['offerto']['id'])
                if 'richiesto' in oggetto and 'id' in oggetto['richiesto']:
                    annunci_ciclo.add(oggetto['richiesto']['id'])

    # Controlla quanti sono inattivi
    annunci_inattivi_ciclo = [aid for aid in annunci_ciclo if aid in annunci_dict and not annunci_dict[aid].attivo]

    if annunci_inattivi_ciclo:
        cicli_con_problemi += 1
        print(f"\n   Ciclo ID {ciclo.id}:")
        print(f"   - Utenti: {ciclo.users}")
        print(f"   - Annunci totali: {len(annunci_ciclo)}")
        print(f"   - Annunci INATTIVI: {len(annunci_inattivi_ciclo)}")
        for aid in annunci_inattivi_ciclo:
            ann = annunci_dict[aid]
            print(f"      ⚠️  ID {aid}: '{ann.titolo}' (utente: {ann.utente.username})")

print(f"\n   Totale cicli con annunci inattivi: {cicli_con_problemi}/{min(20, cicli_validi.count())}")

print("\n" + "=" * 80)
print("DIAGNOSI COMPLETATA")
print("=" * 80)

# 6. Suggerimenti
if annunci_inattivi:
    print("\n⚠️  PROBLEMA TROVATO:")
    print(f"Ci sono {len(annunci_inattivi)} annunci INATTIVI che sono referenziati nei cicli.")
    print("Questi annunci vengono filtrati dalla visualizzazione, causando cicli mancanti.")
    print("\nSOLUZIONI:")
    print("1. Riattivare gli annunci disattivati")
    print("2. Invalidare i cicli che contengono annunci inattivi")
    print("3. Far ricalcolare i cicli dal CycleCalculator")

if annunci_mancanti:
    print("\n⚠️  PROBLEMA CRITICO:")
    print(f"Ci sono {len(annunci_mancanti)} annunci che sono referenziati nei cicli ma NON esistono nel database!")
    print("Questi cicli devono essere invalidati o ricalcolati.")
