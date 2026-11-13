# Verifiable Credentials — Ed25519 Signing & Key Management

**Verified (2026-11-13):** implemented in `app/services/w3c_credentials.py`, routes in `app/routes/credentials.py` and `app/routes/ml_specialization.py`, generator `scripts/generate_credential_keypair.py`. Tests: `tests/test_w3c_credentials.py`.

RUACH course and ML specialization credentials are issued as W3C Verifiable
Credential documents (data model v1) signed with Ed25519 (`Ed25519Signature2020`
over the JCS-canonical document without the `proof` block). Any verifier can
check the proof offline; revocation state lives behind a public status endpoint.

## Components

- **Private key** — signs credentials; only the server ever holds it.
  Base64 of the 32 raw bytes in `CREDENTIAL_ED25519_PRIVATE_KEY_B64`.
- **Public key** — published at `/.well-known/jwks.json`
  (`kty: OKP, crv: Ed25519, kid: ed25519-1`), cacheable.
- **Verification endpoints**
  - Offline: check the proof against the JWKS document.
  - Online: `POST /api/credentials/verify-vc` with the credential JSON as body.
  - Revocation: `GET /api/credentials/<public_id>/status` (course) and
    `GET /specializations/machine-learning/credentials/<public_id>/status` (ML).

## One-time setup (production)

1. Generate the keypair locally:

   ```sh
   .venv/bin/python scripts/generate_credential_keypair.py
   ```

2. Set both printed variables in the hosting environment (Render:
   `render.yaml` already declares them with `sync: false`; Vercel: project
   settings). Redeploy.
3. Confirm `GET /.well-known/jwks.json` serves the public key.
4. Issue a test credential, then call `POST /api/credentials/verify-vc` with
   the downloaded document; it must return `{"valid": true, ...}`.

## Local development and CI

Set `CREDENTIAL_ED25519_PRIVATE_KEY_B64` / `CREDENTIAL_ED25519_PUBLIC_KEY_B64`
in the environment, or let `tests/test_w3c_credentials.py` use its generated
throwaway keypair. Without a configured key the VC download endpoints answer
503 with a clear error; issuing (the existing flow) is unaffected.

## Revocation model

The signed proof only vouches for issuance. Verifiers that need freshness
must check the status endpoint. Credentials can be revoked in the database;
`/api/credentials/<id>/status` then reports `{"status": "revoked"}`. Revoked
credentials are refused at export (`409`) — a learner whose credential is
revoked cannot re-download or re-share it as a current credential.

## Key rotation (documented limitation)

Rotating the signing key invalidates verification of previously issued VCs
unless both public keys are published. The current JWKS serves only the
active key; to rotate safely either (a) keep the old public key in JWKS with
a new `kid` (requires a code change), or (b) accept that credentials signed
before rotation stop verifying offline (HMAC verify links are unaffected).
Rotation is therefore deliberately rare and should be planned as a small
maintenance window.

## Signature algorithm notes for verifiers

`proof.proofValue` is base64url (no padding) of a 64-byte Ed25519 signature
over the UTF-8 bytes of `json.dumps(document_without_proof, sort_keys=True,
separators=(',', ':'), ensure_ascii=False, allow_nan=False)`. There is no
canonicalization library requirement — re-serializing with the same rules
reproduces the signed bytes.
