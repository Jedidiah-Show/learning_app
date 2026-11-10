# Tutor quality evaluation

`tests/fixtures/tutor_quality_cases.json` is the minimum prompt-contract set for
Explain, Hint, Quiz, and Code Review modes. `test_tutor_modes_cover_quality_cases`
checks that each request selects the intended teaching behavior and response
depth. This is a deterministic contract test, not a claim that a model response
has passed a quality evaluation.

Before a model or prompt release, run each case against the configured model
and score the response from 0 to 2 on:

- Lesson relevance and factual grounding
- Mode adherence (especially no complete solution in Hint mode)
- Clear reasoning and actionable learner guidance
- Appropriate response length and beginner-friendly language
- No fabricated references or unsupported claims

Record model and prompt version, scores, latency, errors, and token/cost data
with the release results. Do not mark model quality validation complete until
the responses have been reviewed against this rubric.
