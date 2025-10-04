from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from scambi.models import UserProfile
from scambi.email_utils import send_verification_email_with_timeout
from django.test import RequestFactory

class Command(BaseCommand):
    help = 'Send verification email to a specific user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Username to send verification email to')

    def handle(self, *args, **options):
        username = options['username']

        try:
            user = User.objects.get(username=username)
            profile = UserProfile.objects.get(user=user)

            self.stdout.write(f'Found user: {user.username} ({user.email})')
            self.stdout.write(f'Profile: {profile.citta}, {profile.provincia}')
            self.stdout.write(f'Email verified: {profile.email_verified}')

            # Create fake request
            factory = RequestFactory()
            request = factory.get('/')
            request.META['HTTP_HOST'] = 'polygonum.onrender.com'

            self.stdout.write('\n=== SENDING VERIFICATION EMAIL ===')

            # Send verification email with timeout
            result = send_verification_email_with_timeout(request, user, profile, timeout_seconds=10)

            if result['success']:
                self.stdout.write(self.style.SUCCESS(f'✅ Verification email sent successfully to {user.email}'))
            elif result['message'] == 'timeout':
                self.stdout.write(self.style.WARNING(f'⏰ Email sending timed out after 10 seconds'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Failed to send email: {result.get("error", "Unknown error")}'))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User "{username}" not found'))
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ UserProfile not found for user "{username}"'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())