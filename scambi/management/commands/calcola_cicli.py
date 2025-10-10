import os
import sys
import django
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

# Setup Django environment per script standalone
if __name__ == "__main__":
    # Assicurati che Django sia configurato
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
    django.setup()

from scambi.models import CicloScambio
from scambi.matching import CycleFinder


class Command(BaseCommand):
    help = 'Calcola tutti i cicli di scambio e li salva nel database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-length',
            type=int,
            default=6,
            help='Lunghezza massima dei cicli (default: 6)'
        )
        parser.add_argument(
            '--commit-batch-size',
            type=int,
            default=100,
            help='Numero di cicli da committare per volta (default: 100)'
        )
        parser.add_argument(
            '--cleanup-old',
            action='store_true',
            help='Rimuove i cicli invalidati più vecchi di 7 giorni'
        )

    def handle(self, *args, **options):
        """
        Metodo principale del comando Django
        """
        max_length = options['max_length']
        batch_size = options['commit_batch_size']
        cleanup_old = options['cleanup_old']

        self.stdout.write(
            self.style.SUCCESS(f"[{datetime.now()}] 🚀 Avvio calcolo cicli...")
        )

        try:
            # Step 1: Cleanup cicli vecchi se richiesto
            if cleanup_old:
                deleted_count, _ = CicloScambio.cleanup_old()
                self.stdout.write(
                    self.style.WARNING(f"[{datetime.now()}] 🧹 Rimossi {deleted_count} cicli vecchi")
                )

            # Step 2: Rimuovi tutti i cicli esistenti (per evitare conflitti di hash)
            deleted_count, _ = CicloScambio.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"[{datetime.now()}] 🗑️ Rimossi {deleted_count} cicli esistenti")
            )

            # Step 3: Calcola nuovi cicli
            finder = CycleFinder()
            finder.costruisci_grafo()

            # Trova tutti i cicli (da 2 a max_length utenti) con un unico algoritmo
            cicli = finder.trova_tutti_cicli(max_length=max_length)

            # Conta per lunghezza per stats
            scambi_diretti = [c for c in cicli if c['lunghezza'] == 2]
            catene_lunghe = [c for c in cicli if c['lunghezza'] > 2]

            self.stdout.write(
                self.style.HTTP_INFO(
                    f"[{datetime.now()}] 📊 Trovati {len(scambi_diretti)} scambi diretti + {len(catene_lunghe)} catene lunghe = {len(cicli)} totali"
                )
            )

            if not cicli:
                self.stdout.write(
                    self.style.WARNING(f"[{datetime.now()}] ⚠️ Nessun ciclo trovato")
                )
                return

            # Step 4: Salva i cicli nel database
            self._salva_cicli_batch(cicli, batch_size)

            # Step 5: Statistiche finali
            cicli_validi = CicloScambio.objects.filter(valido=True).count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{datetime.now()}] ✅ Calcolo completato! "
                    f"Cicli validi nel DB: {cicli_validi}"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[{datetime.now()}] ❌ Errore durante il calcolo: {e}")
            )
            sys.exit(1)

    def _salva_cicli_batch(self, cicli, batch_size):
        """
        Salva i cicli nel database a batch per ottimizzare le performance
        """
        total_cicli = len(cicli)
        salvati = 0
        errori = 0

        self.stdout.write(
            self.style.HTTP_INFO(f"[{datetime.now()}] 💾 Inizio salvataggio {total_cicli} cicli...")
        )

        for i in range(0, total_cicli, batch_size):
            batch = cicli[i:i + batch_size]

            try:
                with transaction.atomic():
                    for ciclo_data in batch:
                        try:
                            ciclo_obj = CicloScambio(
                                users=ciclo_data['users'],
                                lunghezza=ciclo_data['lunghezza'],
                                dettagli=ciclo_data['dettagli'],
                                hash_ciclo=ciclo_data['hash_ciclo'],
                                valido=True
                            )
                            ciclo_obj.save()
                            salvati += 1

                        except Exception as e:
                            errori += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"[{datetime.now()}] ⚠️ Errore salvando ciclo {ciclo_data.get('hash_ciclo', 'unknown')}: {type(e).__name__}: {e}"
                                )
                            )

                # Progress update ogni batch
                progresso = (i + len(batch)) / total_cicli * 100
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f"[{datetime.now()}] 📊 Progresso: {progresso:.1f}% "
                        f"({salvati} salvati, {errori} errori)"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"[{datetime.now()}] ❌ Errore nel batch {i}-{i+len(batch)}: {e}")
                )
                errori += len(batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"[{datetime.now()}] 💾 Salvataggio completato: "
                f"{salvati} cicli salvati, {errori} errori"
            )
        )


# Script standalone per Render Cron Job
def main():
    """
    Funzione principale per esecuzione standalone (usata da Render Cron)
    """
    print(f"[{datetime.now()}] 🎯 Avvio calcolo cicli Polygonum (standalone)...")

    try:
        # Setup Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scambio_sito.settings')
        django.setup()

        # Importa dopo setup Django
        from django.core.management import call_command

        # Esegui il comando Django
        call_command('calcola_cicli', verbosity=2)

        print(f"[{datetime.now()}] ✅ Calcolo cicli completato con successo!")

    except Exception as e:
        print(f"[{datetime.now()}] ❌ ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()