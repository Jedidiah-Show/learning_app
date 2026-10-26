"""Normalization and validation for optional recovery phone numbers."""

import re


class PhoneError(ValueError):
    """Raised when a phone number cannot be used for account recovery."""


def normalize_phone(value):
    """Return an E.164-style phone number, or None for an empty value.

    Phone numbers are optional. When supplied they must include a country
    code so the same value can identify an account and receive an SMS.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise PhoneError('Phone number must be text.')
    trimmed = value.strip()
    if not trimmed:
        return None
    if not trimmed.startswith('+'):
        raise PhoneError('Include the country code, starting with +.')
    digits = re.sub(r'\D', '', trimmed)
    if not 8 <= len(digits) <= 15:
        raise PhoneError('Enter a valid phone number with 8 to 15 digits.')
    if digits.startswith('0'):
        raise PhoneError('Use the country code instead of a leading zero.')
    return f'+{digits}'
