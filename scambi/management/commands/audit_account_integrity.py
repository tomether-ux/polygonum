"""Diagnostica in sola lettura per la coerenza degli account."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower
from django.utils import timezone

from scambi.models import UserProfile


class Command(BaseCommand):
    help = 'Controlla account e profili senza modificare o eliminare dati'

    def add_arguments(self, parser):
        parser.add_argument(
            '--details',
            action='store_true',
            help='Mostra ID e username degli account da verificare (mai password o token)',
        )

    def handle(self, *args, **options):
        details = options['details']
        now = timezone.now()

        missing_profiles = User.objects.filter(userprofile__isnull=True).order_by('id')
        blank_emails = User.objects.filter(email='').order_by('id')
        duplicate_groups = list(
            User.objects.exclude(email='')
            .annotate(normalized_email=Lower('email'))
            .values('normalized_email')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
            .order_by('normalized_email')
        )
        duplicate_accounts = sum(group['total'] for group in duplicate_groups)
        banned_profiles = UserProfile.objects.filter(is_banned=True).order_by('user_id')
        active_suspensions = UserProfile.objects.filter(
            suspension_until__gt=now,
        ).order_by('user_id')
        expired_suspensions = UserProfile.objects.filter(
            suspension_until__isnull=False,
            suspension_until__lte=now,
        ).order_by('user_id')

        self.stdout.write('AUDIT ACCOUNT — SOLA LETTURA (nessun dato modificato)')
        self.stdout.write(f'Utenti totali: {User.objects.count()}')
        self.stdout.write(f'Profili totali: {UserProfile.objects.count()}')
        self.stdout.write(f'Utenti senza profilo: {missing_profiles.count()}')
        self.stdout.write(f'Utenti senza email: {blank_emails.count()}')
        self.stdout.write(f'Gruppi email duplicate: {len(duplicate_groups)}')
        self.stdout.write(f'Account coinvolti in email duplicate: {duplicate_accounts}')
        self.stdout.write(f'Profili bannati: {banned_profiles.count()}')
        self.stdout.write(f'Sospensioni attive: {active_suspensions.count()}')
        self.stdout.write(f'Sospensioni scadute ancora registrate: {expired_suspensions.count()}')

        if not details:
            self.stdout.write('Usa --details per mostrare ID e username da verificare manualmente.')
            return

        self._write_users('Utenti senza profilo', missing_profiles)
        self._write_users('Utenti senza email', blank_emails)

        self.stdout.write('\nEmail duplicate (l’indirizzo non viene mostrato):')
        if not duplicate_groups:
            self.stdout.write('  nessuna')
        for index, group in enumerate(duplicate_groups, start=1):
            users = User.objects.annotate(normalized_email=Lower('email')).filter(
                normalized_email=group['normalized_email'],
            ).order_by('id')
            identifiers = ', '.join(
                f'ID {user.id} ({user.username})' for user in users
            )
            self.stdout.write(f'  gruppo {index}: {identifiers}')

        self._write_profiles('Profili bannati', banned_profiles)
        self._write_profiles('Sospensioni attive', active_suspensions)
        self._write_profiles('Sospensioni scadute', expired_suspensions)

    def _write_users(self, title, queryset):
        self.stdout.write(f'\n{title}:')
        users = list(queryset)
        if not users:
            self.stdout.write('  nessuno')
            return
        for user in users:
            self.stdout.write(f'  ID {user.id} ({user.username})')

    def _write_profiles(self, title, queryset):
        self.stdout.write(f'\n{title}:')
        profiles = list(queryset.select_related('user'))
        if not profiles:
            self.stdout.write('  nessuno')
            return
        for profile in profiles:
            self.stdout.write(f'  ID utente {profile.user_id} ({profile.user.username})')
