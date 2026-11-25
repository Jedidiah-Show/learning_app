# Interface Contracts (Draft)

Versioned contracts for internal/external boundaries. Changes should be additive when possible; breaking changes require version bumps and migration notes.

## 1. GitHub Webhook Verification Contract

**Endpoint:** `POST /api/webhooks/github` (`app/routes/projects.py:github_webhook`)

**Auth/Integrity:**
- `X-Hub-Signature-256` HMAC-SHA256 over raw request body using `GITHUB_WEBHOOK_SECRET`.
- Fail closed when secret is unconfigured (`503`).
- Invalid signature -> `401`.

**Accepted events:**
- `check_run` / `workflow_run` with `action=completed` and successful conclusion as defined by verification service.
- Push events never verify projects by themselves.

**Verification rules:**
- Match learner submission by repository + exact recorded `commit_sha`.
- Only verified successful CI on allowlisted hosts/providers counts.
- Idempotent: repeated valid events should not create duplicate completion side effects.

**Response shape:**
```json
{"status": "ignored|processed|verified", "reason": "...", "project_id": 123}
```
(Exact fields may evolve; keep backward-compatible keys.)

## 2. AI Prompt/Output Contracts

**Gateway:** `app/ai/gateway.py` + `app/gemini.py` / `app/openrouter.py`

**Request contract:**
- `task_type`: stable identifier (e.g., `project_brief`, `project_review`, `tutor_response`).
- `prompt_version`: from `app/ai/prompts/registry.py`; bump on prompt/output contract change.
- `model_tier`: `flash|pro`.
- `use_cache`: bool; cache keys must include normalized prompt, model tier, task/prompt version as applicable.

**Output contract:**
- JSON-only responses for structured tasks.
- Validate schema before persistence or state transitions.
- Reject malformed/empty/truncated/blocked responses as provider errors, not success.

**Project review output (critical):**
```json
{
  "score": 0-100|null,
  "summary": "string",
  "strengths": ["string"],
  "gaps": ["string"],
  "next_steps": ["string"],
  "criterion_feedback": [
    {"criterion": "exact rubric criterion", "score": 0-100, "evidence": "string", "gap": "string"}
  ]
}
```
Validation: every rubric criterion scored, evidence/gap present, bounded lengths, no invented execution claims.

## 3. Project Verification Contract

**Service:** `app/project_verification.py`

**Inputs:**
- `repository_url` (public HTTPS)
- `checks_url` (public HTTPS checks/run URL, when used)
- `commit_sha` (full SHA)
- optional `branch`

**Output:**
```json
{"verified": true|false, "commit_sha": "...", "provider": "...", "pending": "github_webhook|..."}
```

**Rules:**
- HTTPS-only, no credentials in URL.
- Allowlisted public CI hosts only.
- Commit SHA must match submitted commit.
- Failures return actionable `VerificationError`; do not mark project complete.

## 4. Completion Gate Contract

A shared course project is completed only when:
- checks verified == true
- evaluation source is AI (`ai`, or legacy missing source treated as AI-era)
- overall score is int 70..100
- every rubric criterion score is int 50..100

This gate must be implemented in a single service function and used by both submit and webhook flows.
