from django.core.management.base import BaseCommand
from scambi.models import Annuncio, CicloScambio
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Debug di un ciclo specifico per vedere i match'

    def add_arguments(self, parser):
        parser.add_argument('ciclo_id', type=int, help='ID del ciclo da analizzare')

    def handle(self, *args, **options):
        ciclo_id = options['ciclo_id']

        try:
            ciclo = CicloScambio.objects.get(id=ciclo_id)

            self.stdout.write(f"\n=== CICLO ID {ciclo.id} ===")
            self.stdout.write(f"Users: {ciclo.users}")
            self.stdout.write(f"Lunghezza: {ciclo.lunghezza}")
            self.stdout.write(f"Valido: {ciclo.valido}")
            self.stdout.write(f"ha_match_titoli: {ciclo.dettagli.get('ha_match_titoli', 'N/A')}")
            self.stdout.write(f"punteggio_qualita: {ciclo.dettagli.get('punteggio_qualita', 'N/A')}")

            # Get usernames
            self.stdout.write(f"\n=== UTENTI ===")
            for uid in ciclo.users:
                try:
                    user = User.objects.get(id=uid)
                    self.stdout.write(f"  {uid}: {user.username}")
                except User.DoesNotExist:
                    self.stdout.write(f"  {uid}: (utente non trovato)")

            # Show matches if available
            if 'matches' in ciclo.dettagli:
                self.stdout.write(f"\n=== MATCHES ({len(ciclo.dettagli['matches'])}) ===")
                for i, match in enumerate(ciclo.dettagli['matches'], 1):
                    offre_id = match.get('offre_id')
                    cerca_id = match.get('cerca_id')
                    tipo = match.get('tipo_match', 'N/A')

                    self.stdout.write(f"\n--- Match {i} (tipo: {tipo}) ---")

                    # Get announcements
                    try:
                        offre = Annuncio.objects.get(id=offre_id)
                        cerca = Annuncio.objects.get(id=cerca_id)

                        self.stdout.write(f"OFFRE [{offre_id}]: {offre.utente.username} - {offre.titolo}")
                        self.stdout.write(f"  Categoria: {offre.categoria}")
                        self.stdout.write(f"CERCA [{cerca_id}]: {cerca.utente.username} - {cerca.titolo}")
                        self.stdout.write(f"  Categoria: {cerca.categoria}")

                        if 'parole_comuni' in match:
                            self.stdout.write(f"Parole comuni: {match['parole_comuni']}")
                    except Annuncio.DoesNotExist:
                        self.stdout.write(f"Annuncio non trovato (offre={offre_id}, cerca={cerca_id})")
            else:
                self.stdout.write(f"\n⚠️ Nessun dettaglio matches disponibile")

        except CicloScambio.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Ciclo {ciclo_id} non trovato"))
