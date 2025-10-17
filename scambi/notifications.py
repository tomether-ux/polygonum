"""
Utility per gestire le notifiche del sistema Polygonum
"""
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Notifica, Annuncio


def crea_notifica(utente, tipo, titolo, messaggio, annuncio_collegato=None, utente_collegato=None, url_azione=None):
    """
    Crea una nuova notifica per l'utente specificato

    Args:
        utente: User object del destinatario
        tipo: Tipo di notifica (vedi TIPO_CHOICES in models.py)
        titolo: Titolo breve della notifica
        messaggio: Messaggio dettagliato
        annuncio_collegato: Annuncio collegato (opzionale)
        utente_collegato: Utente collegato (opzionale)
        url_azione: URL per azione (opzionale)

    Returns:
        Notifica object creata
    """
    notifica = Notifica.objects.create(
        utente=utente,
        tipo=tipo,
        titolo=titolo,
        messaggio=messaggio,
        annuncio_collegato=annuncio_collegato,
        utente_collegato=utente_collegato,
        url_azione=url_azione
    )
    return notifica


def notifica_preferito_aggiunto(annuncio, utente_che_aggiunge):
    """
    Crea notifica quando qualcuno aggiunge un annuncio ai preferiti
    """
    titolo = f"❤️ Il tuo annuncio è piaciuto!"
    messaggio = f"{utente_che_aggiunge.username} ha aggiunto il tuo annuncio '{annuncio.titolo}' ai preferiti."

    return crea_notifica(
        utente=annuncio.utente,
        tipo='preferito_aggiunto',
        titolo=titolo,
        messaggio=messaggio,
        annuncio_collegato=annuncio,
        utente_collegato=utente_che_aggiunge,
        url_azione=reverse('dettaglio_annuncio', kwargs={'annuncio_id': annuncio.id})
    )


def notifica_nuova_catena(utente, numero_catene):
    """
    Crea notifica per nuove catene di scambio disponibili
    """
    titolo = f"🔗 {numero_catene} nuove catene di scambio!"
    if numero_catene == 1:
        messaggio = "È stata trovata 1 nuova catena di scambio che potrebbe interessarti."
    else:
        messaggio = f"Sono state trovate {numero_catene} nuove catene di scambio che potrebbero interessarti."

    return crea_notifica(
        utente=utente,
        tipo='nuova_catena',
        titolo=titolo,
        messaggio=messaggio,
        url_azione=reverse('catene_scambio')
    )


def notifica_proposta_scambio(proposta):
    """
    Crea notifica per nuova proposta di scambio
    """
    titolo = f"🤝 Nuova proposta di scambio!"
    messaggio = f"{proposta.richiedente.username} ti ha proposto di scambiare '{proposta.annuncio_richiesto.titolo}' con '{proposta.annuncio_offerto.titolo}'."

    return crea_notifica(
        utente=proposta.destinatario,
        tipo='proposta_scambio',
        titolo=titolo,
        messaggio=messaggio,
        annuncio_collegato=proposta.annuncio_richiesto,
        utente_collegato=proposta.richiedente,
        url_azione=reverse('dettaglio_proposta_scambio', kwargs={'proposta_id': proposta.id})
    )


def notifica_benvenuto(utente):
    """
    Crea messaggio di benvenuto per nuovi utenti
    """
    titolo = "🌱 Benvenuto su Polygonum!"
    messaggio = """Ciao e benvenuto nella nostra comunità di scambi sostenibili!

🌍 **La nostra filosofia**: Crediamo in un mondo più sostenibile dove gli oggetti trovano nuova vita attraverso lo scambio. Ogni scambio è un piccolo gesto per l'ambiente e un grande passo verso una comunità più unita.

🔄 **Come funziona**:
• Pubblica i tuoi annunci di oggetti che offri o cerchi
• Il nostro sistema trova automaticamente catene di scambio multiple
• Connettiti con altri utenti per scambi equi e sostenibili

💡 **I tuoi primi passi**:
1. Completa il tuo profilo con la tua città
2. Pubblica il tuo primo annuncio
3. Esplora le catene di scambio disponibili
4. Aggiungi annunci interessanti ai preferiti

Buon scambio! 🌱"""

    return crea_notifica(
        utente=utente,
        tipo='benvenuto',
        titolo=titolo,
        messaggio=messaggio,
        url_azione=reverse('crea_annuncio')
    )


def notifica_catena_attivata(utente, catena, utente_attivatore):
    """
    Crea notifica quando una catena di scambio viene attivata
    """
    titolo = f"🎉 Catena di scambio attivata!"
    messaggio = f"{utente_attivatore.username} ha attivato la catena '{catena.nome}'. Ora puoi coordinarti con gli altri partecipanti nella chat di gruppo per completare gli scambi."

    return crea_notifica(
        utente=utente,
        tipo='sistema',
        titolo=titolo,
        messaggio=messaggio,
        url_azione=reverse('chat_conversazione', kwargs={'conversazione_id': catena.conversazione.id}) if catena.conversazione else reverse('lista_messaggi')
    )


def notifica_nuovo_messaggio(utente, messaggio):
    """
    Crea notifica per nuovo messaggio ricevuto
    """
    conversazione = messaggio.conversazione
    mittente = messaggio.mittente

    if conversazione.tipo == 'gruppo':
        titolo = f"💬 Nuovo messaggio nel gruppo"
        messaggio_testo = f"{mittente.username} ha scritto nel gruppo '{conversazione.get_nome_display(utente)}': {messaggio.contenuto[:50]}..."
    else:
        titolo = f"💬 Nuovo messaggio da {mittente.username}"
        messaggio_testo = f"{mittente.username} ti ha scritto: {messaggio.contenuto[:50]}..."

    return crea_notifica(
        utente=utente,
        tipo='sistema',
        titolo=titolo,
        messaggio=messaggio_testo,
        utente_collegato=mittente,
        url_azione=reverse('chat_conversazione', kwargs={'conversazione_id': conversazione.id})
    )


def segna_tutte_come_lette(utente):
    """
    Segna tutte le notifiche dell'utente come lette
    """
    return Notifica.objects.filter(utente=utente, letta=False).update(letta=True)


def conta_notifiche_non_lette(utente):
    """
    Conta le notifiche non lette dell'utente
    """
    return Notifica.objects.filter(utente=utente, letta=False).count()


def ottieni_notifiche_recenti(utente, limite=10):
    """
    Ottiene le notifiche più recenti dell'utente
    """
    return Notifica.objects.filter(utente=utente).order_by('-data_creazione')[:limite]


def notifica_proposta_catena(utente, proposta, iniziatore):
    """
    Crea notifica quando qualcuno propone una catena di scambio

    Args:
        utente: Destinatario della notifica
        proposta: PropostaCatena object
        iniziatore: User che ha proposto la catena
    """
    titolo = f"🔗 {iniziatore.username} è interessato a una catena!"
    messaggio = f"{iniziatore.username} ha mostrato interesse per una catena di scambio che ti coinvolge. Rispondi per confermare il tuo interesse!"

    return crea_notifica(
        utente=utente,
        tipo='proposta_catena',
        titolo=titolo,
        messaggio=messaggio,
        utente_collegato=iniziatore,
        url_azione=reverse('catene_scambio')
    )


def notifica_risposta_proposta(utente, proposta, rispondente, interessato=True):
    """
    Crea notifica quando qualcuno risponde a una proposta di catena

    Args:
        utente: Destinatario della notifica (iniziatore)
        proposta: PropostaCatena object
        rispondente: User che ha risposto
        interessato: Boolean se l'utente è interessato o meno
    """
    if interessato:
        titolo = f"✅ {rispondente.username} è interessato!"
        messaggio = f"{rispondente.username} ha mostrato interesse per la tua proposta di catena. {proposta.get_count_interessati()}/{proposta.get_count_totale()} utenti interessati."
        tipo = 'risposta_proposta_catena'
    else:
        titolo = f"❌ {rispondente.username} non è interessato"
        messaggio = f"{rispondente.username} ha rifiutato la tua proposta di catena. La proposta è stata annullata."
        tipo = 'proposta_rifiutata'

    return crea_notifica(
        utente=utente,
        tipo=tipo,
        titolo=titolo,
        messaggio=messaggio,
        utente_collegato=rispondente,
        url_azione=reverse('catene_scambio')
    )


def notifica_tutti_interessati(utente, proposta):
    """
    Crea notifica quando tutti gli utenti sono interessati a una catena

    Args:
        utente: Destinatario della notifica
        proposta: PropostaCatena object
    """
    titolo = f"🎉 Tutti interessati alla catena!"
    messaggio = f"Tutti gli utenti hanno mostrato interesse per la catena di scambio! Verrà creata una chat di gruppo per coordinare gli scambi."

    return crea_notifica(
        utente=utente,
        tipo='tutti_interessati',
        titolo=titolo,
        messaggio=messaggio,
        url_azione=reverse('catene_scambio')
    )