import os
import subprocess
import sys

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Avvia le attività pianificate in un processo con timeout assoluto'

    def handle(self, *args, **options):
        raw_timeout = os.environ.get('BACKGROUND_HARD_TIMEOUT_SECONDS', '240')
        try:
            timeout_seconds = int(raw_timeout)
        except (TypeError, ValueError) as exc:
            raise CommandError(
                'BACKGROUND_HARD_TIMEOUT_SECONDS deve essere un intero'
            ) from exc

        if not 60 <= timeout_seconds <= 300:
            raise CommandError(
                'BACKGROUND_HARD_TIMEOUT_SECONDS deve essere tra 60 e 300'
            )

        command = [sys.executable, 'manage.py', 'run_scheduled_tasks']
        try:
            completed = subprocess.run(
                command,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise CommandError(
                f'Attività interrotte dopo {timeout_seconds}s'
            ) from exc

        if completed.returncode != 0:
            raise CommandError(
                f'Attività terminate con codice {completed.returncode}'
            )
