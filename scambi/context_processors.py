"""Context processor globali disponibili in tutti i template."""
from django.db.models import Count, Q

from .models import Categoria


def categorie_navbar(request):
    """
    Rende disponibili le categorie più popolari per la sotto-navbar
    (presente in ogni pagina tramite base.html).
    """
    categorie = (
        Categoria.objects.annotate(
            num_annunci=Count('annuncio', filter=Q(annuncio__attivo=True))
        )
        .order_by('-num_annunci')[:4]
    )
    return {'categorie_navbar': categorie}
