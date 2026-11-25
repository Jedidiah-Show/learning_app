# Learning Outcome Event Schema (Draft)

Privacy-conscious event model for product and learning analytics. Events must not include secrets, raw prompts, submission source code, or unnecessary PII.

## Common Envelope

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `event_name` | string | yes | Stable snake_case name |
| `event_version` | int | yes | Schema version |
| `occurred_at` | ISO-8601 UTC | yes | Event time |
| `request_id` | string | no | Correlates with logs |
| `actor_user_id` | int/hash | no | Internal ID; hash/export carefully |
| `actor_role` | string | no | learner/admin/reviewer |
| `pathway` | string | no | ai-engineering/machine-learning/shared-foundations |
| `surface` | string | no | dashboard/lesson/project/arena/tutor/etc. |
| `properties` | object | yes | Event-specific, bounded fields |

## Core Events

### Learning Progress
- `lesson_started` - `{lesson_id, module_id, pathway, source}`
- `lesson_completed` - `{lesson_id, module_id, pathway, completion_source, duration_seconds?}`
- `quiz_submitted` - `{quiz_id, lesson_id?, score, passed, attempt}`
- `review_item_answered` - `{review_item_id, correct, interval_days, due_at}`

### Projects
- `project_submission_saved` - `{module_id, pathway, has_repo, has_checks_url, has_demo}`
- `project_verification_result` - `{module_id, provider, verified, pending, reason_category?}`
- `project_evaluation_result` - `{module_id, source, score?, passed, failed_criteria_count?}`
- `project_completed` - `{module_id, pathway, score, evaluation_source}`

### Practice / Arena
- `practice_run` - `{exercise_id, lesson_id, result, runtime_ms?, error_category?}`
- `arena_submission_queued` - `{problem_id, language, submission_id}`
- `arena_submission_completed` - `{problem_id, submission_id, status, score?, runtime_ms?}`

### Tutor / AI
- `tutor_prompt_sent` - `{lesson_id?, pathway, model_tier, prompt_version?}`
- `tutor_response_received` - `{lesson_id?, pathway, provider, fallback_used, latency_ms, outcome}`
- `ai_provider_fallback` - `{task_type, primary_provider, fallback_provider, reason_category, cooldown_seconds?}`

### Engagement / Outcomes
- `streak_milestone_reached` - `{streak_days}`
- `certificate_issued` - `{credential_type, pathway, public_id}`
- `support_request_created` - `{category, has_page_path}`

## Privacy & Retention

- Do not log raw email, phone, tokens, passwords, prompt text, submission code, or full AI responses in analytics events.
- Prefer bounded enums/categories over free text.
- Apply retention limits and access controls; aggregate for reporting where possible.
- Keep event schemas versioned; additive changes increment minor documentation, breaking changes increment `event_version`.
