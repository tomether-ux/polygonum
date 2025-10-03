"""
Utility per gestire le notifiche del sistema Polygonum
"""
from django.contrib.auth.models import User
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
        url_azione=f"/annunci/{annuncio.id}/"
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
        url_azione="/catene-scambio/"
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
        url_azione=f"/proposte-scambio/{proposta.id}/"
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
        url_azione="/crea-annuncio/"
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