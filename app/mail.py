"""Gmail API mail delivery for account recovery."""

import base64
from email.message import EmailMessage
import os


GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'


def password_reset_mail_configured():
    return all(os.environ.get(key) for key in (
        'GMAIL_SENDER_EMAIL',
        'GMAIL_REFRESH_TOKEN',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'PUBLIC_APP_URL',
    ))


def send_password_reset_email(recipient, reset_url):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not password_reset_mail_configured():
        raise RuntimeError('Password recovery email configuration is incomplete')

    sender = os.environ['GMAIL_SENDER_EMAIL']
    message = EmailMessage()
    message['To'] = recipient
    message['From'] = sender
    message['Subject'] = 'Reset your learning account password'
    message.set_content(
        'A password reset was requested for your learning account.\n\n'
        f'Use this link within 30 minutes:\n{reset_url}\n\n'
        'If you did not request this, you can ignore this email.'
    )
    credentials = Credentials(
        token=None,
        refresh_token=os.environ['GMAIL_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ['GOOGLE_CLIENT_ID'],
        client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
        scopes=[GMAIL_SEND_SCOPE],
    )
    credentials.refresh(Request())
    service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
    service.users().messages().send(
        userId='me', body={'raw': raw_message}
    ).execute()
