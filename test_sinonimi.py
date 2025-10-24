import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.models import Annuncio, CicloScambio
from scambi.matching import oggetti_compatibili_con_tipo, converti_ciclo_db_a_view_format

# Test 1: Verifica se ci sono annunci con fotocamera
print("=== TEST 1: Annunci nel database ===")
fotocamera_annunci = Annuncio.objects.filter(titolo__icontains='fotocamera', attivo=True)
macchina_annunci = Annuncio.objects.filter(titolo__icontains='macchina fotografica', attivo=True)

print(f"Annunci con 'fotocamera': {fotocamera_annunci.count()}")
for ann in fotocamera_annunci:
    print(f"  - {ann.id}: {ann.titolo} ({ann.tipo})")

print(f"\nAnnunci con 'macchina fotografica': {macchina_annunci.count()}")
for ann in macchina_annunci:
    print(f"  - {ann.id}: {ann.titolo} ({ann.tipo})")

# Test 2: Verifica match tra fotocamera e macchina fotografica
if fotocamera_annunci.exists() and macchina_annunci.exists():
    print("\n=== TEST 2: Compatibilità tra annunci ===")
    foto = fotocamera_annunci.first()
    macchina = macchina_annunci.first()
    
    compatible, tipo_match = oggetti_compatibili_con_tipo(macchina, foto)
    print(f"'{macchina.titolo}' vs '{foto.titolo}'")
    print(f"Compatibile: {compatible}")
    print(f"Tipo match: {tipo_match}")

# Test 3: Verifica cicli nel database
print("\n=== TEST 3: Cicli nel database ===")
cicli = CicloScambio.objects.filter(valido=True)
print(f"Totale cicli validi: {cicli.count()}")

# Test 4: Verifica se qualche ciclo ha usa_sinonimi
print("\n=== TEST 4: Cicli con flag usa_sinonimi ===")
count_con_sinonimi = 0
for ciclo in cicli[:10]:  # Primi 10 cicli
    ciclo_converted = converti_ciclo_db_a_view_format(ciclo)
    if ciclo_converted and ciclo_converted.get('usa_sinonimi'):
        count_con_sinonimi += 1
        print(f"Ciclo {ciclo.id}: usa_sinonimi = True")
        print(f"  Utenti: {ciclo.users}")

print(f"\nTotale cicli con sinonimi (su primi 10): {count_con_sinonimi}")
