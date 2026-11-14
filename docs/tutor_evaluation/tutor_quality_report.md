# Tutor Evaluation Report (M5.6)

**Date:** 2026-11-14  
**Scope:** Domain-aware tutoring for Shared Foundations, AI Engineering, and Machine Learning Engineering.

## Evaluation datasets
Separate, versioned prompt sets are defined for each domain:
- `docs/tutor_evaluation/shared_foundations_eval.json`
- `docs/tutor_evaluation/ai_engineering_eval.json`
- `docs/tutor_evaluation/machine_learning_eval.json`

Each case specifies prompt, type, optional lesson/problem/error context, and expected behaviors (technical correctness cues, context relevance, explanation quality, beginner accessibility, hint usefulness, and scope handling).

## Evaluation dimensions
Assess each response against:
1. **Technical correctness** — facts, reasoning, and code/math guidance are accurate for the domain.
2. **Context relevance** — uses supplied lesson, pathway/domain, errors, submissions, and Skill Passport evidence; does not assume the other specialisation is complete.
3. **Explanation quality** — clear structure, concrete examples/analogies where helpful, links to lesson concepts.
4. **Beginner accessibility** — plain language, defines terms when needed, avoids unnecessary jargon.
5. **Hint usefulness (Socratic)** — encourages prediction/reasoning, gives progressive hints, identifies misconceptions, and withholds full solutions before editorial stages.
6. **Code correctness** — suggested fixes/steps are syntactically and logically sound for the stated context.
7. **Mathematical correctness** — statistics/ML formulas, metrics, and interpretations are correct.
8. **Unsupported claims** — avoids fabrication, overconfidence, and guarantees; states uncertainty/limits.
9. **Latency** — time to first/complete response within product targets.
10. **Cost** — token/request cost tracked per mode and domain.

## Current implementation evidence (code-level)
- `app/services/tutor.py`: domain inference/profiles for Shared Foundations, AI Engineering, and ML; pathway/domain context assembly (lesson/module, submissions, errors, exercise, Skill Passport); progressive Socratic hint stages; diagnosis helpers; guardrails against premature solution disclosure.
- `app/routes/lessons.py`: domain-aware prompt/greeting, syllabus scoping by learner pathway, Socratic mode instructions, out-of-scope redirect behavior, and pathway context in tutor responses.
- `templates/lessons/detail.html` + `app/routes/main.py`: domain-aware tutor greeting rendered in lesson UI.

## Baseline run status
- **Automated structural checks / harness:** `docs/tutor_evaluation/run_tutor_eval.py` loads all three domain datasets and generates case records for rubric scoring.
  - Dry run: `.venv/bin/python docs/tutor_evaluation/run_tutor_eval.py --domain all --dry-run`
  - JSONL output: `.venv/bin/python docs/tutor_evaluation/run_tutor_eval.py --domain all --dry-run --out /tmp/tutor_eval.jsonl`
  - Baseline dry-run result (2026-11-14): **15 cases** across `shared-foundations`, `ai-engineering`, `machine-learning`.
- **Model-backed qualitative scoring:** live model execution, rubric scoring, and latency/cost capture are not yet fully automated in-repo; run generated cases through the live tutor with representative learner contexts and record scores per dimension (1–5) plus latency/token/cost observations per domain and model tier.
- **Regression:** targeted M5-related and pathway/practice suites passed in batched runs during this implementation cycle; a full-suite regression run is required for release evidence.

## Known gaps / follow-up
- Add an automated harness to execute dataset cases against `assemble_tutor_context`/tutor prompts and capture rubric scores consistently.
- Expand datasets with code-review and multi-turn misconception cases per domain.
- Record measured latency/cost baselines per provider/model tier and enforce thresholds in CI where feasible.
- Extend UI rendering of full pathway context (current module/lesson/competency summary) in all tutor surfaces, including practice arena chat surfaces if enabled.

## Conclusion
M5 foundations are implemented: domain-aware context, specialized domain behaviors/greetings, Socratic hinting/guardrails, and per-domain evaluation datasets with a quality rubric/report. Remaining work is to operationalize automated scoring and publish measured latency/cost baselines across all domains.
