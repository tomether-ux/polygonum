from django.core.management.base import BaseCommand
from scambi.models import CicloScambio
from datetime import datetime

class Command(BaseCommand):
    help = 'Valida tutti i cicli verificando che gli annunci esistano ancora'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-valid',
            action='store_true',
            help='Forza tutti i cicli come validi senza controllare gli annunci (non raccomandato)'
        )
        parser.add_argument(
            '--show-details',
            action='store_true',
            help='Mostra dettagli degli annunci mancanti'
        )

    def handle(self, *args, **options):
        force_valid = options.get('force_valid', False)
        show_details = options.get('show_details', False)

        self.stdout.write(f"[{datetime.now()}] 🔧 Inizio validazione cicli...")

        # Conta i cicli attuali
        total_cycles = CicloScambio.objects.count()
        invalid_cycles = CicloScambio.objects.filter(valido=False).count()
        valid_cycles = CicloScambio.objects.filter(valido=True).count()

        self.stdout.write(f"📊 Stato prima della validazione:")
        self.stdout.write(f"   - Totale cicli: {total_cycles}")
        self.stdout.write(f"   - Cicli validi: {valid_cycles}")
        self.stdout.write(f"   - Cicli invalidi: {invalid_cycles}")

        if force_valid:
            self.stdout.write(
                self.style.WARNING("⚠️  Modalità force-valid attiva - rivalidazione senza controlli")
            )
            updated = CicloScambio.objects.filter(valido=False).update(valido=True)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{datetime.now()}] ✅ Forzati {updated} cicli come validi"
                )
            )
            return

        # Validazione intelligente: controlla annunci
        self.stdout.write("🔍 Validazione annunci in corso...")
        stats = CicloScambio.validate_all_cycles()

        self.stdout.write(f"\n📊 Risultati validazione:")
        self.stdout.write(f"   - Cicli controllati: {stats['total_checked']}")
        self.stdout.write(
            self.style.SUCCESS(f"   - Cicli ancora validi: {stats['still_valid']}")
        )

        if stats['invalidated'] > 0:
            self.stdout.write(
                self.style.WARNING(f"   - Cicli invalidati: {stats['invalidated']}")
            )
            self.stdout.write(
                f"   💡 Motivo: annunci non più esistenti o non attivi"
            )

            if show_details and stats['missing_annunci_details']:
                self.stdout.write("\n📋 Dettagli annunci mancanti:")
                for detail in stats['missing_annunci_details'][:10]:  # Max 10 per non sovracaricare
                    self.stdout.write(
                        f"   - Ciclo {detail['ciclo_id']} ({detail['hash'][:8]}...): "
                        f"annunci mancanti: {detail['missing_annunci']}"
                    )
                if len(stats['missing_annunci_details']) > 10:
                    remaining = len(stats['missing_annunci_details']) - 10
                    self.stdout.write(f"   ... e altri {remaining} cicli")
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ Tutti i cicli validi hanno annunci attivi!")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n[{datetime.now()}] ✅ Validazione completata!"
            )
        )