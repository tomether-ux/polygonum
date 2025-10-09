#!/usr/bin/env python3
"""
Script standalone per calcolo cicli di scambio Polygonum
Utilizzato da Render Cron Job ogni 30 minuti

Questo script:
1. Si connette al database PostgreSQL
2. Invalida i cicli esistenti
3. Calcola nuovi cicli usando algoritmo DFS
4. Li salva nel database per lettura veloce
"""

import os
import sys
import django
from datetime import datetime

def setup_django():
    """Setup Django environment"""
    # Aggiungi il path del progetto
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
    django.setup()


def main():
    """
    Funzione principale per il calcolo cicli
    """
    print(f"[{datetime.now()}] 🚀 === POLYGONUM CYCLE CALCULATOR ===")
    print(f"[{datetime.now()}] 🌍 Environment: {os.environ.get('RENDER_ENVIRONMENT', 'local')}")

    try:
        # Setup Django
        setup_django()

        # Importa dopo setup Django
        from django.core.management import call_command
        from django.db import connection

        # Test connessione database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"[{datetime.now()}] ✅ Database connesso: {result}")

        # Esegui il comando di calcolo cicli
        print(f"[{datetime.now()}] 🔄 Avvio calcolo cicli...")
        call_command(
            'calcola_cicli',
            max_length=6,
            commit_batch_size=50,  # Batch più piccoli per Render
            cleanup_old=True,
            verbosity=2
        )

        # Statistiche finali
        from scambi.models import CicloScambio
        cicli_totali = CicloScambio.objects.count()
        cicli_validi = CicloScambio.objects.filter(valido=True).count()

        print(f"[{datetime.now()}] 📊 Statistiche finali:")
        print(f"[{datetime.now()}]   - Cicli totali: {cicli_totali}")
        print(f"[{datetime.now()}]   - Cicli validi: {cicli_validi}")
        print(f"[{datetime.now()}] ✅ === CALCOLO COMPLETATO CON SUCCESSO ===")

    except Exception as e:
        print(f"[{datetime.now()}] ❌ === ERRORE CRITICO ===")
        print(f"[{datetime.now()}] Errore: {e}")

        # Log traceback completo per debugging
        import traceback
        traceback.print_exc()

        # Exit con codice errore per far fallire il cron job
        sys.exit(1)


if __name__ == '__main__':
    main()