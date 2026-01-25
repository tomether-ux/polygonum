from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Mostra lista utenti registrati con email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Numero massimo di utenti da mostrare (default: 20)'
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS('👥 LISTA UTENTI POLYGONUM'))
        self.stdout.write("=" * 80 + "\n")

        users = User.objects.filter(is_active=True).order_by('-date_joined')[:options['limit']]

        if not users:
            self.stdout.write(self.style.ERROR("❌ Nessun utente trovato"))
            return

        self.stdout.write(f"Totale utenti attivi: {User.objects.filter(is_active=True).count()}\n")
        self.stdout.write(f"{'#':<4} {'Username':<20} {'Email':<40} {'Verificato':<12}")
        self.stdout.write("-" * 80)

        for i, user in enumerate(users, 1):
            email_verified = "✅" if hasattr(user, 'userprofile') and user.userprofile.email_verified else "❌"
            email = user.email or "(nessuna email)"

            self.stdout.write(f"{i:<4} {user.username:<20} {email:<40} {email_verified:<12}")

        if User.objects.filter(is_active=True).count() > options['limit']:
            remaining = User.objects.filter(is_active=True).count() - options['limit']
            self.stdout.write(f"\n... e altri {remaining} utenti (usa --limit per vedere di più)")

        self.stdout.write("\n" + "=" * 80 + "\n")
