# Troubleshooting Labs — Engineering Pilot Runbook (2026-11-13)

**Scope:** Pilot of Goal G5 (Safe, Practical Engineering Labs) with three
real-world debugging scenarios, shipped as Practice Arena challenges:

| Lab problem | Scenario |
| --- | --- |
| `lab-troubleshoot-vector-index` | Broken vector index & similarity drift (dimension mismatch + missing L2 normalization) |
| `lab-troubleshoot-rag-chunking` | RAG chunking & overlap misconfiguration (non-positive stride, mid-word cuts) |
| `lab-troubleshoot-docker-network` | Docker bridge network & service discovery failure (`localhost` inside containers) |

## What a lab is

A lab is a buggy-baseline Python challenge (`lab: true` in
`app/data/arena_problems.json`). The learner must:

1. **Diagnose** the failure described in the statement,
2. **Fix** the code (judged deterministically by the hidden `judge_tests`
   suite via the containerized judge — the browser never sees the suite),
3. **Verify** the fix,
4. **Debrief**: submit a short diagnosis + verification write-up, rubric-scored
   against *Diagnosis*, *Verification*, and *Clarity* (0–100 each).

A lab debrief is only available **after a judged ACCEPTED verdict**. Passing
(score ≥ 70 with every criterion ≥ 50) records **LAB evidence** in the Skill
Passport for the lab's skills (`rag`, `vector-databases`, `embeddings`,
`debugging` or `docker`, `deployment`, `networking`, `debugging`).

## Evidence semantics

Evidence types carry a strength rank and are never downgraded:
`LESSON (1) < PROBLEM (2) < LAB (3) < PROJECT (4)`. The judge records
`PROBLEM` evidence on ACCEPTED verdicts; passing a lab debrief upgrades the
same skills to `LAB`. Evidence is stored in `UserSkillProgress` with
`evidence_type='LAB'` and `evidence_id=<problem_id>`.

## Data and API

- Table `lab_debrief` (migration `6e8f0b2d4a51`): one row per (user, lab).
  Stores diagnosis, verification, score, criterion feedback (JSON),
  evaluation source (`ai`/`local`), and pass/fail.
- `GET /arena/api/problems/<id>/debrief` — returns the learner's stored
  debrief or `null`.
- `POST /arena/api/problems/<id>/debrief` — evaluates via the configured AI
  provider (`use_cache=True`); on AI outage the write-up is stored as
  `evaluation_source='local'` and can be re-scored on retry. Invalid AI
  payloads return 503 and store nothing.

## Constraints honoured

- No host shell access; judging stays inside the existing isolated sandbox.
- Scenarios are deterministic, resettable (Reset button), and versioned in
  git with dedicated hidden test suites verified against the reference
  solutions.
- Rubric scoring treats the learner write-up as untrusted data.
- Lab evidence maps to existing Skill Passport nodes; no new credentials are
  issued by the pilot.

## Verification record (2026-11-13)

- Hidden suites pass against reference solutions (all 88 published
  challenges; 62 lesson exercises + 23 arena problems newly authored).
- `tests/test_lab_debrief.py` covers gating, validation, AI pass/fail,
  outage fallback, invalid-payload 503, LAB evidence award, and
  evidence-type no-downgrade.
