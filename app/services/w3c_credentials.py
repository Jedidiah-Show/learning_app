"""W3C Verifiable Credentials for RUACH course and specialization credentials.

Builds and verifies tamper-proof credential documents using Ed25519 digital
signatures. The server holds the Ed25519 private key (base64 in
``CREDENTIAL_ED25519_PRIVATE_KEY_B64``); the matching public key is published
at ``/.well-known/jwks.json`` so any verifier can check the proof offline or
via ``POST /api/credentials/verify-vc``.

Issuance/rendering of the legacy HMAC verify URLs is unaffected; this service
adds an exportable W3C Verifiable Credential document on top of the same
``credential`` rows.

Proof format: ``Ed25519Signature2020`` over the JCS-style canonical form
(sorted keys, minimal separators, UTF-8) of the credential document with the
``proof`` block removed. This is deliberately documented here so external
verifiers can reproduce the exact bytes that were signed.
"""

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Tuple


W3C_CONTEXT = 'https://www.w3.org/2018/credentials/v1'
SECURITY_CONTEXT = 'https://w3id.org/security/suites/ed25519-2020/v1'
PROOF_TYPE = 'Ed25519Signature2020'
PROOF_PURPOSE = 'assertionMethod'
KEY_ID = 'ed25519-1'

COURSE_CREDENTIAL_TYPE = 'RUACHCourseCredential'
SPECIALIZATION_CREDENTIAL_TYPE = 'RUACHSpecializationCredential'


class W3CCredentialError(RuntimeError):
    """Raised when credential signing material is missing or malformed."""


def _b64_decode(value: str, name: str) -> bytes:
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception as error:
        raise W3CCredentialError(f'{name} is not valid base64') from error
    if len(raw) != 32:
        raise W3CCredentialError(f'{name} must be exactly 32 bytes, got {len(raw)}')
    return raw


def signing_key_bytes(env: Dict[str, str] | None = None) -> bytes:
    env = env if env is not None else os.environ
    raw = env.get('CREDENTIAL_ED25519_PRIVATE_KEY_B64', '').strip()
    if not raw:
        raise W3CCredentialError(
            'CREDENTIAL_ED25519_PRIVATE_KEY_B64 is not configured. '
            'Generate one with scripts/generate_credential_keypair.py and set it in the environment.'
        )
    return _b64_decode(raw, 'CREDENTIAL_ED25519_PRIVATE_KEY_B64')


def private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.from_private_bytes(signing_key_bytes())


def public_key_bytes(env: Dict[str, str] | None = None) -> bytes:
    env = env if env is not None else os.environ
    raw = env.get('CREDENTIAL_ED25519_PUBLIC_KEY_B64', '').strip()
    if raw:
        return _b64_decode(raw, 'CREDENTIAL_ED25519_PUBLIC_KEY_B64')
    from cryptography.hazmat.primitives import serialization

    return private_key().public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def jwks() -> Dict[str, Any]:
    """Public verification key, published at /.well-known/jwks.json."""
    return {
        'keys': [{
            'kty': 'OKP',
            'crv': 'Ed25519',
            'kid': KEY_ID,
            'use': 'sig',
            'x': base64.urlsafe_b64encode(public_key_bytes()).rstrip(b'=').decode('ascii'),
        }],
    }


def _canonical_bytes(document: Dict[str, Any]) -> bytes:
    """Deterministic serialization of the document for signing/verifying."""
    return json.dumps(
        document, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False,
    ).encode('utf-8')


def _proof_block(issuer: str, created: str, signature: bytes) -> Dict[str, Any]:
    return {
        'type': PROOF_TYPE,
        'created': created,
        'proofPurpose': PROOF_PURPOSE,
        'verificationMethod': f'{issuer}/.well-known/jwks.json#{KEY_ID}',
        'proofValue': base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii'),
    }


def issuance_timestamp(value) -> str:
    return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def build_unsigned_vc(
    *,
    public_id: str,
    recipient_name: str,
    credential_type: str,
    credential_title: str,
    issued_at,
    issuer: str,
    status_url: str | None = None,
) -> Dict[str, Any]:
    issuer = issuer.rstrip('/')
    status = status_url or f'{issuer}/api/credentials/{public_id}/status'
    return {
        '@context': [W3C_CONTEXT, SECURITY_CONTEXT],
        'type': ['VerifiableCredential', credential_type],
        'id': f'{issuer}/credentials/{public_id}',
        'issuer': {
            'id': issuer,
            'name': 'RUACH AI & ML Engineering',
        },
        'issuanceDate': issuance_timestamp(issued_at),
        'validFrom': issuance_timestamp(issued_at),
        'credentialSubject': {
            'id': f'urn:ruach:user:{public_id}',
            'name': recipient_name,
            'credential': {
                'title': credential_title,
            },
        },
        'credentialStatus': {
            'id': status,
            'type': 'SimpleCredentialStatus2020',
        },
    }


def sign_vc(unsigned: Dict[str, Any], issuer: str) -> Dict[str, Any]:
    signature = private_key().sign(_canonical_bytes(unsigned))
    created = issuance_timestamp(datetime.now(timezone.utc))
    vc = dict(unsigned)
    vc['proof'] = _proof_block(issuer.rstrip('/'), created, signature)
    return vc


def verify_vc(vc: Dict[str, Any], *, public_key: bytes | None = None) -> Tuple[bool, str]:
    """Verify a VC document's Ed25519 proof against its payload.

    Returns (True, 'ok') when valid; otherwise (False, reason).
    """
    if not isinstance(vc, dict):
        return False, 'Credential is not a JSON object'
    proof = vc.get('proof')
    if not isinstance(proof, dict):
        return False, 'Credential has no proof block'
    if proof.get('type') != PROOF_TYPE:
        return False, f"Unsupported proof type {proof.get('type')!r}"
    proof_value = proof.get('proofValue')
    if not isinstance(proof_value, str) or not proof_value.strip():
        return False, 'Proof has no signature value'
    unsigned = {key: value for key, value in vc.items() if key != 'proof'}
    try:
        signature = base64.urlsafe_b64decode(proof_value + '=' * (-len(proof_value) % 4))
    except Exception:
        return False, 'Proof signature is not valid base64url'
    key_bytes = public_key if public_key is not None else public_key_bytes()
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(
            signature, _canonical_bytes(unsigned),
        )
    except Exception:
        return False, 'Signature verification failed'
    return True, 'ok'


def vc_for_course_credential(credential, issuer: str) -> Dict[str, Any]:
    if credential.revoked_at is not None:
        raise W3CCredentialError('A revoked credential cannot be re-issued or exported')
    unsigned = build_unsigned_vc(
        public_id=credential.public_id,
        recipient_name=credential.recipient_name,
        credential_type=COURSE_CREDENTIAL_TYPE,
        credential_title=credential.course_title,
        issued_at=credential.issued_at,
        issuer=issuer,
    )
    return sign_vc(unsigned, issuer)


def vc_for_specialization_credential(credential, issuer: str, credential_title: str) -> Dict[str, Any]:
    if credential.revoked_at is not None:
        raise W3CCredentialError('A revoked credential cannot be re-issued or exported')
    status_url = (
        f'{issuer.rstrip("/")}/specializations/machine-learning/'
        f'credentials/{credential.public_id}/status'
    )
    unsigned = build_unsigned_vc(
        public_id=credential.public_id,
        recipient_name=credential.recipient_name,
        credential_type=SPECIALIZATION_CREDENTIAL_TYPE,
        credential_title=credential_title,
        issued_at=credential.issued_at,
        issuer=issuer,
        status_url=status_url,
    )
    return sign_vc(unsigned, issuer)
