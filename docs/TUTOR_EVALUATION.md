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

## Latency and cost baselines

Not yet measured in this environment — record them on the first live run
(report: p50/p95 latency, tokens per response, cost per 1k tutoring requests)
and store the result alongside the release notes. Until then, latency/cost
must be reported as *unmeasured*, not as passing.

## Release rule

A tutor prompt or model change may not ship unless:

1. `--strict` structural validation passes in CI; and
2. the last live evaluation for the affected domain scored every case ≥ 1 on
   mode adherence, domain correctness and no-solution-leakage, with zero
   safety failures.

