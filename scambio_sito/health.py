import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


def _health_response(payload, *, status=200):
    response = JsonResponse(payload, status=status)
    response['Cache-Control'] = 'no-store'
    return response


@require_http_methods(['GET', 'HEAD'])
def liveness(request):
    """Conferma che il processo web è in grado di rispondere."""
    return _health_response({'status': 'ok'})


@require_http_methods(['GET', 'HEAD'])
def readiness(request):
    """Conferma che il processo web riesce a comunicare con il database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            database_ready = cursor.fetchone() == (1,)
    except Exception as exc:
        logger.warning(
            'Database readiness check failed error_type=%s',
            type(exc).__name__,
        )
        database_ready = False

    if not database_ready:
        return _health_response({'status': 'unavailable'}, status=503)

    return _health_response({'status': 'ok'})
