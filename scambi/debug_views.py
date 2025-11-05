"""
View di debug temporanee - DA RIMUOVERE DOPO IL DEBUG
"""

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from .models import Annuncio, CicloScambio
from .matching import oggetti_compatibili_con_tipo


@require_http_methods(["GET"])
def debug_basso(request):
    """
    Debug: Perché 'basso' blocca le catene?
    """
    output = []
    output.append("=" * 80)
    output.append("🔍 DIAGNOSI: Perché 'basso' blocca le catene?")
    output.append("=" * 80)

    # 1. Trova 'basso'
    try:
        basso = Annuncio.objects.get(titolo__iexact='basso', attivo=True)
        output.append(f"\n✅ 'basso' attivo trovato:")
        output.append(f"   ID: {basso.id}")
        output.append(f"   Utente: {basso.utente.username}")
        output.append(f"   Tipo: {basso.tipo}")
        output.append(f"   Categoria: {basso.categoria}")
    except Annuncio.DoesNotExist:
        output.append("\n❌ 'basso' non è attivo")
        return HttpResponse("\n".join(output), content_type="text/plain")

    # 2. Analizza match
    output.append("\n" + "=" * 80)
    output.append("ANALISI MATCH DI 'BASSO'")
    output.append("=" * 80)

    tipo_opposto = 'cerco' if basso.tipo == 'offro' else 'offro'
    altri_annunci = Annuncio.objects.filter(attivo=True, tipo=tipo_opposto).exclude(id=basso.id)

    output.append(f"\nAnalizzo {altri_annunci.count()} annunci {tipo_opposto} attivi...")

    match_specifico = []
    match_parziale = []
    match_sinonimo = []
    match_categoria = []

    for ann in altri_annunci:
        if basso.tipo == 'offro':
            compatibile, tipo_match = oggetti_compatibili_con_tipo(basso, ann)
        else:
            compatibile, tipo_match = oggetti_compatibili_con_tipo(ann, basso)

        if compatibile:
            entry = f"{ann.utente.username}: '{ann.titolo}'"

            if tipo_match == 'specifico':
                match_specifico.append(entry)
            elif tipo_match == 'parziale':
                match_parziale.append(entry)
            elif tipo_match == 'sinonimo':
                match_sinonimo.append(entry)
            elif tipo_match == 'categoria':
                match_categoria.append(entry)

    output.append(f"\n📊 RISULTATI:")
    output.append(f"   Match SPECIFICO: {len(match_specifico)}")
    output.append(f"   Match PARZIALE: {len(match_parziale)}")
    output.append(f"   Match SINONIMO: {len(match_sinonimo)}")
    output.append(f"   Match CATEGORIA: {len(match_categoria)}")

    match_titolo = len(match_specifico) + len(match_parziale) + len(match_sinonimo)
    output.append(f"\n🎯 Match che CycleFinder ACCETTA: {match_titolo}")

    if match_titolo > 0:
        output.append(f"\n❗ PROBLEMA IDENTIFICATO!")
        output.append(f"   'basso' HA {match_titolo} match titolo!")
        output.append(f"   Quindi ENTRA nel grafo!")
        output.append(f"\n   Dettagli:")

        if match_specifico:
            output.append(f"\n   SPECIFICI ({len(match_specifico)}):")
            for m in match_specifico[:5]:
                output.append(f"      - {m}")

        if match_parziale:
            output.append(f"\n   PARZIALI ({len(match_parziale)}):")
            for m in match_parziale[:5]:
                output.append(f"      - {m}")

        if match_sinonimo:
            output.append(f"\n   SINONIMI ({len(match_sinonimo)}):")
            for m in match_sinonimo[:5]:
                output.append(f"      - {m}")

    else:
        output.append(f"\n✅ 'basso' ha SOLO match categoria")
        output.append(f"   CycleFinder lo esclude (corretto)")

    # 3. Cicli DB
    output.append("\n" + "=" * 80)
    output.append("CICLI NEL DATABASE")
    output.append("=" * 80)

    cicli_validi = CicloScambio.objects.filter(valido=True)
    output.append(f"\nCicli validi: {cicli_validi.count()}")

    if cicli_validi.count() > 0:
        cicli_con_basso = [c for c in cicli_validi if basso.utente.id in c.users]
        output.append(f"Cicli con {basso.utente.username}: {len(cicli_con_basso)}")

    # 4. Diagnosi finale
    output.append("\n" + "=" * 80)
    output.append("🎯 DIAGNOSI FINALE")
    output.append("=" * 80)

    if match_titolo > 0:
        output.append(f"\n❌ 'basso' HA match titolo → ENTRA nel grafo")
        output.append(f"\n   SOLUZIONE:")
        output.append(f"   1. Rinomina 'basso' con titolo più specifico")
        output.append(f"   2. Oppure disattivalo")
    else:
        output.append(f"\n✅ 'basso' ha solo match categoria")
        if cicli_validi.count() == 0:
            output.append(f"   ⚠️  DB vuoto - ricalcola i cicli")

    output.append("\n" + "=" * 80)

    return HttpResponse("\n".join(output), content_type="text/plain; charset=utf-8")


@require_http_methods(["GET"])
def debug_view_catene(request):
    """
    Simula il flusso della view catene_scambio per vedere dove si blocca
    """
    from .matching import (
        get_cicli_precalcolati,
        filtra_catene_per_utente_ottimizzato,
        calcola_qualita_ciclo
    )
    from django.contrib.auth.models import User

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

    # Utente da testare
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
        return HttpResponse("\n".join(output), content_type="text/plain; charset=utf-8")

    # STEP 2: Unifica catene
    output.append("\n" + "=" * 80)
    output.append("STEP 2: Unifica scambi diretti + catene")
    output.append("=" * 80)

    catene_uniche = scambi_diretti + catene
    output.append(f"\nCatene uniche totali: {len(catene_uniche)}")

    # STEP 3: Filtra per qualità (SEPARATAMENTE per scambi diretti e catene)
    output.append("\n" + "=" * 80)
    output.append("STEP 3: Filtra per qualità (ha_match_titoli)")
    output.append("=" * 80)

    # Filtra scambi diretti
    scambi_diretti_specifici = []
    catene_elim_sd = []
    for c in scambi_diretti:
        try:
            _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
            if ha_match_titoli:
                scambi_diretti_specifici.append(c)
            else:
                # Registra quali sono stati eliminati
                utenti_names = [u['user'].username for u in c['utenti']]
                catene_elim_sd.append(f"{' ↔ '.join(utenti_names)}")
        except Exception as e:
            output.append(f"   ⚠️  Errore su scambio diretto: {e}")

    # Filtra catene lunghe
    catene_specifiche = []
    catene_elim_lunghe = []
    for c in catene:
        try:
            _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
            if ha_match_titoli:
                catene_specifiche.append(c)
            else:
                utenti_names = [u['user'].username for u in c['utenti']]
                catene_elim_lunghe.append(f"{' → '.join(utenti_names)}")
        except Exception as e:
            output.append(f"   ⚠️  Errore su catena: {e}")

    output.append(f"\n📊 Risultati filtro qualità:")
    output.append(f"   Scambi diretti: {len(scambi_diretti)} → {len(scambi_diretti_specifici)} (eliminati {len(catene_elim_sd)})")
    output.append(f"   Catene lunghe: {len(catene)} → {len(catene_specifiche)} (eliminati {len(catene_elim_lunghe)})")

    if catene_elim_sd:
        output.append(f"\n   ❌ Scambi diretti eliminati (solo categoria):")
        for e in catene_elim_sd[:5]:
            output.append(f"      - {e}")
        if len(catene_elim_sd) > 5:
            output.append(f"      ... e altri {len(catene_elim_sd) - 5}")

    if catene_elim_lunghe:
        output.append(f"\n   ❌ Catene lunghe eliminate (solo categoria):")
        for e in catene_elim_lunghe[:5]:
            output.append(f"      - {e}")
        if len(catene_elim_lunghe) > 5:
            output.append(f"      ... e altri {len(catene_elim_lunghe) - 5}")

    # STEP 4: Filtra per utente
    output.append("\n" + "=" * 80)
    output.append(f"STEP 4: Filtra per utente {user.username}")
    output.append("=" * 80)

    try:
        scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
            scambi_diretti_specifici, catene_specifiche, user
        )

        output.append(f"\n✅ Dopo filtro utente:")
        output.append(f"   Scambi diretti: {len(scambi_diretti_utente)}")
        output.append(f"   Catene lunghe: {len(catene_lunghe_utente)}")

        totale_visualizzabile = len(scambi_diretti_utente) + len(catene_lunghe_utente)
        output.append(f"\n📊 TOTALE VISUALIZZABILE: {totale_visualizzabile}")

        # Mostra dettagli delle catene visualizzabili
        if totale_visualizzabile > 0:
            output.append(f"\n   Dettagli catene visualizzabili:")
            for c in (scambi_diretti_utente + catene_lunghe_utente)[:5]:
                utenti_names = [u['user'].username for u in c['utenti']]
                output.append(f"      - {' → '.join(utenti_names)}")

    except Exception as e:
        output.append(f"\n❌ ERRORE nel filtro utente: {e}")

    output.append("\n" + "=" * 80)
    return HttpResponse("\n".join(output), content_type="text/plain; charset=utf-8")
