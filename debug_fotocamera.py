"""
Script per debuggare il problema del ciclo a 5 con fotocamera/macchina fotografica
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
django.setup()

from django.contrib.auth.models import User
from scambi.models import Annuncio
from scambi.matching import oggetti_compatibili_con_tipo, estrai_parole_chiave
from scambi.synonym_matcher import get_synonyms

# Lista degli utenti coinvolti
usernames = ['hhh', 'admin', 'fede', 'piero', 'marco']

print("=" * 80)
print("ANALISI ANNUNCI NEL CICLO A 5")
print("=" * 80)

# Raccogli tutti gli annunci attivi di questi utenti
annunci_per_utente = {}
for username in usernames:
    try:
        user = User.objects.get(username=username)
        annunci = Annuncio.objects.filter(utente=user, attivo=True)
        annunci_per_utente[username] = list(annunci)

        print(f"\n{'='*80}")
        print(f"UTENTE: {username}")
        print(f"{'='*80}")
        for ann in annunci:
            print(f"\nID: {ann.id}")
            print(f"Titolo: {ann.titolo}")
            print(f"Descrizione: {ann.descrizione}")
            print(f"Offro: {ann.offro}")
            print(f"Cerco: {ann.cerco}")

            # Estrai parole chiave
            parole_offro = estrai_parole_chiave(ann.offro)
            parole_cerco = estrai_parole_chiave(ann.cerco)

            print(f"Parole chiave OFFRO: {parole_offro}")
            print(f"Parole chiave CERCO: {parole_cerco}")

            # Mostra sinonimi per parole chiave importanti
            for parola in parole_offro:
                if len(parola) > 3:
                    sinonimi = get_synonyms(parola)
                    if len(sinonimi) > 1:
                        print(f"  Sinonimi di '{parola}': {sinonimi}")

            for parola in parole_cerco:
                if len(parola) > 3:
                    sinonimi = get_synonyms(parola)
                    if len(sinonimi) > 1:
                        print(f"  Sinonimi di '{parola}': {sinonimi}")

    except User.DoesNotExist:
        print(f"❌ Utente {username} non trovato")

# Ora verifica tutte le compatibilità possibili
print("\n" + "=" * 80)
print("MATRICE DI COMPATIBILITÀ")
print("=" * 80)

tutti_annunci = []
for username in usernames:
    if username in annunci_per_utente:
        tutti_annunci.extend(annunci_per_utente[username])

print(f"\nTotale annunci da verificare: {len(tutti_annunci)}")

# Crea matrice di compatibilità
compatibilita = []
for i, ann1 in enumerate(tutti_annunci):
    for j, ann2 in enumerate(tutti_annunci):
        if i != j and ann1.utente != ann2.utente:
            is_compatible, tipo_match = oggetti_compatibili_con_tipo(ann1, ann2)
            if is_compatible:
                compatibilita.append({
                    'da': f"{ann1.utente.username} (ID:{ann1.id})",
                    'offre': ann1.offro,
                    'a': f"{ann2.utente.username} (ID:{ann2.id})",
                    'cerca': ann2.cerco,
                    'tipo': tipo_match
                })

print(f"\nTrovate {len(compatibilita)} compatibilità:")
for comp in compatibilita:
    simbolo = "🔄"
    if comp['tipo'] == 'sinonimo':
        simbolo = "📚"
    elif comp['tipo'] == 'specifico':
        simbolo = "✅"
    elif comp['tipo'] == 'parziale':
        simbolo = "🔸"

    print(f"\n{simbolo} {comp['da']} può dare '{comp['offre']}' → {comp['a']} cerca '{comp['cerca']}'")
    print(f"   Tipo match: {comp['tipo']}")

# Cerca specificamente match con fotocamera/macchina fotografica
print("\n" + "=" * 80)
print("FOCUS: FOTOCAMERA / MACCHINA FOTOGRAFICA")
print("=" * 80)

for ann in tutti_annunci:
    testo_completo = f"{ann.titolo} {ann.descrizione} {ann.offro} {ann.cerco}".lower()
    if 'fotocamera' in testo_completo or 'macchina fotografica' in testo_completo:
        print(f"\n🔍 Annuncio ID:{ann.id} di {ann.utente.username}")
        print(f"   Titolo: {ann.titolo}")
        print(f"   Offro: {ann.offro}")
        print(f"   Cerco: {ann.cerco}")

        parole_offro = estrai_parole_chiave(ann.offro)
        parole_cerco = estrai_parole_chiave(ann.cerco)

        print(f"   Parole OFFRO: {parole_offro}")
        print(f"   Parole CERCO: {parole_cerco}")

        # Verifica sinonimi
        print(f"\n   Sinonimi per parole in OFFRO:")
        for parola in parole_offro:
            if len(parola) > 2:
                sinonimi = get_synonyms(parola)
                print(f"     '{parola}' → {sinonimi}")

        print(f"\n   Sinonimi per parole in CERCO:")
        for parola in parole_cerco:
            if len(parola) > 2:
                sinonimi = get_synonyms(parola)
                print(f"     '{parola}' → {sinonimi}")

print("\n" + "=" * 80)
print("FINE ANALISI")
print("=" * 80)
