# M4 — Project Studio Evidence Architecture

**Date:** 2026-11-22  
**Scope:** Code-verifiable Phase 4 foundations for the AI/ML Project Studio. This document records what was implemented and what remains an external or later-phase concern. It does not claim a live deployment, human reviewer UI, GPU run, or MLflow server verification.

## 1. Decisions

1. **Extend, do not replace.** The M2 shared lifecycle, milestone service, M3 artifact storage and ML experiment log remain the source of truth. No second project-management system was introduced.
2. **One lifecycle, separate workflows.** `app/services/project_lifecycle.py` still owns stage transitions. AI and ML projects keep independent records and assessment rules.
3. **Evidence is multi-source.** A generated score is never sufficient. An evaluation version stores automated checks, criterion-level rubric feedback, evidence references, and an optional human review as separate fields.
4. **Versions are append-only.** Reassessment writes a new `ProjectEvaluation` row; earlier evidence is never rewritten.
5. **Approval is a two-key process.** A privileged reviewer must approve the evidence, and the shared lifecycle must be `approved` or `published`, before competency claims are linked.
6. **Lesson completion is not mastery.** Lesson progress remains developmental evidence. Only verified project or assessment evidence can set `verification_status = VERIFIED`.

## 2. What was added

### Shared project infrastructure

| Component | Location | Responsibility |
|---|---|---|
| Evaluation model | `app/models.py` (`ProjectEvaluation`) | One append-only version per evaluation, with separate evidence columns and reviewer metadata. |
| Evidence service | `app/services/project_evaluation.py` | Validation, status derivation, versioning, human-review application and competency linkage. |
| Competency mapping | `app/services/project_competencies.py` | Module competencies from published manifests; ML uses the existing passport map. |
| Portfolio evidence | `app/services/project_portfolio.py` | Builds portfolio entries only from verified evaluations with an approved/published lifecycle. |
| Deterministic report checks | `app/domains/machine_learning/report.py` | Shared by ML submission and M4 evaluation evidence; no duplicate rule. |
| Artifact ownership | `app/services/artifacts.py`, `app/routes/artifacts.py` | `project_type='ai'` now accepts artifacts owned by an AI specialization project. |

### Specialization-specific evidence mappers

- `app/domains/ai_engineering/evaluation.py` reads only AI prompt versions, retrieval configurations, agent executions, evaluation records, AI project records, artifacts and milestones.
- `app/domains/machine_learning/evaluation.py` reads only ML projects, tracked experiments, durable artifacts and milestones.
- Neither mapper imports the other specialization, HTTP request state, or provider code.

### HTTP surface

Added to the existing `projects` blueprint (no new blueprint):

| Route | Purpose |
|---|---|
| `POST /api/projects/evaluations` | Create an evaluation version from stored specialization evidence, or from an explicit three-source payload. |
| `GET /api/projects/evaluations/<domain>/<project_key>` | Read versions for the owner or a privileged reviewer. |
| `POST /api/projects/evaluations/<int:id>/review` | Record a privileged human decision (`approved` / `revision_requested`). |
| `GET /api/projects/portfolio/evidence` | Read evidence-backed portfolio entries for the owner or a reviewed learner. |

The existing `/portfolio` and `/showcase/u/<public_id>` views now include these entries. Public output uses a whitelist and never exposes rubric feedback, human-review notes or internal failure details.

## 3. Evidence policy

`derive_status` applies one deterministic policy:

- any failed automated check → `REVISION_REQUESTED`;
- any rubric criterion below 50 → `REVISION_REQUESTED`;
- both sources present and a human decision of `approved` → `VERIFIED`;
- no human decision → `AWAITING_HUMAN_REVIEW`.

The displayed `rubric_score` is the arithmetic mean of criterion scores. It is descriptive, not a gate on its own. Criterion evidence text is mandatory.

Human review checks `can_assess_competency`, which rejects owners and unprivileged learners. A successful approval also moves the lifecycle to `approved` when the current stage permits it. If the evidence is `VERIFIED`, `link_verified_competencies`:

- ensures a `SkillNode` from the published module competency list;
- upserts `UserSkillProgress` with `evidence_type='PROJECT'` and an evidence id containing the evaluation version;
- appends a `SkillVerification` transition for every linked competency;
- never downgrades an existing `MASTERED` status.

## 4. Domain isolation

- AI competencies use ids derived from each AI module's published `competencies` list (`ai-competency-*`).
- ML competencies use the existing `ML_PROJECT_COMPETENCIES` map.
- A reviewer approving an AI project cannot create ML competency evidence, and vice versa. This is covered by regression tests.

## 5. Migration

`j5k6l7m8n9o0_add_project_evaluation.py` descends from M3 head `i4j5k6l7m8n9`. It only creates `project_evaluation` and its indexes; no existing table or column is changed. The pre-existing untracked `1a7665109d7c` migration remains untouched and is still recorded as separate repository debt.

## 6. Reused Phase 5 foundations

M4's Tutor 2.0 context requirement is served by the existing `app.domains.learning.context.resolve_learning_context` resolver and the existing tutor service. This M4 slice did not modify them; their regression suites are included in the full run. Retrieval-augmented learning, tutor evaluation datasets, and competency-aware recommendation changes remain later Phase 5 work and are not claimed here.

## 7. Explicitly not verified here

- Live Docker execution or kernel-level resource enforcement.
- GPU scheduling or advanced compute workers.
- MLflow server connectivity and real run logging.
- Deployment of a judge worker on a separate Docker-capable host.
- A browser UI for reviewer decisions; M4 exposes the HTTP API only.
- Full Phase 5 RAG ingestion, retrieval-boundary enforcement and tutor quality dataset evaluation.
