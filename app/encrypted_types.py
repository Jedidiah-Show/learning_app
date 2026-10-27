"""Application-level encryption for sensitive values stored in the database.

OAuth refresh tokens are long-lived bearer credentials.  Storing them as
plaintext means a database export, backup, or read-only replica is enough to
take over a learner's Google Calendar.  The :class:`EncryptedText` type keeps
the database column compatible with the existing ``Text`` schema while
encrypting values on the way in and decrypting them on the way out.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from app import db


ENCRYPTED_PREFIX = 'enc:v1:'


def _fernet_key():
    """Return a stable Fernet key for the current application.

    Production should set ``TOKEN_ENCRYPTION_KEY`` and keep it stable across
    deployments.  When it is not configured we derive a key from SECRET_KEY so
    tokens are never written in plaintext.  Rotating either value requires
    reconnecting Google Calendar, which is handled as an authorization error.
    """
    configured = current_app.config.get('TOKEN_ENCRYPTION_KEY')
    material = configured or current_app.config.get('SECRET_KEY')
    if isinstance(material, str):
        material = material.encode('utf-8')
    if not material:
        raise RuntimeError('A SECRET_KEY or TOKEN_ENCRYPTION_KEY is required')
    digest = hashlib.sha256(b'learning-app-token-encryption:' + material).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(value):
    if value is None or value == '':
        return value
    if not isinstance(value, str):
        value = str(value)
    if value.startswith(ENCRYPTED_PREFIX):
        return value
    token = Fernet(_fernet_key()).encrypt(value.encode('utf-8')).decode('ascii')
    return ENCRYPTED_PREFIX + token


def decrypt_secret(value):
    if not value or not isinstance(value, str):
        return value
    if not value.startswith(ENCRYPTED_PREFIX):
        # Existing rows were stored before encryption was introduced.  They
        # remain readable and are encrypted the next time they are written.
        return value
    try:
        return Fernet(_fernet_key()).decrypt(
            value[len(ENCRYPTED_PREFIX):].encode('ascii')
        ).decode('utf-8')
    except (InvalidToken, ValueError, TypeError):
        current_app.logger.error(
            'A stored integration token could not be decrypted; the user must '
            'reconnect the integration.'
        )
        return None


class EncryptedText(db.TypeDecorator):
    """A ``Text`` column whose values are encrypted at the application layer."""

    impl = db.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_secret(value)

    def process_result_value(self, value, dialect):
        return decrypt_secret(value)
