from django.core.management.base import BaseCommand
from scambi.models import Annuncio, CicloScambio
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Debug della catena da 6 persone'

    def handle(self, *args, **options):
        usernames = ['admin', 'hhh', 'marco', 'piero', 'fede', 'obelus']

        self.stdout.write("=== CATENA DA 6: admin → hhh → marco → piero → fede → obelus → admin ===\n")

        user_ids = []
        for i, username in enumerate(usernames):
            try:
                user = User.objects.get(username=username)
                user_ids.append(user.id)
                next_username = usernames[(i + 1) % len(usernames)]

                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"{i+1}. {username.upper()} (ID: {user.id})")
                self.stdout.write(f"{'='*60}")

                annunci_offre = Annuncio.objects.filter(utente=user, tipo='offro', attivo=True)
                annunci_cerca = Annuncio.objects.filter(utente=user, tipo='cerco', attivo=True)

                self.stdout.write(f"\n{username} OFFRE:")
                if annunci_offre.exists():
                    for a in annunci_offre:
                        self.stdout.write(f"  [{a.id}] {a.titolo}")
                        self.stdout.write(f"      Categoria: {a.categoria}")
                else:
                    self.stdout.write("  (nessun annuncio attivo)")

                self.stdout.write(f"\n{username} CERCA:")
                if annunci_cerca.exists():
                    for a in annunci_cerca:
                        self.stdout.write(f"  [{a.id}] {a.titolo}")
                        self.stdout.write(f"      Categoria: {a.categoria}")
                else:
                    self.stdout.write("  (nessun annuncio attivo)")

                self.stdout.write(f"\n→ Deve matchare con: {next_username}")

            except User.DoesNotExist:
                self.stdout.write(f"\n❌ User '{username}' non trovato")

        # Check for 6-person cycles
        self.stdout.write(f"\n\n{'='*60}")
        self.stdout.write("CICLI DA 6 PERSONE NEL DATABASE")
        self.stdout.write(f"{'='*60}")

        if user_ids:
            self.stdout.write(f"\nUser IDs cercati: {user_ids}")

            cicli_6 = CicloScambio.objects.filter(lunghezza=6)
            self.stdout.write(f"\nTotale cicli da 6 nel DB: {cicli_6.count()}")

            for ciclo in cicli_6:
                self.stdout.write(f"\n--- Ciclo ID {ciclo.id} ---")
                self.stdout.write(f"Users: {ciclo.users}")
                self.stdout.write(f"ha_match_titoli: {ciclo.dettagli.get('ha_match_titoli', 'N/A')}")
                self.stdout.write(f"valido: {ciclo.valido}")

                # Check if it matches our users
                if set(ciclo.users) == set(user_ids):
                    self.stdout.write(self.style.SUCCESS("\n✓ QUESTO È IL CICLO CHE CERCHIAMO!"))

                    # Print detailed matches
                    if 'matches' in ciclo.dettagli:
                        self.stdout.write("\nMatches dettagliati:")
                        for j, match in enumerate(ciclo.dettagli['matches'], 1):
                            self.stdout.write(f"\n  Match {j}:")
                            self.stdout.write(f"    Offre ID: {match.get('offre_id')}")
                            self.stdout.write(f"    Cerca ID: {match.get('cerca_id')}")
                            self.stdout.write(f"    Tipo: {match.get('tipo_match')}")
                            if 'parole_comuni' in match:
                                self.stdout.write(f"    Parole comuni: {match.get('parole_comuni')}")
