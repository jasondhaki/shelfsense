"""Sign-up verification email over SMTP (stdlib smtplib; Gmail with an app password in prod).
No SMTP configured: in dev the code is logged so sign-up still works offline (CLAUDE.md rule 4);
in prod email sign-up reports itself unavailable and guests carry on."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import Settings

log = logging.getLogger(__name__)


class MailUnavailable(Exception):
    pass


def send_code(to: str, code: str, s: Settings) -> None:
    if not s.email_ready:
        if s.app_env == "prod":
            raise MailUnavailable("email is not configured")
        log.warning("SMTP not configured (dev): verification code for %s is %s", to, code)
        return
    msg = EmailMessage()
    msg["Subject"] = f"{code} is your ShelfSense code"
    msg["From"] = f"ShelfSense <{s.smtp_user}>"
    msg["To"] = to
    msg.set_content(
        f"Your ShelfSense verification code is {code}\n\n"
        "It expires in 15 minutes. If you didn't create a ShelfSense account, ignore this email."
    )
    try:
        with smtplib.SMTP_SSL(
            s.smtp_host, s.smtp_port, timeout=s.http_timeout_s, context=ssl.create_default_context()
        ) as smtp:
            smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as e:
        log.error("sending verification email failed: %s: %s", type(e).__name__, e)
        raise MailUnavailable(str(e)) from None
