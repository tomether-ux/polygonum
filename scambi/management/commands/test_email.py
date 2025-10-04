from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Test email configuration and sending'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address to send test to')

    def handle(self, *args, **options):
        self.stdout.write('=== TEST EMAIL CONFIGURATION ===')

        # Check configuration
        self.stdout.write(f'EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'EMAIL_HOST: {getattr(settings, "EMAIL_HOST", "Not configured")}')
        self.stdout.write(f'EMAIL_HOST_USER: {getattr(settings, "EMAIL_HOST_USER", "Not configured")}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {getattr(settings, "DEFAULT_FROM_EMAIL", "Not configured")}')

        # Check environment
        is_render = os.environ.get('RENDER')
        sendgrid_key = os.environ.get('SENDGRID_API_KEY')

        self.stdout.write(f'RENDER environment: {is_render}')
        if sendgrid_key:
            self.stdout.write(f'SENDGRID_API_KEY: Present ({len(sendgrid_key)} chars)')
        else:
            self.stdout.write('SENDGRID_API_KEY: NOT PRESENT')

        # Test email sending
        test_email = options.get('email', 'test@example.com')

        try:
            send_mail(
                'Test Email from Polygonum',
                'This is a test email to verify SendGrid configuration.',
                settings.DEFAULT_FROM_EMAIL,
                [test_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Test email sent successfully to {test_email}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to send email: {e}'))