import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.core.signing import TimestampSigner

logger = logging.getLogger(__name__)

def generate_verification_token(user_id):
    """
    Genera un token firmato con timestamp per la verifica email
    SECURITY: Token include timestamp, scadenza verificata in verify_email (48h)
    """
    signer = TimestampSigner(salt='email-verification')
    return signer.sign(str(user_id))

def _send_mail_task(subject, message, from_email, recipient_list):
    """Task interno per invio email (eseguito in thread separato)"""
    return send_mail(subject, message, from_email, recipient_list, fail_silently=False)

def send_verification_email_with_timeout(request, user, user_profile, timeout_seconds=30):
    """
    Invia email di verifica con timeout gestito via ThreadPoolExecutor
    SECURITY: Usa concurrent.futures invece di signal.alarm() per compatibilità Gunicorn
    """
    # Genera token di verifica con timestamp (SECURITY: scade dopo 48h)
    token = generate_verification_token(user.id)
    user_profile.email_verification_token = token
    user_profile.save()

    # SECURITY: Usa SITE_URL da settings invece di current_site.domain (previene Host header injection)
    protocol = 'https' if request.is_secure() else 'http'
    site_url = getattr(settings, 'SITE_URL', f"{protocol}://{request.get_host()}")
    # Rimuovi protocollo da SITE_URL se presente
    site_url = site_url.replace('https://', '').replace('http://', '')
    verification_url = f"{protocol}://{site_url}{reverse('verify_email', args=[token])}"

    # Contenuto email
    subject = 'Verifica il tuo account - Polygonum'
    message = f"""
Ciao {user.username}!

Grazie per esserti registrato su Polygonum, il nostro sito di scambi.

Per completare la registrazione e iniziare a pubblicare annunci,
clicca sul link qui sotto per verificare il tuo indirizzo email:

{verification_url}

Se non hai richiesto questa registrazione, ignora questa email.

Benvenuto nella community degli scambi!
    """

    from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@polygonum.com'

    try:
        logger.info(
            "Sending verification email user_id=%s timeout_seconds=%s",
            user.id,
            timeout_seconds,
        )

        # SECURITY: Usa ThreadPoolExecutor con timeout invece di signal.alarm()
        # Funziona correttamente con Gunicorn multi-worker
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_send_mail_task, subject, message, from_email, [user.email])
            future.result(timeout=timeout_seconds)

        logger.info("Verification email sent user_id=%s", user.id)
        return {"success": True, "message": "Email inviata"}

    except FuturesTimeoutError:
        logger.warning(
            "Verification email timeout user_id=%s timeout_seconds=%s",
            user.id,
            timeout_seconds,
        )
        return {"success": False, "message": "timeout", "error": "Email delivery timeout"}

    except Exception as exc:
        logger.error(
            "Verification email failed user_id=%s error_type=%s",
            user.id,
            type(exc).__name__,
        )
        return {"success": False, "message": "error", "error": "Email delivery failed"}

def send_verification_email(request, user, user_profile):
    """Wrapper per backward compatibility"""
    result = send_verification_email_with_timeout(request, user, user_profile)
    return result["success"]
