import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site

def generate_verification_token():
    """Genera un token unico per la verifica email"""
    return str(uuid.uuid4())

def send_verification_email(request, user, user_profile):
    """Invia email di verifica all'utente"""
    # Genera token di verifica
    token = generate_verification_token()
    user_profile.email_verification_token = token
    user_profile.save()

    # Crea URL di verifica
    current_site = get_current_site(request)
    protocol = 'https' if request.is_secure() else 'http'
    verification_url = f"{protocol}://{current_site.domain}{reverse('verify_email', args=[token])}"

    # Contenuto email
    subject = 'Verifica il tuo account - Sito di Scambi'
    message = f"""
Ciao {user.username}!

Grazie per esserti registrato sul nostro sito di scambi.

Per completare la registrazione e iniziare a pubblicare annunci,
clicca sul link qui sotto per verificare il tuo indirizzo email:

{verification_url}

Se non hai richiesto questa registrazione, ignora questa email.

Benvenuto nella community degli scambi!
    """

    try:
        print(f"🔧 Debug Email - Tentativo invio a: {user.email}")
        print(f"🔧 Email Backend: {settings.EMAIL_BACKEND}")
        print(f"🔧 Email Host: {getattr(settings, 'EMAIL_HOST', 'Non configurato')}")
        print(f"🔧 API Key presente: {'Sì' if settings.EMAIL_HOST_PASSWORD else 'No'}")

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@scambi.com',
            [user.email],
            fail_silently=False,
        )
        print(f"✅ Email inviata con successo a {user.email}")
        return True
    except Exception as e:
        print(f"❌ Errore invio email: {e}")
        print(f"❌ Tipo errore: {type(e).__name__}")
        return False