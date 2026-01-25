from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.core.signing import Signer
import os


class Command(BaseCommand):
    help = 'Invia una newsletter personalizzata a tutti gli utenti registrati'

    def add_arguments(self, parser):
        parser.add_argument(
            '--oggetto',
            type=str,
            required=True,
            help='Oggetto della email'
        )
        parser.add_argument(
            '--messaggio',
            type=str,
            required=True,
            help='Corpo del messaggio (HTML supportato)'
        )
        parser.add_argument(
            '--link-cta',
            type=str,
            default='',
            help='Link per il bottone Call-To-Action (opzionale)'
        )
        parser.add_argument(
            '--testo-cta',
            type=str,
            default='Visita il sito',
            help='Testo del bottone CTA (default: "Visita il sito")'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula l\'invio senza inviare realmente le email'
        )
        parser.add_argument(
            '--solo-verificati',
            action='store_true',
            help='Invia solo agli utenti con email verificata'
        )
        parser.add_argument(
            '--test-email',
            type=str,
            help='Invia solo a questo indirizzo email per test'
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS('📧 INVIO NEWSLETTER POLYGONUM'))
        self.stdout.write("=" * 60 + "\n")

        # 1. Ottieni lista utenti
        users = self.get_users(options)

        if not users:
            self.stdout.write(self.style.ERROR("❌ Nessun utente trovato con i criteri specificati"))
            return

        # 3. Mostra riepilogo
        self.show_summary(users, options)

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - Nessuna email sarà inviata\n"))
        else:
            # Conferma prima di procedere (solo se non è test-email)
            if not options['test_email']:
                confirm = input(f"\n⚠️  Procedere con l'invio a {len(users)} utenti? (sì/no): ")
                if confirm.lower() not in ['sì', 'si', 'yes', 'y']:
                    self.stdout.write(self.style.WARNING("\n❌ Invio annullato dall'utente"))
                    return

        # 4. Invia email
        sent_count = 0
        failed_count = 0

        for user in users:
            try:
                if self.send_newsletter(user, options):
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Errore per {user.email}: {e}"))
                failed_count += 1

        # 5. Report finale
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"✅ Newsletter completata!"))
        self.stdout.write(f"  📨 Inviate: {sent_count}")
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠️  Fallite: {failed_count}"))
        self.stdout.write("=" * 60 + "\n")

    def get_users(self, options):
        """Ottiene la lista di utenti a cui inviare"""
        if options['test_email']:
            # Modalità test: solo un utente specifico
            users = User.objects.filter(email=options['test_email'])
            if not users.exists():
                self.stdout.write(self.style.ERROR(f"❌ Utente con email {options['test_email']} non trovato"))
            return users

        # Filtra utenti
        users = User.objects.filter(is_active=True)

        # Filtra solo utenti con newsletter abilitata
        users = users.filter(userprofile__newsletter_enabled=True)

        if options['solo_verificati']:
            users = users.filter(userprofile__email_verified=True)

        # Escludi utenti senza email
        users = users.exclude(email='').exclude(email__isnull=True)

        return users.order_by('username')

    def show_summary(self, users, options):
        """Mostra riepilogo prima dell'invio"""
        self.stdout.write("\n📋 Riepilogo:")
        self.stdout.write(f"  Oggetto: {options['oggetto']}")
        self.stdout.write(f"  Destinatari: {len(users)} utenti")

        if options['test_email']:
            self.stdout.write(self.style.WARNING(f"  🧪 MODALITÀ TEST - Solo a: {options['test_email']}"))

        if options['solo_verificati']:
            self.stdout.write("  ✅ Solo utenti verificati")

        if options['link_cta']:
            self.stdout.write(f"  🔗 CTA: {options['testo_cta']} → {options['link_cta']}")

        # Mostra primi 5 destinatari
        self.stdout.write(f"\n👥 Primi destinatari:")
        for user in users[:5]:
            verified = "✓" if hasattr(user, 'userprofile') and user.userprofile.email_verified else "✗"
            self.stdout.write(f"  {verified} {user.username} ({user.email})")

        if len(users) > 5:
            self.stdout.write(f"  ... e altri {len(users) - 5} utenti")

    def send_newsletter(self, user, options):
        """Invia la newsletter a un singolo utente"""
        try:
            # Genera token firmato per unsubscribe
            signer = Signer()
            unsubscribe_token = signer.sign(str(user.id))

            # URL base
            base_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://polygonum.io')
            unsubscribe_url = f"{base_url}/newsletter/unsubscribe/{unsubscribe_token}/"
            profilo_url = f"{base_url}/profilo/{user.username}/"

            # Prepara contesto per template
            context = {
                'nome_utente': user.username,
                'oggetto': options['oggetto'],
                'messaggio': options['messaggio'],
                'link_cta': options.get('link_cta', ''),
                'testo_cta': options.get('testo_cta', 'Visita il sito'),
                'unsubscribe_url': unsubscribe_url,
                'profilo_url': profilo_url,
            }

            # Renderizza template HTML
            html_content = render_to_string('scambi/emails/newsletter.html', context)

            # Versione testo semplice (fallback)
            text_content = f"""
Ciao {user.username}!

{options['messaggio']}

---
Polygonum
https://polygonum.io
            """

            # Crea email
            email = EmailMultiAlternatives(
                subject=options['oggetto'],
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")

            if not options['dry_run']:
                email.send(fail_silently=False)

            self.stdout.write(f"  ✅ {user.username} ({user.email})")
            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ {user.username} ({user.email}): {e}"))
            return False
