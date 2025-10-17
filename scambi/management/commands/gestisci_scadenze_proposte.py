"""
Comando per gestire scadenze e reminder delle proposte catene
Esegui con: python manage.py gestisci_scadenze_proposte
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from scambi.models import PropostaCatena
from scambi.notifications import notifica_reminder_scadenza, notifica_proposta_scaduta


class Command(BaseCommand):
    help = 'Gestisce le scadenze delle proposte catene: invia reminder e annulla proposte scadute'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🕐 Inizio controllo scadenze proposte catene...'))

        # 1. Invia reminder per proposte che scadono tra <= 1 giorno
        proposte_reminder = PropostaCatena.objects.filter(
            stato='in_attesa',
            reminder_inviato=False,
            data_scadenza__isnull=False
        )

        count_reminder = 0
        for proposta in proposte_reminder:
            if proposta.necessita_reminder():
                utenti = proposta.get_utenti_coinvolti()
                for utente in utenti:
                    # Invia solo agli utenti che non hanno ancora risposto
                    try:
                        risposta = proposta.risposte.get(utente=utente)
                        if risposta.risposta == 'in_attesa':
                            notifica_reminder_scadenza(utente, proposta)
                    except:
                        pass

                proposta.reminder_inviato = True
                proposta.save()
                count_reminder += 1
                giorni = proposta.giorni_alla_scadenza()
                self.stdout.write(
                    f'  📧 Reminder inviato per proposta {proposta.id} (scade tra {giorni} giorni)'
                )

        # 2. Annulla proposte scadute
        proposte_scadute = PropostaCatena.objects.filter(
            stato='in_attesa',
            data_scadenza__isnull=False
        )

        count_scadute = 0
        for proposta in proposte_scadute:
            if proposta.is_scaduta():
                utenti = proposta.get_utenti_coinvolti()
                for utente in utenti:
                    notifica_proposta_scaduta(utente, proposta)

                proposta.stato = 'annullata'
                proposta.save()
                count_scadute += 1
                self.stdout.write(
                    self.style.WARNING(f'  ⏰ Proposta {proposta.id} annullata (scaduta)')
                )

        # Riepilogo
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Controllo completato:\n'
                f'  - {count_reminder} reminder inviati\n'
                f'  - {count_scadute} proposte annullate (scadute)'
            )
        )
