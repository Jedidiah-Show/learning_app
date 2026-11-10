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
- GitHub Actions runs are verified through the GitHub API only
- The submitted repository and full commit SHA must match the completed, successful run
- Unsupported CI providers, missing API identity, and API errors fail closed
- API redirects are restricted to HTTPS on `api.github.com`; verification does not fetch caller-selected URLs

## Secrets
- Secrets not committed
- CI hygiene checks in place
- Clean export process documented

## Known Limitations
- Only GitHub Actions is supported for automated project verification
- Outbound network policy and secret-history/credential rotation reviews remain operational responsibilities
- Browser, accessibility, and learner validation remain necessary for release acceptance
