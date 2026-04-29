import logging
import os
import resend

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str) -> dict:
    """Invia una email tramite Resend API.

    Args:
        to: Indirizzo email destinatario
        subject: Oggetto della email
        html: Corpo della email in HTML

    Returns:
        Dizionario con l'id del messaggio inviato

    Raises:
        Exception: In caso di errore nell'invio
    """
    api_key = os.environ.get("RESEND_API_KEY")
    email_from = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")

    if not api_key:
        raise ValueError("RESEND_API_KEY non configurata nelle variabili d'ambiente")

    resend.api_key = api_key

    params = {
        "from": email_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    try:
        response = resend.Emails.send(params)
        logger.info(f"Email inviata a {to} — id: {response.get('id')}")
        return response
    except Exception as e:
        logger.error(f"Errore invio email a {to}: {e}")
        raise
