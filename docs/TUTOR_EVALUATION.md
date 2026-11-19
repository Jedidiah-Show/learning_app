# Tutor quality evaluation

Two distinct layers are used, and they are never conflated (M5.4):

## 1. Structural dataset validation (runs in CI)

`docs/tutor_evaluation/run_tutor_eval.py --domain all --dry-run --strict`

validates the three domain datasets (`shared_foundations_eval.json`,
`ai_engineering_eval.json`, `machine_learning_eval.json`) and scores case
metadata heuristically. Every emitted record carries `mode: structural`,
`model_id: structural`, and a `run_id`. The `--strict` flag exits non-zero if
any case fails structural validation; this is the release gate for prompt
edits. It does **not** measure live model quality.

`test_tutor_modes_cover_quality_cases` (fixtures:
`tests/fixtures/tutor_quality_cases.json`) additionally checks that each
mode selects the intended teaching behaviour and depth. Canonical modes:

`explain · socratic · debug · review · practice · project_mentor · assessment_prep`

(legacy `hint`/`quiz`/`code_review` are accepted aliases mapping onto
`socratic`/`practice`/`review`).

## 2. Model-backed evaluation (before a tutor prompt/model release)

Run the same runner without `--dry-run` with `GEMINI_API_KEY` configured; the
record mode becomes `live` and metadata records the configured model
(`GEMINI_FLASH_MODEL`/`GEMINI_PRO_MODEL`). Score each response from 0 to 2 on:

- Lesson relevance and factual grounding
- Mode adherence (especially no complete solution in Socratic mode)
- Domain correctness (Shared Foundations vs AI Engineering vs ML — no cross-
  contamination)
- Clear reasoning and actionable learner guidance
- Appropriate response length and beginner-friendly language
- Hint progression (stage n+1 discloses nothing that stage n would)
- Solution leakage (no verbatim solution code unless the editorial stage)
- Safety and no fabricated references or unsupported claims

Record model and prompt version, scores, latency, errors, and token/cost data
with the release results. Do not mark model quality validation complete until
the responses have been reviewed against this rubric.

## Live run attempts (2026-11-19)

Gemini integration has never worked in this deployment; the configured
`GEMINI_API_KEY` returns HTTP 401 (revoked/never valid). The application is
wired and healthy with OpenRouter as the provider (owner-confirmed).

First live run (`docs/tutor_evaluation/live_run_2026-11-19.jsonl`, run_id in
the file): **5 of 15 cases answered** — `sf-01`, `sf-02`, `sf-05`, `ai-03`,
`ml-05`. Average latency of answered cases ≈ 11.7 s (max ≈ 17.6 s), driven by
OpenRouter retries. The remaining 10 cases failed with OpenRouter **HTTP 402
(in-flight credit limit exceeded)** or truncated output. Conclusion: live
model-backed evaluation is **blocked by provider credits**, not by the app.
Latency/cost baselines are therefore **unmeasured** — do not cite the run as
passing. To complete this step: add OpenRouter credits, then

    GEMINI_API_KEY= .venv/bin/python docs/tutor_evaluation/run_tutor_eval.py \
        --domain all --out docs/tutor_evaluation/live_run_<date>.jsonl

and score each response per the rubric below before promoting the tutor
prompt. Structural gates (`--strict`) continue to run in CI.

## Release rule

A tutor prompt or model change may not ship unless:

1. `--strict` structural validation passes in CI; and
2. the last live evaluation for the affected domain scored every case ≥ 1 on
   mode adherence, domain correctness and no-solution-leakage, with zero
   safety failures.

