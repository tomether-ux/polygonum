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

from scambi.models import CicloScambio, CalcoloMetadata
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
        parser.add_argument(
            '--incremental',
            action='store_true',
            help='Usa calcolo incrementale (ricalcola solo cicli impattati da modifiche)'
        )
        parser.add_argument(
            '--force-full',
            action='store_true',
            help='Forza calcolo completo anche se ci sono poche modifiche'
        )

    def handle(self, *args, **options):
        """
        Metodo principale del comando Django
        """
        import time
        start_time = time.time()

        max_length = options['max_length']
        batch_size = options['commit_batch_size']
        cleanup_old = options['cleanup_old']
        incremental = options['incremental']
        force_full = options['force_full']

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

            # Step 2: Determina se usare calcolo incrementale o completo
            usa_incrementale = False
            metadata = CalcoloMetadata.get_or_create_singleton()

            if incremental and not force_full:
                finder = CycleFinder()

                # Trova annunci modificati dall'ultimo calcolo
                annunci_modificati = finder.get_annunci_modificati(metadata.ultimo_calcolo_completo)
                count_modificati = annunci_modificati.count()

                self.stdout.write(
                    self.style.HTTP_INFO(f"[{datetime.now()}] 📋 Annunci modificati: {count_modificati}")
                )

                # Se ci sono modifiche, usa calcolo incrementale
                if count_modificati > 0:
                    # Se ci sono TROPPI annunci modificati (>30% del totale), meglio fare calcolo completo
                    from scambi.models import Annuncio
                    totale_annunci = Annuncio.objects.filter(attivo=True).count()
                    percentuale_modificati = (count_modificati / totale_annunci * 100) if totale_annunci > 0 else 100

                    if percentuale_modificati > 30:
                        self.stdout.write(
                            self.style.WARNING(
                                f"[{datetime.now()}] ⚠️ Troppe modifiche ({percentuale_modificati:.1f}%), "
                                f"uso calcolo completo invece di incrementale"
                            )
                        )
                    else:
                        usa_incrementale = True
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[{datetime.now()}] ⚡ Uso calcolo incrementale ({percentuale_modificati:.1f}% modificati)"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"[{datetime.now()}] ✅ Nessuna modifica, niente da ricalcolare")
                    )
                    return

            # Step 3: Calcola cicli (incrementale o completo)
            if usa_incrementale:
                cicli = self._calcolo_incrementale(finder, annunci_modificati, max_length)
            else:
                cicli = self._calcolo_completo(max_length)

            # Step 4: Salva i cicli nel database
            if cicli:
                self._salva_cicli_batch(cicli, batch_size)
            else:
                self.stdout.write(
                    self.style.WARNING(f"[{datetime.now()}] ⚠️ Nessun ciclo trovato")
                )

            # Step 5: Aggiorna metadata e statistiche finali
            elapsed = time.time() - start_time
            cicli_validi = CicloScambio.objects.filter(valido=True).count()
            CalcoloMetadata.aggiorna_calcolo(cicli_validi, elapsed)

            self.stdout.write(
                self.style.SUCCESS(
                    f"[{datetime.now()}] ✅ Calcolo completato in {elapsed:.1f}s! "
                    f"Cicli validi nel DB: {cicli_validi}"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[{datetime.now()}] ❌ Errore durante il calcolo: {e}")
            )
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def _calcolo_completo(self, max_length):
        """
        Esegue calcolo completo di tutti i cicli
        """
        self.stdout.write(
            self.style.HTTP_INFO(f"[{datetime.now()}] 🔄 Calcolo completo di tutti i cicli...")
        )

        # Marca tutti i cicli esistenti come non validi
        existing_count = CicloScambio.objects.filter(valido=True).count()
        CicloScambio.objects.filter(valido=True).update(valido=False)
        self.stdout.write(
            self.style.WARNING(f"[{datetime.now()}] 🔄 Marcati {existing_count} cicli come non validi")
        )

        # Calcola nuovi cicli
        finder = CycleFinder()
        finder.costruisci_grafo()
        cicli = finder.trova_tutti_cicli(max_length=max_length)

        # Stats
        scambi_diretti = [c for c in cicli if c['lunghezza'] == 2]
        catene_lunghe = [c for c in cicli if c['lunghezza'] > 2]

        self.stdout.write(
            self.style.HTTP_INFO(
                f"[{datetime.now()}] 📊 Trovati {len(scambi_diretti)} scambi diretti + "
                f"{len(catene_lunghe)} catene lunghe = {len(cicli)} totali"
            )
        )

        return cicli

    def _calcolo_incrementale(self, finder, annunci_modificati, max_length):
        """
        Esegue calcolo incrementale solo per gli utenti impattati
        """
        self.stdout.write(
            self.style.HTTP_INFO(f"[{datetime.now()}] ⚡ Calcolo incrementale...")
        )

        # Step 1: Identifica utenti impattati
        utenti_impattati = finder.get_utenti_impattati(annunci_modificati)

        # Step 2: Invalida solo i cicli che coinvolgono questi utenti
        count_invalidati = finder.invalida_cicli_con_utenti(utenti_impattati)

        # Step 3: Costruisci grafo e trova nuovi cicli per questi utenti
        finder.costruisci_grafo()
        cicli = finder.trova_cicli_per_utenti(utenti_impattati, max_length)

        # Stats
        scambi_diretti = [c for c in cicli if c['lunghezza'] == 2]
        catene_lunghe = [c for c in cicli if c['lunghezza'] > 2]

        self.stdout.write(
            self.style.HTTP_INFO(
                f"[{datetime.now()}] 📊 Ricalcolati {len(scambi_diretti)} scambi diretti + "
                f"{len(catene_lunghe)} catene lunghe = {len(cicli)} totali per {len(utenti_impattati)} utenti"
            )
        )

        return cicli

    def _salva_cicli_batch(self, cicli, batch_size):
        """
        Salva i cicli nel database a batch usando upsert intelligente
        - Se il ciclo esiste già (stesso hash_ciclo), lo riattiva e aggiorna i dettagli
        - Se il ciclo è nuovo, lo crea
        - Questo preserva gli ID dei cicli esistenti e le PropostaCatena collegate!
        """
        total_cicli = len(cicli)
        creati = 0
        aggiornati = 0
        errori = 0

        self.stdout.write(
            self.style.HTTP_INFO(f"[{datetime.now()}] 💾 Inizio salvataggio/aggiornamento {total_cicli} cicli...")
        )

        for i in range(0, total_cicli, batch_size):
            batch = cicli[i:i + batch_size]

            try:
                with transaction.atomic():
                    for ciclo_data in batch:
                        try:
                            hash_ciclo = ciclo_data['hash_ciclo']

                            # Cerca se esiste già un ciclo con questo hash
                            ciclo_esistente = CicloScambio.objects.filter(hash_ciclo=hash_ciclo).first()

                            if ciclo_esistente:
                                # AGGIORNA il ciclo esistente (preserva ID e PropostaCatena!)
                                ciclo_esistente.users = ciclo_data['users']
                                ciclo_esistente.lunghezza = ciclo_data['lunghezza']
                                ciclo_esistente.dettagli = ciclo_data['dettagli']
                                ciclo_esistente.valido = True  # Riattiva
                                ciclo_esistente.save()
                                aggiornati += 1
                            else:
                                # CREA nuovo ciclo
                                CicloScambio.objects.create(
                                    users=ciclo_data['users'],
                                    lunghezza=ciclo_data['lunghezza'],
                                    dettagli=ciclo_data['dettagli'],
                                    hash_ciclo=hash_ciclo,
                                    valido=True
                                )
                                creati += 1

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
                        f"({creati} nuovi, {aggiornati} aggiornati, {errori} errori)"
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
                f"{creati} cicli nuovi creati, {aggiornati} cicli esistenti aggiornati, {errori} errori"
            )
        )

        # Cleanup cicli che non sono più validi (non trovati nel nuovo calcolo)
        # Ma SOLO se non hanno proposte attive!
        cicli_da_rimuovere = CicloScambio.objects.filter(
            valido=False
        ).exclude(
            proposte__stato='in_attesa'  # Non eliminare cicli con proposte in attesa
        )
        rimossi_count = cicli_da_rimuovere.count()
        if rimossi_count > 0:
            cicli_da_rimuovere.delete()
            self.stdout.write(
                self.style.WARNING(
                    f"[{datetime.now()}] 🗑️ Rimossi {rimossi_count} cicli non più validi (senza proposte attive)"
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