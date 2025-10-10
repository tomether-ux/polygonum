from django.core.management.base import BaseCommand
from scambi.models import CicloScambio
from datetime import datetime

class Command(BaseCommand):
    help = 'Rivalidate all cycles in the database (set valido=True for all cycles)'

    def handle(self, *args, **options):
        self.stdout.write(f"[{datetime.now()}] 🔧 Inizio rivalidazione cicli...")

        # Conta i cicli attuali
        total_cycles = CicloScambio.objects.count()
        invalid_cycles = CicloScambio.objects.filter(valido=False).count()
        valid_cycles = CicloScambio.objects.filter(valido=True).count()

        self.stdout.write(f"📊 Stato attuale:")
        self.stdout.write(f"   - Totale cicli: {total_cycles}")
        self.stdout.write(f"   - Cicli validi: {valid_cycles}")
        self.stdout.write(f"   - Cicli invalidi: {invalid_cycles}")

        if invalid_cycles == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ Tutti i cicli sono già validi! Niente da fare.")
            )
            return

        # Rivalidate all invalid cycles
        updated = CicloScambio.objects.filter(valido=False).update(valido=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"[{datetime.now()}] ✅ Rivalidati {updated} cicli! "
                f"Ora tutti i {total_cycles} cicli sono validi."
            )
        )