"""
Comando Django per popolare le fasce di prezzo degli annunci esistenti
basandosi sul loro prezzo_stimato.

Uso: python manage.py popola_fasce_prezzo
"""

from django.core.management.base import BaseCommand
from django.db import models
from scambi.models import Annuncio


class Command(BaseCommand):
    help = 'Popola il campo fascia_prezzo per tutti gli annunci esistenti basandosi sul prezzo_stimato'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe fatto senza salvare modifiche',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 Modalità DRY-RUN: nessuna modifica verrà salvata'))

        # Trova tutti gli annunci con prezzo ma senza fascia
        annunci_da_aggiornare = Annuncio.objects.filter(
            prezzo_stimato__isnull=False
        ).filter(
            models.Q(fascia_prezzo__isnull=True) | models.Q(fascia_prezzo='')
        )

        # Oppure aggiorna TUTTI gli annunci con prezzo (ricalcola anche le fasce esistenti)
        # Decommenta la linea sotto per ricalcolare tutte le fasce
        # annunci_da_aggiornare = Annuncio.objects.filter(prezzo_stimato__isnull=False)

        totale = annunci_da_aggiornare.count()

        if totale == 0:
            self.stdout.write(self.style.SUCCESS('✅ Nessun annuncio da aggiornare'))
            return

        self.stdout.write(f'\n📊 Trovati {totale} annunci con prezzo da classificare\n')

        # Contatori per statistiche
        stats = {
            'economico': 0,
            'basso': 0,
            'medio': 0,
            'alto': 0,
            'premium': 0,
        }

        aggiornati = 0

        for annuncio in annunci_da_aggiornare:
            # Calcola la fascia usando il metodo del model
            fascia_calcolata = annuncio.calcola_fascia_prezzo()

            if fascia_calcolata:
                stats[fascia_calcolata] += 1

                # Mostra progress ogni 10 annunci
                if (aggiornati + 1) % 10 == 0:
                    self.stdout.write(f'   Processati {aggiornati + 1}/{totale}...', ending='\r')

                if not dry_run:
                    annuncio.fascia_prezzo = fascia_calcolata
                    annuncio.save(update_fields=['fascia_prezzo'])

                aggiornati += 1

        # Stampa risultati
        self.stdout.write('\n')
        self.stdout.write(self.style.SUCCESS(f'✅ {"Simulati" if dry_run else "Aggiornati"} {aggiornati} annunci\n'))

        # Mostra statistiche per fascia
        self.stdout.write('📈 Distribuzione per fascia:')
        for fascia, count in stats.items():
            percentuale = (count / totale * 100) if totale > 0 else 0
            barra = '█' * int(percentuale / 2)
            self.stdout.write(f'   {fascia.ljust(10)}: {str(count).rjust(4)} ({percentuale:5.1f}%) {barra}')

        # Mostra esempi per ogni fascia
        if not dry_run:
            self.stdout.write('\n🔍 Esempi per fascia:')
            for fascia_nome in ['economico', 'basso', 'medio', 'alto', 'premium']:
                esempio = Annuncio.objects.filter(fascia_prezzo=fascia_nome).first()
                if esempio:
                    self.stdout.write(
                        f'   {fascia_nome.ljust(10)}: €{esempio.prezzo_stimato} - "{esempio.titolo[:40]}"'
                    )

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  Riesegui senza --dry-run per salvare le modifiche'))
