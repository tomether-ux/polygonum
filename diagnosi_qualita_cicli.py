"""
Script per diagnosticare il problema con il filtraggio qualità cicli.
Controlla perché i cicli vengono filtrati nella pagina /catene-scambio/
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import CicloScambio, Annuncio
from scambi.matching import converti_ciclo_db_a_view_format, calcola_qualita_ciclo

print("=" * 80)
print("🔍 DIAGNOSI FILTRO QUALITÀ CICLI")
print("=" * 80)

# 1. Stato generale
cicli_validi = CicloScambio.objects.filter(valido=True)
print(f"\n📊 Cicli validi nel DB: {cicli_validi.count()}")

# 2. Pre-carica annunci (come nel codice di produzione)
annunci_ids = set()
for ciclo_db in cicli_validi:
    dettagli = ciclo_db.dettagli
    if 'scambi' in dettagli:
        for scambio in dettagli['scambi']:
            oggetti = scambio.get('oggetti', [])
            for oggetto in oggetti:
                if 'offerto' in oggetto and 'id' in oggetto['offerto']:
                    annunci_ids.add(oggetto['offerto']['id'])
                if 'richiesto' in oggetto and 'id' in oggetto['richiesto']:
                    annunci_ids.add(oggetto['richiesto']['id'])

annunci_dict = {a.id: a for a in Annuncio.objects.filter(id__in=annunci_ids)}
print(f"📦 Pre-caricati {len(annunci_dict)} annunci")

# 3. Controlla annunci inattivi
annunci_inattivi = [a for a in annunci_dict.values() if not a.attivo]
print(f"\n⚠️  Annunci INATTIVI trovati: {len(annunci_inattivi)}")
if annunci_inattivi:
    for ann in annunci_inattivi[:5]:
        print(f"    - ID {ann.id}: '{ann.titolo}' (utente: {ann.utente.username})")

# 4. Converti cicli e controlla qualità
print(f"\n🔍 CONTROLLO QUALITÀ PER OGNI CICLO:\n")

cicli_convertiti = 0
cicli_scartati_inattivi = 0
cicli_scartati_qualita = 0
cicli_ok = 0

for ciclo_db in cicli_validi[:20]:  # Primi 20 cicli
    try:
        # Converti
        ciclo_convertito = converti_ciclo_db_a_view_format(ciclo_db, annunci_dict)

        if ciclo_convertito is None:
            cicli_scartati_inattivi += 1
            print(f"❌ Ciclo {ciclo_db.id}: SCARTATO (annuncio inattivo)")
            continue

        cicli_convertiti += 1

        # Calcola qualità
        punteggio, ha_match_titoli = calcola_qualita_ciclo(ciclo_convertito, return_tipo_match=True)

        if ha_match_titoli:
            cicli_ok += 1
            print(f"✅ Ciclo {ciclo_db.id}: OK - Punteggio {punteggio}, lunghezza {len(ciclo_convertito.get('utenti', []))}")
        else:
            cicli_scartati_qualita += 1
            print(f"⚠️  Ciclo {ciclo_db.id}: FILTRATO (solo match categoria/generico) - Punteggio {punteggio}")

            # Mostra dettagli per capire perché è stato scartato
            if ciclo_convertito.get('utenti'):
                print(f"    Utenti nel ciclo: {[u['nome'] for u in ciclo_convertito['utenti']]}")
                for i, utente in enumerate(ciclo_convertito['utenti']):
                    if utente.get('offerta') and utente.get('richiede'):
                        print(f"    - {utente['nome']}")
                        print(f"      Offre: '{utente['offerta'].titolo}'")
                        print(f"      Cerca: '{utente['richiede'].titolo}'")

    except Exception as e:
        print(f"❌ Ciclo {ciclo_db.id}: ERRORE durante conversione - {e}")
        cicli_scartati_inattivi += 1

# 5. Riepilogo
print("\n" + "=" * 80)
print("📊 RIEPILOGO:")
print("=" * 80)
print(f"Cicli validi nel DB: {cicli_validi.count()}")
print(f"Cicli convertiti con successo: {cicli_convertiti}")
print(f"Cicli scartati (annunci inattivi): {cicli_scartati_inattivi}")
print(f"Cicli scartati (solo match categoria): {cicli_scartati_qualita}")
print(f"✅ Cicli che passano il filtro: {cicli_ok}")
print("=" * 80)

if cicli_scartati_qualita > 0:
    print("\n⚠️  PROBLEMA IDENTIFICATO:")
    print("Molti cicli vengono filtrati perché hanno solo match per categoria/generici.")
    print("Questo è causato dal filtro in views.py (linee 356-360) che accetta solo")
    print("cicli con 'ha_match_titoli=True' (match specifici/parziali/sinonimi).")
