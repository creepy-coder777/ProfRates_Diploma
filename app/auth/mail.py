"""Delivery is separate from account/token handling. No public mailbox endpoint."""
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol
import json
import smtplib
import ssl
import os
from app.config import get_settings, ROOT
from app.auth.crypto import new_token

class MailDeliveryError(RuntimeError):
    pass

class Mailer(Protocol):
    def send(self, recipient: str, purpose: str, link: str) -> None: ...

class LocalMailbox:
    def send(self, recipient, purpose, link):
        s = get_settings()
        if s.app_env != 'development' or s.mail_backend != 'local':
            raise MailDeliveryError('Local mail is disabled')
        folder = Path(s.local_mail_dir)
        if not folder.is_absolute():
            folder = ROOT / folder
        folder = folder.resolve()
        if folder.is_relative_to((ROOT / 'frontend').resolve()):
            raise MailDeliveryError('Mailbox cannot be publicly served')
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        filename = folder / (new_token() + '.json')
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({'recipient': recipient, 'purpose': purpose, ('code' if purpose == 'reset-code' else 'link'): link,
                       'delivery': 'local-test-only'}, f, ensure_ascii=False)

class SMTPMailer:
    def send(self, recipient, purpose, link):
        s = get_settings()
        msg = EmailMessage()
        msg['From'] = s.smtp_from
        msg['To'] = recipient
        msg['Subject'] = 'ProfRates: ' + ('Verify email' if purpose == 'verify' else 'Reset password')
        msg.set_content(('Your ProfRates reset code: ' + link + '\nThis code expires in 10 minutes.' if purpose == 'reset-code' else 'Open this one-time link:\n' + link) + '\nIf you did not request this, ignore this message.')
        try:
            cls = smtplib.SMTP_SSL if s.smtp_security == 'ssl' else smtplib.SMTP
            with cls(s.smtp_host, s.smtp_port, timeout=10) as client:
                if s.smtp_security == 'starttls':
                    client.starttls(context=ssl.create_default_context())
                if s.smtp_user:
                    client.login(s.smtp_user, s.smtp_password.get_secret_value())
                client.send_message(msg)
        except Exception:
            raise MailDeliveryError('Mail service unavailable') from None

def get_mailer() -> Mailer:
    s = get_settings()
    if s.mail_backend == 'local' and s.app_env == 'development':
        return LocalMailbox()
    if s.mail_backend == 'smtp' and s.smtp_host and s.smtp_from:
        return SMTPMailer()
    raise MailDeliveryError('Mail delivery is not configured')
