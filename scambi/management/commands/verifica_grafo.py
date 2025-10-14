from django.core.management.base import BaseCommand
from scambi.models import Annuncio
from scambi.matching import CycleFinder, oggetti_compatibili_avanzato, oggetti_compatibili_con_tipo
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Verifica il grafo di compatibilità per la catena da 6'

    def handle(self, *args, **options):
        usernames = ['admin', 'hhh', 'marco', 'piero', 'fede', 'obelus']

        self.stdout.write("=== VERIFICA GRAFO PER CATENA DA 6 ===\n")

        try:
            users = [User.objects.get(username=u) for u in usernames]
        except User.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"Utente non trovato: {e}"))
            return

        # Sequenza attesa: admin → hhh → marco → piero → fede → obelus → admin
        expected_sequence = [
            ('admin', 'hhh'),
            ('hhh', 'marco'),
            ('marco', 'piero'),
            ('piero', 'fede'),
            ('fede', 'obelus'),
            ('obelus', 'admin')
        ]

        for from_user, to_user in expected_sequence:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"VERIFICA MATCH: {from_user} → {to_user}")
            self.stdout.write(f"{'='*60}")

            try:
                user_a = User.objects.get(username=from_user)
                user_b = User.objects.get(username=to_user)

                offerte_a = Annuncio.objects.filter(utente=user_a, tipo='offro', attivo=True)
                richieste_b = Annuncio.objects.filter(utente=user_b, tipo='cerco', attivo=True)

                self.stdout.write(f"\n{from_user} OFFRE:")
                for off in offerte_a:
                    self.stdout.write(f"  [{off.id}] {off.titolo}")

                self.stdout.write(f"\n{to_user} CERCA:")
                for req in richieste_b:
                    self.stdout.write(f"  [{req.id}] {req.titolo}")

                # Test compatibilità con distanza default
                distanza_km = 50
                match_trovato = False

                for offerta in offerte_a:
                    for richiesta in richieste_b:
                        # Verifica con algoritmo avanzato
                        compatible_adv, punteggio_adv, dettagli_adv = oggetti_compatibili_avanzato(
                            offerta, richiesta, distanza_km
                        )

                        # Verifica con tipo match
                        compatible_tipo, tipo_match = oggetti_compatibili_con_tipo(offerta, richiesta)

                        if compatible_tipo:
                            self.stdout.write(f"\n  ✓ MATCH TROVATO:")
                            self.stdout.write(f"    Offerta: {offerta.titolo}")
                            self.stdout.write(f"    Richiesta: {richiesta.titolo}")
                            self.stdout.write(f"    Tipo match: {tipo_match}")
                            self.stdout.write(f"    Punteggio avanzato: {punteggio_adv}")
                            self.stdout.write(f"    Compatible avanzato: {compatible_adv}")
                            self.stdout.write(f"    Dettagli: {dettagli_adv}")

                            if punteggio_adv < 20:
                                self.stdout.write(self.style.WARNING(
                                    f"    ⚠️ PROBLEMA: Punteggio {punteggio_adv} < 20 (soglia minima)"
                                ))
                                self.stdout.write(self.style.WARNING(
                                    "    Questo match NON sarà incluso nel grafo!"
                                ))
                            else:
                                self.stdout.write(self.style.SUCCESS(
                                    f"    ✓ OK: Punteggio {punteggio_adv} >= 20"
                                ))

                            match_trovato = True

                if not match_trovato:
                    self.stdout.write(self.style.ERROR("\n  ❌ NESSUN MATCH TROVATO"))
                    self.stdout.write(self.style.ERROR("  Questo collegamento NON esiste nel grafo!"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Errore: {e}"))
                import traceback
                traceback.print_exc()

        # Ora costruisci il grafo reale e verifica
        self.stdout.write(f"\n\n{'='*60}")
        self.stdout.write("COSTRUZIONE GRAFO REALE")
        self.stdout.write(f"{'='*60}\n")

        finder = CycleFinder()
        finder.costruisci_grafo()

        self.stdout.write("\nGrafo costruito. Verifica collegamenti:")
        for from_user, to_user in expected_sequence:
            user_a = User.objects.get(username=from_user)
            user_b = User.objects.get(username=to_user)

            if user_a.id in finder.grafo and user_b.id in finder.grafo[user_a.id]:
                self.stdout.write(self.style.SUCCESS(f"✓ {from_user} → {to_user} presente nel grafo"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ {from_user} → {to_user} ASSENTE dal grafo"))
