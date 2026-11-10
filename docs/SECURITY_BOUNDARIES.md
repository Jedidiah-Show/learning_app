# Security Boundaries Review

## Authentication & Sessions
- Session cookies configured securely (HttpOnly, Secure in prod, SameSite=Lax)
- Session versioning enforced

## Authorization
- Admin routes protected separately
- Lesson access gated by progression

## CSRF Protection
- Global protection enabled by default
- Tokens required for mutating requests
- Tests run with production-like CSRF settings

## Project Verification
- Provider API verification where possible
- SSRF protections (host allowlists, redirect validation, private IP blocking, DNS checks)
- Strict repo/commit verification

## Secrets
- Secrets not committed
- CI hygiene checks in place
- Clean export process documented

## Known Limitations
- DNS pinning at connection time not fully implemented
- Some legacy code paths need ongoing review
