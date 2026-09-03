"""Lock applicativi per operazioni pesanti eseguite fuori dalla request normale."""

import threading
from contextlib import contextmanager

from django.db import connection


# Identificatore stabile riservato al calcolo globale dei cicli.
CYCLE_CALCULATION_LOCK_ID = 8_240_620_112
_local_cycle_lock = threading.Lock()


@contextmanager
def cycle_calculation_lock():
    """Prova ad acquisire un lock senza attendere e restituisce il risultato.

    In produzione PostgreSQL usa un advisory lock condiviso tra processi e
    istanze. SQLite e gli ambienti di test usano un lock nel processo locale.
    """
    if connection.vendor == 'postgresql':
        acquired = False
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT pg_try_advisory_lock(%s)',
                    [CYCLE_CALCULATION_LOCK_ID],
                )
                acquired = bool(cursor.fetchone()[0])
            yield acquired
        finally:
            if acquired:
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_unlock(%s)',
                        [CYCLE_CALCULATION_LOCK_ID],
                    )
        return

    acquired = _local_cycle_lock.acquire(blocking=False)
    try:
        yield acquired
    finally:
        if acquired:
            _local_cycle_lock.release()
