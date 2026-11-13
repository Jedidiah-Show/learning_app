#!/usr/bin/env python3
"""Generate the Ed25519 keypair used to sign W3C verifiable credentials.

Run locally or in CI, then set the two printed environment variables on the
hosting platform (Render/Vercel) and in CI if credentials are issued there.

Usage:

    .venv/bin/python scripts/generate_credential_keypair.py

The private key must never be committed or logged; it signs credentials.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main():
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    print('CREDENTIAL_ED25519_PRIVATE_KEY_B64=' + base64.b64encode(private_bytes).decode())
    print('CREDENTIAL_ED25519_PUBLIC_KEY_B64=' + base64.b64encode(public_bytes).decode())
    print()
    print('Set both on the hosting platform. The public key is also published')
    print('at /.well-known/jwks.json for offline verifiers.')


if __name__ == '__main__':
    main()
