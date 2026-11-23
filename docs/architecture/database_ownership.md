# RUACH LMS — Database Ownership & Model Inventory (M0 Audit)

**Date:** 2026-11-24  
**Release:** Architecture Evolution 1.0  
**Baseline Commit:** `41d1d16`  
**Current Head:** `m7n8o9p1q2r3` (67 Mapped Models)

---

## 1. Domain Ownership Matrix (67 SQLAlchemy Models)

While all models currently reside in `app/models.py` sharing a single PostgreSQL/SQLite database, their logical ownership is strictly divided across domains:

| Domain | Models Owned | Table Names | Description |
|---|---|---|---|
| **Identity & Access** | 4 | `user`, `password_reset_token`, `phone_verification_code`, `rate_limit_counter` | Credentials, sessions, rate limits, roles (`learner`, `reviewer`, `instructor`, `administrator`). |
| **User & Profile** | 5 | `user_config`, `user_profile_photo`, `user_schedule`, `user_subject`, `user_subject_config` | User preferences, photos, study schedules, enrollments. |
| **Learning & Curriculum** | 9 | `learning_pathway`, `learner_pathway_enrollment`, `course_plan`, `lesson`, `lesson_bookmark`, `lesson_note`, `subject_curriculum`, `study_session`, `pathway_change_request` | Core curriculum delivery, pathway enrollments, study sessions. |
| **Progress & Foundations** | 4 | `progress`, `lesson_completion`, `lesson_task_progress`, `foundation_lesson_progress` | Granular lesson completions, task checklists, shared foundation unlock chains. |
| **Assessment & Quizzes** | 4 | `quiz`, `quiz_result`, `review_item`, `proficiency_test` | Lesson quizzes, diagnostic tests, spaced repetition intervals. |
| **AI Engineering Domain** | 6 | `ai_specialization_project`, `ai_prompt_version`, `ai_retrieval_configuration`, `ai_agent_execution_record`, `ai_evaluation_record`, `gemini_usage_bucket` | AI specialization workspaces, prompt versions, agent runs, RAG configurations. |
| **Machine Learning Domain** | 4 | `ml_specialization_project`, `ml_specialization_lesson_completion`, `ml_project_experiment`, `ml_specialization_credential` | ML specialization progress, model training experiments, metrics. |
| **Practice & Coding Arena** | 6 | `submission`, `practice_workspace`, `practice_usage_daily`, `arena_recommendation_dismissal`, `lab_debrief`, `engineering_lab_completion` | Code submissions, judge verdicts, troubleshooting lab debriefs, Pyodide workspaces. |
| **Project Studio & Evidence** | 5 | `course_project`, `learning_project`, `project_milestone`, `project_lifecycle_event`, `project_evaluation` | Milestone checklists, lifecycle transitions, multi-source evaluation versions. |
| **Artifacts & Storage** | 2 | `project_artifact`, `workspace_project` | Durable project files (S3/local), multi-file CodeMirror workspace trees. |
| **Credentials & Passport** | 4 | `credential`, `skill_node`, `user_skill_progress`, `skill_verification` | W3C verifiable credentials, Skill Passport competency nodes, verification audit logs. |
| **Community & Support** | 4 | `community_post`, `community_reply`, `support_request`, `leaderboard_score` | Forum discussions, learner feedback, materialized leaderboard scores. |
| **Integrations & Calendar** | 2 | `calendar_event`, `video_progress` | Google Calendar sync events, video watch completion. |
| **AI Platform & Background** | 4 | `ai_background_job`, `ai_job_result`, `ai_usage_record`, `tutor_conversation` | Background AI tasks, execution results, cost telemetry, persistent tutor chat. |
| **Operations & Infrastructure** | 4 | `admin_audit_log`, `app_config_override`, `judge_worker_heartbeat`, `service_heartbeat` | Admin actions, dynamic config overrides, worker heartbeats. |

---

## 2. Migration Lineage & Integrity

* **Head Revision:** `m7n8o9p1q2r3` (`Reconcile model/migration drift recorded in earlier milestone reports`)
* **Lineage Verification:** Clean single linear chain descending from initial schema `b5855622047f` through M2 (`h2i3j4k5l6m7`), M3 (`i4j5k6l7m8n9`), M4 (`j5k6l7m8n9o0`), M5 (`k6l7m8n9o0p1`), and drift reconciliation (`m7n8o9p1q2r3`).
* **Archived Drafts:** The unapplied and conflicting `1a7665109d7c` draft is safely disabled in `migrations/archive/1a7665109d7c_drop_pathway_destination_column.py.disabled`.
* **Drift Check:** `flask db check` reports **"No new upgrade operations detected"** (zero schema differences).

---

## 3. Data Separation & Future Service Readiness

To prepare for selective future service extraction without rewriting:
1. **Foreign Key Coupling Reduction:** Critical cross-domain entities (such as `ProjectEvaluation` and `ProjectArtifact`) reference domain objects via typed string keys and entity IDs (`owner_id`, `project_key`, `domain`) rather than hard foreign-key cascades across domain boundaries.
2. **Encapsulated Queries:** Domain logic queries models only within its logical scope; cross-domain queries are wrapped in service functions.
3. **No Distributed Transactions:** Workflows across domains rely on append-only event records (`ProjectLifecycleEvent`, `SkillVerification`) rather than distributed two-phase commits.
