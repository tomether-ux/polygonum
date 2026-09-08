"""Configurazione Gunicorn prudente per il servizio web Polygonum."""

import os


def _bounded_int(name, default, minimum, maximum):
    """Legge un intero dall'ambiente e fallisce subito se non è sicuro."""
    raw_value = os.environ.get(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f'{name} deve essere un numero intero') from exc

    if not minimum <= value <= maximum:
        raise RuntimeError(
            f'{name} deve essere compreso tra {minimum} e {maximum}'
        )
    return value


bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Un solo processo mantiene coerenti cache e rate limit LocMem. I thread
# permettono comunque di servire altre richieste mentre una è in attesa di
# database, Cloudinary o SMTP, con un consumo RAM più prudente su Render.
workers = 1
worker_class = 'gthread'
threads = _bounded_int('GUNICORN_THREADS', 4, 2, 8)

# Il calcolo protetto delle catene può durare più dei 30 secondi predefiniti di
# Gunicorn. Il limite resta finito per evitare richieste bloccate senza termine.
timeout = _bounded_int('GUNICORN_TIMEOUT_SECONDS', 120, 30, 300)
graceful_timeout = 30
keepalive = 5

accesslog = '-'
errorlog = '-'
capture_output = True
