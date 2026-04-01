"""
API Views per il pannello di amministrazione Polygonum Gestionale
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import Annuncio, User
from django.utils import timezone
import json


def verificatoken_admin(request):
    """
    Verifica che la richiesta abbia il token admin corretto nell'header Authorization
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return False

    token = auth_header.replace('Bearer ', '')
    admin_token = getattr(settings, 'ADMIN_GESTIONALE_TOKEN', None)

    if not admin_token:
        return False

    return token == admin_token


@csrf_exempt
@require_http_methods(["GET"])
def annunci_pending(request):
    """
    GET /api/admin/annunci-pending/
    Restituisce la lista di annunci con immagini in stato pending
    """
    # Verifica token
    if not verificatoken_admin(request):
        return JsonResponse({'error': 'Non autorizzato'}, status=401)

    # Query annunci pending con immagine
    annunci = Annuncio.objects.filter(
        moderation_status='pending',
        immagine__isnull=False
    ).select_related('utente').order_by('-data_creazione')

    # Serializza i dati
    data = []
    for annuncio in annunci:
        # Costruisci l'URL dell'immagine Cloudinary
        immagine_url = ''
        if annuncio.immagine:
            try:
                # CloudinaryField ha un metodo url
                immagine_url = annuncio.immagine.url
            except:
                immagine_url = str(annuncio.immagine)

        data.append({
            'id': annuncio.id,
            'titolo': annuncio.titolo,
            'descrizione': annuncio.descrizione[:200],  # Primi 200 caratteri
            'immagine_url': immagine_url,
            'utente_username': annuncio.utente.username,
            'utente_email': annuncio.utente.email,
            'data_upload': annuncio.data_creazione.isoformat(),
            'categoria': annuncio.categoria.nome if annuncio.categoria else '',
            'tipo': annuncio.get_tipo_display(),
        })

    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def modera_annuncio(request, annuncio_id):
    """
    POST /api/admin/modera/<id>/
    Body: {"azione": "approva"} o {"azione": "elimina"}

    Approva o elimina un annuncio
    """
    # Verifica token
    if not verificatoken_admin(request):
        return JsonResponse({'error': 'Non autorizzato'}, status=401)

    # Parse body
    try:
        body = json.loads(request.body)
        azione = body.get('azione')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON non valido'}, status=400)

    if azione not in ['approva', 'elimina']:
        return JsonResponse({'error': 'Azione non valida. Usa "approva" o "elimina"'}, status=400)

    # Trova l'annuncio
    annuncio = get_object_or_404(Annuncio, id=annuncio_id)

    if azione == 'approva':
        annuncio.moderation_status = 'approved'
        annuncio.moderated_at = timezone.now()
        annuncio.save()

        return JsonResponse({
            'success': True,
            'message': f'Annuncio #{annuncio_id} approvato',
            'annuncio_id': annuncio_id,
            'nuovo_stato': 'approved'
        })

    elif azione == 'elimina':
        # Elimina l'annuncio
        annuncio_id_deleted = annuncio.id
        annuncio.delete()

        return JsonResponse({
            'success': True,
            'message': f'Annuncio #{annuncio_id_deleted} eliminato',
            'annuncio_id': annuncio_id_deleted,
            'eliminato': True
        })


@csrf_exempt
@require_http_methods(["GET"])
def stats_dashboard(request):
    """
    GET /api/admin/stats/
    Restituisce statistiche per la dashboard (FASE 2)
    """
    # Verifica token
    if not verificatoken_admin(request):
        return JsonResponse({'error': 'Non autorizzato'}, status=401)

    # TODO: Implementare le statistiche nella Fase 2
    return JsonResponse({
        'utenti_totali': User.objects.count(),
        'annunci_attivi': Annuncio.objects.filter(attivo=True).count(),
        'message': 'Statistiche complete da implementare nella Fase 2'
    })
