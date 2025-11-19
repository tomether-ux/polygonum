from django.core.management.base import BaseCommand
from scambi.models import UserProfile, Provincia

class Command(BaseCommand):
    help = 'Assegna provincia di default (Roma) agli utenti senza provincia_obj'

    def handle(self, *args, **options):
        # Ottieni provincia di Roma (default)
        try:
            roma = Provincia.objects.get(sigla='RM')
            self.stdout.write(f'Provincia default: {roma.nome} ({roma.sigla})')
        except Provincia.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Provincia Roma (RM) non trovata. Carica prima il fixture!'))
            return

        # Trova tutti i profili senza provincia_obj
        profiles_without_provincia = UserProfile.objects.filter(provincia_obj__isnull=True)
        count = profiles_without_provincia.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ Tutti gli utenti hanno già una provincia assegnata'))
            return

        self.stdout.write(f'Trovati {count} utenti senza provincia')

        # Assegna Roma come default
        updated = 0
        for profile in profiles_without_provincia:
            # Se hanno una città vecchia, usala, altrimenti lascia vuoto
            if profile.citta_old:
                profile.citta = profile.citta_old
            elif not profile.citta:
                profile.citta = 'Da aggiornare'

            profile.provincia_obj = roma
            profile.save()
            updated += 1
            self.stdout.write(f'  - {profile.user.username}: provincia → {roma.sigla}, città → "{profile.citta}"')

        self.stdout.write(self.style.SUCCESS(f'✅ {updated} utenti aggiornati con provincia di default'))
        self.stdout.write(self.style.WARNING('⚠️  Gli utenti dovranno aggiornare manualmente la loro provincia nel profilo'))
