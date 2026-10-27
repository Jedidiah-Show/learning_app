"""Twilio SMS delivery for optional phone-based account recovery."""

import os

import requests


TWILIO_API_BASE = 'https://api.twilio.com/2010-04-01'
TWILIO_TIMEOUT_SECONDS = 10
SMS_CONFIGURATION_KEYS = (
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_FROM_NUMBER',
    'PUBLIC_APP_URL',
)


def password_reset_sms_configured():
    """Return True when Twilio and an absolute app URL are configured."""
    return all(
        isinstance(os.environ.get(key), str) and os.environ[key].strip()
        for key in SMS_CONFIGURATION_KEYS
    )


def send_password_reset_sms(recipient, reset_url):
    """Send a password reset link to a phone number through Twilio."""
    if not password_reset_sms_configured():
        raise RuntimeError('Password recovery SMS configuration is incomplete')

    account_sid = os.environ['TWILIO_ACCOUNT_SID'].strip()
    auth_token = os.environ['TWILIO_AUTH_TOKEN'].strip()
    from_number = os.environ['TWILIO_FROM_NUMBER'].strip()
    response = requests.post(
        f'{TWILIO_API_BASE}/Accounts/{account_sid}/Messages.json',
        auth=(account_sid, auth_token),
        data={
            'From': from_number,
            'To': recipient,
            'Body': (
                'RUACH password reset requested. Use this link within '
                f'30 minutes: {reset_url} If you did not request this, '
                'ignore this message.'
            ),
        },
        timeout=TWILIO_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise RuntimeError(f'Twilio returned HTTP {response.status_code}')
