"""
API Views per il pannello di amministrazione Polygonum Gestionale
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import Annuncio, User, CatenaScambio
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import timedelta
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

    # Contatori principali
    utenti_totali = User.objects.count()
    annunci_attivi = Annuncio.objects.filter(attivo=True).count()
    catene_completate = CatenaScambio.objects.filter(stato='completata').count()

    # Nuove iscrizioni oggi
    oggi = timezone.now().date()
    nuove_iscrizioni_oggi = User.objects.filter(
        date_joined__date=oggi
    ).count()

    # Iscrizioni ultimi 30 giorni (per grafico)
    data_inizio = oggi - timedelta(days=29)  # Includi oggi = 30 giorni totali

    iscrizioni_per_giorno = User.objects.filter(
        date_joined__date__gte=data_inizio
    ).annotate(
        data=TruncDate('date_joined')
    ).values('data').annotate(
        count=Count('id')
    ).order_by('data')

    # Crea array completo degli ultimi 30 giorni (anche giorni con 0 iscrizioni)
    iscrizioni_dict = {entry['data']: entry['count'] for entry in iscrizioni_per_giorno}

    iscrizioni_ultimi_30_giorni = []
    for i in range(30):
        data = data_inizio + timedelta(days=i)
        iscrizioni_ultimi_30_giorni.append({
            'data': data.isoformat(),
            'count': iscrizioni_dict.get(data, 0)
        })

    return JsonResponse({
        'utenti_totali': utenti_totali,
        'annunci_attivi': annunci_attivi,
        'catene_completate': catene_completate,
        'nuove_iscrizioni_oggi': nuove_iscrizioni_oggi,
        'iscrizioni_ultimi_30_giorni': iscrizioni_ultimi_30_giorni
    })
