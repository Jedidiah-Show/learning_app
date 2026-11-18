# RUACH LMS — Release 1.1 Status (Authoritative)

**Release:** 1.1 — Learning Intelligence & Engineering Excellence
**Baseline commit:** `68b3125` (Parallel Pathways 1.0.0 + subsequent development)
**Authoritative for:** milestone completion status, verification evidence, exit decisions

> This is the single authoritative milestone-status document. `goals.md`,
> `milestones.md` and `implementation_plan.md` define intended work;
> `progress.md` records implementation history. Do not duplicate milestone
> status elsewhere. A milestone is complete only when its exit criteria are
> demonstrated with evidence.

## Status legend

- `NOT STARTED` — no work begun
- `IN PROGRESS` — work underway, exit criteria not yet demonstrated
- `BLOCKED` — cannot proceed; blocker recorded
- `EXIT REVIEW` — implementation complete, awaiting exit-criteria verification
- `COMPLETE` — exit criteria demonstrated; evidence recorded below

## Milestone board

| Milestone | Name | Priority | Status | Owner | Started | Completed |
|---|---|---|---|---|---|---|
| M0 | Security, Data Integrity and Release Baseline | Critical | IN PROGRESS | Engineering | 2026-11-18 | — |
| M1 | Canonical Curriculum and Pathway Integrity | Critical | NOT STARTED | — | — | — |
| M2 | Project Studio and ML Project Corrections | High | NOT STARTED | — | — | — |
| M3 | Practice Arena 2.1 and Assessment Integrity | High | NOT STARTED | — | — | — |
| M4 | Skill Passport and Competency Verification | Critical | NOT STARTED | — | — | — |
| M5 | AI Tutor 3.0 | High | NOT STARTED | — | — | — |
| M6 | Learning Intelligence and Adaptive Practice | Strategic | NOT STARTED | — | — | — |
| M7 | Reliability, Accessibility and Release Verification | Critical | NOT STARTED | — | — | — |

## M0 — Security, Data Integrity and Release Baseline

**Status:** IN PROGRESS
**Dependencies:** none

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M0.1 Source distribution hygiene | `scripts/export_release_source.sh`, `docs/RELEASE_ARTIFACT_POLICY.md` | DONE (verified) | `tests/test_release_export.py` passes; archive scanned clean; checksum + `MANIFEST.txt` produced; `scripts/clean_export.sh` now delegates; CI runs export verification |
| M0.2 Credential audit and rotation | `docs/SECURITY_REMEDIATION_REPORT.md` | IN PROGRESS — audit complete, rotation pending console access | Audit: no secrets ever committed to Git; local `.env`/`.env.local`/`client_secret_*.json` are untracked and git-ignored; ROTATE decisions recorded; requires Google Cloud / AI Studio / Neon / Render console actions |
| M0.3 Authorization audit | `app/services/authorization.py` + regression tests | DONE (verified) | Passport assess/invalidate/history now require privileged reviewer + distinct target learner; learner self-verification closed; `tests/test_authorization.py` + updated `tests/test_skill_passport.py` pass |
| M0.4 Release metadata | `/healthz`, `/readyz`, `/version` | DONE (verified) | `app/version.py` (APP_VERSION 1.1.0); `/healthz` liveness, `/readyz` DB readiness, `/version` release identity (no secrets); covered by `ReleaseMetadataTests` |
| M0.5 Tests | export/secret-scan/authz/metadata tests | DONE (pending full-suite result) | New: `tests/test_authorization.py`, `tests/test_release_export.py`; updated passport tests; CI secret scan strengthened with export verification step |

**M0 exit blockers:** (1) Execute ROTATE decisions in `docs/SECURITY_REMEDIATION_REPORT.md` and delete local `client_secret_*.json` copies; (2) full test suite must pass; (3) docs for backup/recovery exist (`docs/RELEASE_PROCESS.md`, `MIGRATION.md`) — a restore drill on a disposable database is scheduled under M7.1.

## M1 — Canonical Curriculum and Pathway Integrity

**Status:** NOT STARTED
**Dependencies:** M0

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| M1.1 Curriculum registry | `app/curriculum_registry.py`, `app/services/curriculum.py` | NOT STARTED | — |
| M1.2 Legacy curriculum migration | `docs/CURRICULUM_ID_MIGRATION.md`, `app/data/curriculum_legacy_mapping.json` | NOT STARTED | — |
| M1.3 Shared Foundations lesson experience | foundation catalogue/detail/progress wiring | NOT STARTED | — |
| M1.4 Independent pathway navigation | enrolment vs focus separation | NOT STARTED | — |
| M1.5 Curriculum contract tests | automated validation suite | NOT STARTED | — |

## Milestones M2–M7

Not started. See `milestones.md` for scope. M2–M4 follow M0/M1; M5 follows
M1/M3; M6 requires M1, M3, M4, M5; M7 is the release gate.

## Exit decisions

_None yet. Each milestone exit requires: tests passing, security review,
documentation updated, migration validation where applicable, and an explicit
recorded decision here._

## Known constraints and notes

- Local `.env` contains non-placeholder development credentials; it is
  git-ignored and not tracked. Rotation of any credential that ever left the
  development machine must be recorded in `docs/SECURITY_REMEDIATION_REPORT.md`.
- No reviewer role exists yet; the codebase has only `User.is_admin`. M0
  authorization fixes therefore gate sensitive assessment operations on
  `is_admin` until M4 introduces the full role model.
