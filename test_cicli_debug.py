"""
Script di debug per diagnosticare il problema con i cicli mancanti online.
Da eseguire sulla Shell di Render.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import CicloScambio, Annuncio, UserProfile
from django.contrib.auth.models import User
from scambi.matching import converti_ciclo_db_a_view_format

print("=" * 70)
print("🔍 DIAGNOSI CICLI MANCANTI")
print("=" * 70)

# 1. Stato generale database
print("\n📊 STATO DATABASE:")
total_users = User.objects.count()
total_annunci = Annuncio.objects.count()
annunci_attivi = Annuncio.objects.filter(attivo=True).count()
annunci_inattivi = Annuncio.objects.filter(attivo=False).count()
total_cicli = CicloScambio.objects.count()
cicli_validi = CicloScambio.objects.filter(valido=True).count()

print(f"  Utenti: {total_users}")
print(f"  Annunci totali: {total_annunci}")
print(f"  Annunci attivi: {annunci_attivi}")
print(f"  Annunci inattivi: {annunci_inattivi}")
print(f"  Cicli totali: {total_cicli}")
print(f"  Cicli validi: {cicli_validi}")

# 2. Controlla annunci inattivi
if annunci_inattivi > 0:
    print(f"\n⚠️  ANNUNCI INATTIVI CHE POTREBBERO BLOCCARE CICLI:")
    for ann in Annuncio.objects.filter(attivo=False)[:10]:
        print(f"     - ID {ann.id}: {ann.titolo} (utente: {ann.utente.username})")

# 3. Test conversione cicli per ogni utente
print("\n👥 TEST CONVERSIONE CICLI PER UTENTE:")

# Pre-carica annunci una volta sola
annunci_ids = set()
for ciclo_db in CicloScambio.objects.filter(valido=True):
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

# Testa per ogni utente
for user in User.objects.all()[:10]:  # Primi 10 utenti
    print(f"\n  👤 {user.username} (ID: {user.id}):")

    # Trova cicli per questo utente
    cicli_validi_db = CicloScambio.objects.filter(valido=True)
    cicli_utente_db = [c for c in cicli_validi_db if user.id in c.users]

    print(f"     Cicli nel DB: {len(cicli_utente_db)}")

    # Prova a convertire ogni ciclo
    cicli_convertiti = 0
    cicli_scartati = 0

    for ciclo_db in cicli_utente_db:
        try:
            ciclo_convertito = converti_ciclo_db_a_view_format(ciclo_db, annunci_dict)
            if ciclo_convertito:
                cicli_convertiti += 1
            else:
                cicli_scartati += 1
                print(f"        ⚠️  Ciclo {ciclo_db.id} scartato (probabilmente annuncio inattivo)")
        except Exception as e:
            print(f"        ❌ Errore ciclo {ciclo_db.id}: {e}")
            cicli_scartati += 1

    print(f"     Cicli visualizzabili: {cicli_convertiti}")
    if cicli_scartati > 0:
        print(f"     ⚠️  Cicli scartati: {cicli_scartati}")

# 4. Controlla se ci sono annunci referenziati nei cicli ma mancanti nel DB
print("\n🔍 CONTROLLO ANNUNCI MANCANTI:")
annunci_mancanti = [aid for aid in annunci_ids if aid not in annunci_dict]
if annunci_mancanti:
    print(f"   ⚠️  {len(annunci_mancanti)} annunci referenziati nei cicli ma NON trovati nel DB!")
    print(f"   IDs mancanti: {annunci_mancanti[:10]}")
else:
    print(f"   ✅ Tutti gli annunci referenziati sono presenti nel DB")

print("\n" + "=" * 70)
print("🏁 DIAGNOSI COMPLETATA")
print("=" * 70)
