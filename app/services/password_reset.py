"""Password reset and phone verification helpers.

Extracted from auth routes to keep route handlers thin.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app, url_for

from app import db
from app.models import PasswordResetToken, PhoneVerificationCode
from app.phone import PhoneError, normalize_phone


def normalize_reset_identifier(raw_identifier):
    if not isinstance(raw_identifier, str) or not raw_identifier.strip():
        return None, None
    identifier = raw_identifier.strip()
    if '@' in identifier:
        return 'email', identifier.lower()
    try:
        return 'phone', normalize_phone(identifier)
    except PhoneError:
        return None, None


def password_reset_channels(user, identifier_kind, email_available, sms_available):
    """Choose delivery methods, preferring the identifier the learner used."""
    channels = []
    if identifier_kind == 'phone' and user.phone and sms_available:
        channels.append('sms')
    if user.email and email_available:
        channels.append('email')
    if user.phone and sms_available and 'sms' not in channels:
        channels.append('sms')
    return channels


def deliver_password_reset(user, channels, reset_url):
    """Try each configured channel and return the one that succeeded."""
    from app.mail import send_password_reset_email
    from app.sms import send_password_reset_sms

    for channel in channels:
        try:
            if channel == 'sms':
                send_password_reset_sms(user.phone, reset_url)
            else:
                send_password_reset_email(user.email, reset_url)
            return channel
        except Exception:
            current_app.logger.exception(
                'Could not send password recovery %s for user %s',
                channel, user.id,
            )
    return None


def issue_password_reset(user, identifier_kind, email_available, sms_available, *, now=None):
    """Create and deliver a reset token when no recent token exists.

    Returns True if a delivery was attempted/sent or a recent token exists (no-op),
    False if delivery failed across all channels. No-op for recent tokens returns True.
    """
    now = now or datetime.now(timezone.utc)
    recent = PasswordResetToken.query.filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.created_at >= now - timedelta(minutes=15),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).first()
    if recent:
        return True
    channels = password_reset_channels(
        user, identifier_kind, email_available, sms_available
    )
    if not channels:
        return True
    raw_token = secrets.token_urlsafe(32)
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode('utf-8')).hexdigest(),
        expires_at=now + timedelta(minutes=30),
    )
    db.session.add(token)
    db.session.commit()
    public_url = os.environ.get('PUBLIC_APP_URL', '').rstrip('/')
    reset_url = public_url + url_for('auth.reset_password', token=raw_token)
    delivered = deliver_password_reset(user, channels, reset_url)
    if not delivered:
        db.session.delete(token)
        db.session.commit()
        current_app.logger.error(
            'Password recovery failed for user %s over all '
            'configured channels %s; no reset was delivered.',
            user.id, channels,
        )
        return False
    return True


def issue_phone_verification_code(user):
    """Create and text a fresh 6-digit phone verification code for a user."""
    from app.sms import password_reset_sms_configured, send_phone_verification_sms

    if not (user.phone and password_reset_sms_configured()):
        return False
    PhoneVerificationCode.query.filter_by(
        user_id=user.id, purpose='verify_phone'
    ).delete(synchronize_session=False)
    code = f'{secrets.randbelow(1_000_000):06d}'
    db.session.add(PhoneVerificationCode(
        user_id=user.id,
        phone=user.phone,
        code_hash=hashlib.sha256(code.encode('utf-8')).hexdigest(),
        purpose='verify_phone',
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    ))
    db.session.commit()
    try:
        send_phone_verification_sms(user.phone, code)
    except Exception:
        current_app.logger.exception(
            'Could not send phone verification SMS for user %s', user.id
        )
        PhoneVerificationCode.query.filter_by(
            user_id=user.id, purpose='verify_phone'
        ).delete(synchronize_session=False)
        db.session.commit()
        return False
    return True
