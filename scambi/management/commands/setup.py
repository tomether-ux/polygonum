import os

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Optionally create an initial superuser from explicit environment variables'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        configured = [username, email, password]
        if not any(configured):
            self.stdout.write(
                self.style.WARNING(
                    'Superuser setup skipped: explicit credentials are not configured'
                )
            )
            return

        missing = [
            name for name, value in (
                ('DJANGO_SUPERUSER_USERNAME', username),
                ('DJANGO_SUPERUSER_EMAIL', email),
                ('DJANGO_SUPERUSER_PASSWORD', password),
            )
            if not value
        ]
        if missing:
            raise CommandError(
                'Incomplete superuser configuration; missing: ' + ', '.join(missing)
            )

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(
                self.style.SUCCESS('Superuser created successfully')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Superuser already exists')
            )
