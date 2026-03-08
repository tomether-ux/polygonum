"""
Comando per verificare e segnalare UserProfile senza città/provincia
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from scambi.models import UserProfile, Annuncio


class Command(BaseCommand):
    help = 'Verifica quali utenti hanno profili senza città/provincia e quanti annunci sono affetti'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Disattiva gli annunci degli utenti senza luogo (non consigliato, meglio contattarli)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("\n🔍 Verifica UserProfile senza città/provincia...\n"))

        # Trova profili senza città o provincia
        profili_incompleti = UserProfile.objects.filter(
            citta__isnull=True
        ) | UserProfile.objects.filter(
            citta=''
        ) | UserProfile.objects.filter(
            provincia_obj__isnull=True
        )

        if not profili_incompleti.exists():
            self.stdout.write(self.style.SUCCESS("✅ Tutti i profili hanno città e provincia!"))
            return

        self.stdout.write(
            self.style.WARNING(
                f"⚠️  Trovati {profili_incompleti.count()} profili senza luogo completo:\n"
            )
        )

        totale_annunci_affetti = 0

        for profilo in profili_incompleti:
            user = profilo.user
            annunci_attivi = Annuncio.objects.filter(utente=user, attivo=True)

            self.stdout.write(
                self.style.WARNING(
                    f"\n👤 {user.username} (ID: {user.id})"
                )
            )
            self.stdout.write(
                f"   Email: {user.email}"
            )
            self.stdout.write(
                f"   Città: {'[VUOTO]' if not profilo.citta else profilo.citta}"
            )
            self.stdout.write(
                f"   Provincia: {'[VUOTO]' if not profilo.provincia_obj else profilo.provincia_obj.nome}"
            )
            self.stdout.write(
                f"   Annunci attivi: {annunci_attivi.count()}"
            )

            if annunci_attivi.exists():
                totale_annunci_affetti += annunci_attivi.count()
                for annuncio in annunci_attivi:
                    self.stdout.write(f"      - {annuncio.titolo} ({annuncio.tipo})")

        self.stdout.write(
            self.style.HTTP_INFO(
                f"\n📊 Riepilogo:"
                f"\n   Profili incompleti: {profili_incompleti.count()}"
                f"\n   Annunci affetti: {totale_annunci_affetti}"
            )
        )

        if options['fix']:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  ATTENZIONE: Modalità --fix non implementata."
                    "\n   Invece di disattivare annunci, è meglio:"
                    "\n   1. Contattare gli utenti via email chiedendo di completare il profilo"
                    "\n   2. Inviare una notifica in-app"
                    "\n   3. Rendere obbligatorio il completamento profilo al prossimo login"
                )
            )
        else:
            self.stdout.write(
                self.style.HTTP_INFO(
                    "\n💡 Suggerimenti:"
                    "\n   1. Contatta questi utenti via email per completare il profilo"
                    "\n   2. Aggiungi un banner nel sito per utenti senza luogo"
                    "\n   3. Il campo è già obbligatorio per nuove registrazioni ✓"
                )
            )

        self.stdout.write(self.style.SUCCESS("\n✅ Verifica completata!\n"))
