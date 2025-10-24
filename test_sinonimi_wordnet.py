import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from scambi.synonym_matcher import get_synonyms, check_synonym_match

print("=== TEST SINONIMI WORDNET ===\n")

# Test 1: Parole con sinonimi noti
test_words = ['libro', 'volume', 'automobile', 'auto', 'bicicletta', 'bici', 'fotocamera', 'macchina fotografica']

for word in test_words:
    sinonimi = get_synonyms(word)
    print(f"'{word}' -> Sinonimi: {sinonimi}")

# Test 2: Check match specifico
print("\n=== TEST CHECK MATCH ===")
test_pairs = [
    ({'libro'}, {'volume'}),
    ({'volume'}, {'libro'}),
    ({'automobile'}, {'auto'}),
    ({'bicicletta'}, {'bici'}),
    ({'fotocamera'}, {'macchina fotografica'}),
]

for parole_offerto, parole_cercato in test_pairs:
    compatible, tipo = check_synonym_match(parole_offerto, parole_cercato)
    print(f"{parole_offerto} vs {parole_cercato}: compatible={compatible}, tipo={tipo}")
