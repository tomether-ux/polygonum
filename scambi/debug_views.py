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
