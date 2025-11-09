"""
Comando Django per cancellare le vecchie immagini rotte dal database.

Usage:
    python manage.py cancella_immagini_vecchie
"""
from django.core.management.base import BaseCommand
from scambi.models import Annuncio


class Command(BaseCommand):
    help = 'Cancella tutte le vecchie immagini rotte degli annunci (pre-fix Cloudinary)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe cancellato senza effettuare modifiche',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING(
            '\n' + '='*60
        ))
        self.stdout.write(self.style.WARNING(
            '  CANCELLA IMMAGINI VECCHIE (rotte pre-fix Cloudinary)'
        ))
        self.stdout.write(self.style.WARNING(
            '='*60 + '\n'
        ))

        # Trova tutti gli annunci con immagini
        annunci_con_immagini = Annuncio.objects.exclude(immagine='').exclude(immagine=None)
        total_count = annunci_con_immagini.count()

        self.stdout.write(f"Trovati {total_count} annunci con immagini\n")

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODALITÀ DRY-RUN (nessuna modifica effettiva)\n'))

        deleted_count = 0
        for annuncio in annunci_con_immagini:
            image_name = annuncio.immagine.name if annuncio.immagine else 'N/A'

            if dry_run:
                self.stdout.write(
                    f"  • Annuncio #{annuncio.id} - {annuncio.titolo[:40]}\n"
                    f"    Immagine: {image_name}"
                )
            else:
                # Cancella l'immagine
                annuncio.immagine.delete(save=False)  # Non salva ancora
                annuncio.immagine = None
                annuncio.save()
                deleted_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Cancellata immagine da annuncio #{annuncio.id} - {annuncio.titolo[:40]}"
                    )
                )

        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 DRY-RUN COMPLETATO: {total_count} immagini verrebbero cancellate\n'
                )
            )
            self.stdout.write(
                'Esegui senza --dry-run per effettuare la cancellazione:\n'
                '  python manage.py cancella_immagini_vecchie\n'
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ COMPLETATO: {deleted_count} immagini cancellate con successo!\n'
                )
            )
            self.stdout.write(
                'Ora gli annunci useranno il placeholder fino a quando\n'
                'non caricherai nuove immagini (che funzioneranno correttamente).\n'
            )
        self.stdout.write('='*60 + '\n')
