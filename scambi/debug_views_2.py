"""
Debug view 2: Verifica cosa succede nella view catene_scambio quando 'basso' è attivo
"""

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from .models import Annuncio, CicloScambio
from .matching import (
    get_cicli_precalcolati,
    trova_scambi_diretti_ottimizzato,
    trova_catene_scambio_ottimizzato,
    filtra_catene_per_utente_ottimizzato,
    calcola_qualita_ciclo
)
from django.contrib.auth.models import User


@require_http_methods(["GET"])
def debug_view_catene(request):
    """
    Simula il flusso della view catene_scambio per vedere dove si blocca
    """
    output = []
    output.append("=" * 80)
    output.append("🔍 DEBUG VIEW CATENE-SCAMBIO")
    output.append("=" * 80)

    # Trova 'basso'
    try:
        basso = Annuncio.objects.get(titolo__iexact='basso', attivo=True)
        output.append(f"\n⚠️  'basso' è ATTIVO (ID: {basso.id}, utente: {basso.utente.username})")
    except Annuncio.DoesNotExist:
        output.append(f"\n✅ 'basso' non è attivo")
        basso = None

    # Simula il flusso della view per un utente specifico
    username = request.GET.get('user', 'admin')

    try:
        user = User.objects.get(username=username)
        output.append(f"\n👤 Test per utente: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        output.append(f"\n❌ Utente '{username}' non trovato")
        return HttpResponse("\n".join(output), content_type="text/plain; charset=utf-8")

    # STEP 1: Carica cicli dal DB
    output.append("\n" + "=" * 80)
    output.append("STEP 1: get_cicli_precalcolati()")
    output.append("=" * 80)

    try:
        risultato = get_cicli_precalcolati()
        scambi_diretti = risultato['scambi_diretti']
        catene = risultato['catene']

        output.append(f"\n✅ Caricati dal DB:")
        output.append(f"   Scambi diretti: {len(scambi_diretti)}")
        output.append(f"   Catene lunghe: {len(catene)}")
        output.append(f"   Totale: {risultato['totale']}")
    except Exception as e:
        output.append(f"\n❌ ERRORE: {e}")
        import traceback
        output.append(traceback.format_exc())
        return HttpResponse("\n".join(output), content_type="text/plain; charset=utf-8")

    # STEP 2: Unifica catene (come fa la view)
    output.append("\n" + "=" * 80)
    output.append("STEP 2: Unifica scambi diretti + catene")
    output.append("=" * 80)

    catene_uniche = scambi_diretti + catene
    output.append(f"\nCatene uniche totali: {len(catene_uniche)}")

    # STEP 3: Filtra per qualità (come fa la view)
    output.append("\n" + "=" * 80)
    output.append("STEP 3: Filtra per qualità (ha_match_titoli)")
    output.append("=" * 80)

    catene_specifiche = []
    for c in catene_uniche:
        try:
            _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
            if ha_match_titoli:
                catene_specifiche.append(c)
        except Exception as e:
            output.append(f"   ⚠️  Errore su ciclo: {e}")

    output.append(f"\nCatene dopo filtro qualità: {len(catene_specifiche)}")
    output.append(f"   Catene eliminate (solo categoria): {len(catene_uniche) - len(catene_specifiche)}")

    if len(catene_specifiche) == 0:
        output.append(f"\n❌ PROBLEMA: Tutte le catene sono state filtrate!")
        output.append(f"   Nessuna catena ha match titoli")

        # Mostra esempio catena bloccata
        if len(catene_uniche) > 0:
            output.append(f"\n   Esempio catena BLOCCATA:")
            c = catene_uniche[0]
            for u in c.get('utenti', []):
                offerta = u.get('offerta')
                richiesta = u.get('richiede')
                if offerta and richiesta:
                    output.append(f"      {u['user'].username}: '{offerta.titolo}' → '{richiesta.titolo}'")

    # STEP 4: Filtra per utente
    output.append("\n" + "=" * 80)
    output.append(f"STEP 4: Filtra per utente {user.username}")
    output.append("=" * 80)

    try:
        scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
            scambi_diretti, catene_specifiche, user
        )

        output.append(f"\n✅ Dopo filtro utente:")
        output.append(f"   Scambi diretti: {len(scambi_diretti_utente)}")
        output.append(f"   Catene lunghe: {len(catene_lunghe_utente)}")

        totale_visualizzabile = len(scambi_diretti_utente) + len(catene_lunghe_utente)
        output.append(f"\n📊 TOTALE VISUALIZZABILE: {totale_visualizzabile}")

        if totale_visualizzabile == 0:
            output.append(f"\n❌ PROBLEMA: Nessuna catena dopo il filtro utente!")

            # Verifica se l'utente è nei cicli del DB
            cicli_db = CicloScambio.objects.filter(valido=True, users__contains=user.id)
            output.append(f"\n   Cicli nel DB per {user.username}: {cicli_db.count()}")

    except Exception as e:
        output.append(f"\n❌ ERRORE nel filtro utente: {e}")
        import traceback
        output.append(traceback.format_exc())

    # DIAGNOSI FINALE
    output.append("\n" + "=" * 80)
    output.append("🎯 DIAGNOSI")
    output.append("=" * 80)

    if len(catene_specifiche) == 0 and len(catene_uniche) > 0:
        output.append(f"\n❌ PROBLEMA: Filtro qualità blocca TUTTE le catene")
        output.append(f"   Cicli nel DB: {len(catene_uniche)}")
        output.append(f"   Cicli con match titoli: 0")
        output.append(f"\n   CAUSA POSSIBILE:")
        output.append(f"   - I cicli nel DB sono obsoleti")
        output.append(f"   - Sono stati calcolati con annunci diversi da quelli attuali")
        output.append(f"   - Oppure il filtro qualità ha un bug")
        output.append(f"\n   SOLUZIONE:")
        output.append(f"   Ricalcola i cicli per aggiornare il database")

    elif totale_visualizzabile == 0 and len(catene_specifiche) > 0:
        output.append(f"\n❌ PROBLEMA: Filtro utente blocca tutte le catene")
        output.append(f"   Catene specifiche: {len(catene_specifiche)}")
        output.append(f"   Catene per {user.username}: 0")

    elif totale_visualizzabile > 0:
        output.append(f"\n✅ OK! {user.username} dovrebbe vedere {totale_visualizzabile} catene")

    output.append("\n" + "=" * 80)

    return HttpResponse("\n".join(output), content_type="text/plain; charset=utf-8")
