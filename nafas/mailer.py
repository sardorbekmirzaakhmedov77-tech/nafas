import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger(__name__)


def send_email(to, subject, text, html=None):
    """Send via SMTP when configured; otherwise print to the log (dev mode)."""
    cfg = current_app.config
    msg = EmailMessage()
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    if not cfg.get("MAIL_SERVER"):
        log.info("Email (not sent, MAIL_SERVER unset) to=%s subject=%r\n%s", to, subject, text)
        return False

    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=20) as smtp:
        smtp.starttls()
        if cfg.get("MAIL_USERNAME"):
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        smtp.send_message(msg)
    return True
