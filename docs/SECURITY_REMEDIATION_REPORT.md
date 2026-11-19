# RUACH LMS — Security Remediation Report (M0.2)

**Date:** 2026-11-18
**Scope:** Local development workspace and release-source distribution path
**Method:** Non-destructive audit. No secret values were printed, logged or
transmitted during the audit. Git history was searched for committed secrets.

## Summary

| Finding | Severity | Status |
|---|---|---|
| Local `.env` contains non-placeholder credentials | High (if machine/files are shared) | Documented — rotation decisions below |
| Local `.env.local` contains a Vercel OIDC token | Medium | Documented — token expires; rotate on suspicion |
| Google OAuth client secret files present (2 copies) | High (if distributed) | Documented — excluded from export; delete after rotation |
| Secrets committed to Git history | — | **None found** (only `.env.example`) |
| Release archive leakage path | — | **Closed** (`scripts/export_release_source.sh` + artifact policy) |
| Learner self-verification of Skill Passport evidence | Critical (authorization) | **Fixed** (see M0.3) |
| Passport assess/invalidate endpoints had no role check | Critical (authorization) | **Fixed** (see M0.3) |

## Audit of local credential files

### `.env` (untracked, git-ignored — never committed)

Non-placeholder values present (names only, no values):

- `SECRET_KEY` (64 chars) — Flask session signing key
- `GEMINI_API_KEY` — Google AI Studio API key
- `ADMIN_API_TOKEN` — administrative API token
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google OAuth web client
- `DATABASE_URL` — Postgres (Neon) connection string with credentials

### `.env.local` (untracked, git-ignored)

- `VERCEL_OIDC_TOKEN` — short-lived OIDC token issued for Vercel deployments

### Google OAuth client secrets (untracked, git-ignored)

Two copies of a web OAuth client secret JSON for project
`736875030044-dlo0bifn1l0i3plbkhsivqgt6lfuc6js`:

- `client_secret_736875030044-dlo0bifn1l0i3plbkhsivqgt6lfuc6js.apps.googleusercontent.com.json`
- `client_secret_2_736875030044-dlo0bifn1l0i3plbkhsivqgt6lfuc6js.apps.googleusercontent.com.json`

### Git history

`git log --all -- .env .env.local 'client_secret_*.json'` and an object-path
scan returned no matches: no credential file was ever committed. Only
`.env.example` (placeholder-only) is tracked.

## Rotation decisions

Rotation requires access to the issuing consoles (Google Cloud, Google AI
Studio, Neon, Vercel, Render), which is outside this workspace. Each item
below records the decision; **owners must execute and tick these off before
the 1.1 release ships**. None of these files are in the distributable archive
(see policy), so source distribution alone does not force rotation — but any
of these files leaving the development machine does.

| Credential | Exposure assessment | Decision | Verification |
|---|---|---|---|
| Google OAuth client secret | Local files only; never committed | **ROTATED (owner-confirmed 2026-11-19); local copies deleted 2026-11-19** | New secret set in Render/Vercel env; old secret deleted in Google Cloud Console; local copies removed |
| `GEMINI_API_KEY` | Local file only | **ROTATED (owner-confirmed 2026-11-19)** | New key works; old key revoked in AI Studio |
| `DATABASE_URL` (Neon) | Local file only | **ROTATED (owner-confirmed 2026-11-19)** | App connects with new URL; old password rejected |
| `ADMIN_API_TOKEN` | Local file only | **ROTATED (owner-confirmed 2026-11-19)** | Admin endpoints accept new token only |
| `SECRET_KEY` | Local file only | **ROTATED (owner-confirmed 2026-11-19)** | Re-login required post-rotation |
| `TOKEN_ENCRYPTION_KEY` | Not present in local env (placeholder in example) | Verify it exists in production env and is stable | Credential decryption still works after any rotation |
| `VERCEL_OIDC_TOKEN` | Short-lived by design | **No action** unless Vercel reports anomaly; do not commit | Token expiry unaffected |
| Signing keys (`docs/CREDENTIAL_SIGNING.md`) | Generated via `scripts/generate_credential_keypair.py`; not found in repo | Confirm private keys are stored only in production secret store | JWKS endpoint serves public key only |

## Hardcoded secrets scan

- Application source greps clean of private-key blocks and common token
  prefixes outside of test fixtures and placeholder documentation.
- `.env.example` contains placeholders only.
- Secret scanning is enforced in CI via `scripts/export_release_source.sh`
  (fail-closed path + content scan) and must be added as a required CI check
  (tracked in M0.5 / M7).

## Verification that no learner can modify another learner's records

See M0.3 audit below and `tests/test_authorization.py`. Summary:

- Passport evidence assessment now requires a privileged reviewer and a
  distinct target learner (`app/services/authorization.py`).
- Admin-portal actions already require `is_admin` and are covered by
  `tests/test_admin_portal.py`.

## Outstanding physical actions — ALL CLOSED 2026-11-19

Owner confirmed credential rotation is complete. The two local `client_secret_*.json` copies were deleted on 2026-11-19. A tracked-file secret sweep (GOCSPX-style OAuth secrets, private keys, `sk_live_*`, `xox[baprs]-`) returns clean. `.env.local` retains only a short-lived Vercel OIDC token (expires naturally). Backup/restore drill verified on a disposable DB (see MIGRATION.md appendix).

1. Execute the ROTATE decisions above in the issuing consoles.
2. Delete the two local `client_secret_*.json` copies after rotation.
3. Confirm production (Render/Vercel) env holds the rotated values.
4. Confirm token/key material is absent from any external archive previously
   shared; if such an archive was shared, rotation is mandatory, not optional.
