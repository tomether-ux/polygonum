"""
Management command per approvare automaticamente gli annunci senza immagine
"""
from django.core.management.base import BaseCommand
from scambi.models import Annuncio


class Command(BaseCommand):
    help = 'Approva automaticamente tutti gli annunci senza immagine che sono in pending'

    def handle(self, *args, **options):
        # Trova tutti gli annunci senza immagine in pending
        annunci_pending = Annuncio.objects.filter(
            moderation_status='pending'
        ).filter(immagine__in=['', None])

        count = annunci_pending.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ Nessun annuncio senza immagine da approvare'))
            return

        self.stdout.write(f'Trovati {count} annunci senza immagine in pending')

        # Approva tutti
        updated = annunci_pending.update(moderation_status='approved')

        self.stdout.write(self.style.SUCCESS(
            f'✓ Approvati {updated} annunci senza immagine'
        ))

        # Mostra statistiche finali
        total_approved = Annuncio.objects.filter(moderation_status='approved', attivo=True).count()
        total_pending = Annuncio.objects.filter(moderation_status='pending', attivo=True).count()

        self.stdout.write(f'\nStatistiche annunci attivi:')
        self.stdout.write(f'  Approved: {total_approved}')
        self.stdout.write(f'  Pending: {total_pending}')
