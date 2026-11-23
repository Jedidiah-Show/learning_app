"""Shared traceable project evaluation evidence (M4).

A project evaluation is not a generated number. Each version stores three
distinct kinds of evidence:

1. automated checks (deterministic or recorded observations),
2. rubric feedback with criterion-level evidence, and
3. an optional human review by a privileged reviewer.

The service validates those sources, computes a transparent status, keeps
append-only versions, and only links competencies when a human reviewer has
approved the evidence *and* the project lifecycle is approved/published.
Lesson completion is never used as mastery evidence here.
"""

from __future__ import annotations

import json
import re

from app import db
from app.models import (
    ProjectEvaluation, SkillNode, SkillVerification, UserSkillProgress, utcnow,
)
from app.services.authorization import can_assess_competency
from app.services.project_competencies import competencies_for

DOMAINS = ('ai-engineering', 'machine-learning')
EVALUATION_STAGES = frozenset({
    'submitted', 'under_review', 'revision_requested', 'approved', 'published',
})
REVIEWABLE_STAGES = frozenset({'submitted', 'under_review'})
DECISIONS = frozenset({'approved', 'revision_requested'})
MIN_CRITERION_SCORE = 50
MAX_CHECKS = 100
MAX_CRITERIA = 50
MAX_REFS = 200


class EvaluationError(ValueError):
    """Raised for invalid evidence, lifecycle state or reviewer action."""


def _load_json(value, field_name, *, expected=None, default=None):
    if value is None or value == '':
        return default if default is not None else ({} if expected is dict else [])
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError) as error:
        raise EvaluationError(f'{field_name} must contain valid JSON') from error
    if expected is not None and not isinstance(parsed, expected):
        raise EvaluationError(f'{field_name} must contain a JSON {expected.__name__}')
    return parsed


def _text(value, field_name, *, limit, required=True):
    if not isinstance(value, str):
        raise EvaluationError(f'{field_name} must be a string')
    cleaned = value.strip()
    if required and not cleaned:
        raise EvaluationError(f'{field_name} is required')
    return cleaned[:limit]


def validate_automated_checks(automated_checks):
    checks = _load_json(automated_checks, 'automated_checks', expected=dict)
    source = _text(checks.get('source'), 'automated_checks.source', limit=200)
    rows = checks.get('checks')
    if not isinstance(rows, list) or not rows or len(rows) > MAX_CHECKS:
        raise EvaluationError(
            f'automated_checks.checks must contain 1 to {MAX_CHECKS} checks'
        )
    normalized = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('passed'), bool):
            raise EvaluationError('Each automated check needs a boolean passed value')
        normalized.append({
            'name': _text(row.get('name'), 'check.name', limit=160),
            'passed': row['passed'],
            'detail': _text(row.get('detail'), 'check.detail', limit=500, required=False),
        })
    return {'source': source, 'checks': normalized}


def validate_rubric_feedback(rubric_feedback):
    rubric = _load_json(rubric_feedback, 'rubric_feedback', expected=dict)
    source = _text(rubric.get('source'), 'rubric_feedback.source', limit=200)
    rows = rubric.get('criteria')
    if not isinstance(rows, list) or not rows or len(rows) > MAX_CRITERIA:
        raise EvaluationError(
            f'rubric_feedback.criteria must contain 1 to {MAX_CRITERIA} criteria'
        )
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise EvaluationError('Each rubric criterion must be an object')
        score = row.get('score')
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            raise EvaluationError('Rubric criterion score must be an integer 0-100')
        normalized.append({
            'criterion': _text(row.get('criterion'), 'criterion', limit=300),
            'score': score,
            'evidence': _text(row.get('evidence'), 'criterion evidence', limit=2000),
            'gap': _text(row.get('gap'), 'criterion gap', limit=2000, required=False),
        })
    return {
        'source': source,
        'criteria': normalized,
        'summary': _text(rubric.get('summary'), 'rubric summary', limit=6000, required=False),
    }


def validate_evidence_refs(evidence_refs):
    refs = _load_json(evidence_refs, 'evidence_refs', expected=list)
    if not refs or len(refs) > MAX_REFS:
        raise EvaluationError(f'evidence_refs must contain 1 to {MAX_REFS} references')
    normalized = []
    for row in refs:
        if not isinstance(row, dict):
            raise EvaluationError('Each evidence reference must be an object')
        normalized.append({
            'type': _text(row.get('type'), 'reference type', limit=60),
            'id': _text(str(row.get('id') or ''), 'reference id', limit=500),
            'detail': _text(row.get('detail'), 'reference detail', limit=500, required=False),
        })
    return normalized


def derive_status(automated_checks, rubric_feedback, human_review):
    """Return a status derived only from the recorded evidence."""
    if any(not row['passed'] for row in automated_checks['checks']):
        return 'REVISION_REQUESTED'
    if any(row['score'] < MIN_CRITERION_SCORE for row in rubric_feedback['criteria']):
        return 'REVISION_REQUESTED'
    if human_review:
        if human_review.get('decision') == 'approved':
            return 'VERIFIED'
        if human_review.get('decision') == 'revision_requested':
            return 'REVISION_REQUESTED'
    return 'AWAITING_HUMAN_REVIEW'


def _rubric_score(rubric_feedback):
    scores = [row['score'] for row in rubric_feedback['criteria']]
    return int(round(sum(scores) / len(scores))) if scores else None


def build_domain_evidence(user_id, domain, project_key):
    """Collect evidence from the owning specialization's own records."""
    if domain == 'ai-engineering':
        from app.domains.ai_engineering.evaluation import build_evidence
    elif domain == 'machine-learning':
        from app.domains.machine_learning.evaluation import build_evidence
    else:
        raise EvaluationError(f'Unknown domain {domain!r}; expected one of {DOMAINS}')
    try:
        return build_evidence(user_id, project_key)
    except ValueError as error:
        raise EvaluationError(str(error)) from error


def _next_version(user_id, domain, project_key):
    highest = db.session.query(db.func.max(ProjectEvaluation.version)).filter_by(
        user_id=user_id, domain=domain, project_key=project_key,
    ).scalar()
    return int(highest or 0) + 1


def create_evaluation(
    user_id,
    domain,
    project_key,
    automated_checks,
    rubric_feedback,
    evidence_refs,
    *,
    created_by=None,
    commit=True,
):
    """Persist one evaluation version and return its public service payload."""
    from app.services.project_lifecycle import current_stage

    if domain not in DOMAINS:
        raise EvaluationError(f'Unknown domain {domain!r}; expected one of {DOMAINS}')
    if not isinstance(project_key, str) or not project_key.strip():
        raise EvaluationError('project_key is required')
    if created_by is not None:
        actor_id = getattr(created_by, 'id', None)
        if actor_id != int(user_id) and not can_assess_competency(created_by, user_id):
            raise EvaluationError('You are not authorized to create evidence for this learner')

    stage = current_stage(user_id, domain, project_key)
    if stage not in EVALUATION_STAGES:
        raise EvaluationError(
            f'Project must be submitted before evaluation (current stage: {stage})'
        )

    checks = validate_automated_checks(automated_checks)
    rubric = validate_rubric_feedback(rubric_feedback)
    refs = validate_evidence_refs(evidence_refs)
    record = ProjectEvaluation(
        user_id=int(user_id),
        domain=domain,
        project_key=project_key.strip(),
        version=_next_version(user_id, domain, project_key),
        lifecycle_stage=stage,
        automated_checks_json=json.dumps(checks, ensure_ascii=False),
        rubric_feedback_json=json.dumps(rubric, ensure_ascii=False),
        evidence_refs_json=json.dumps(refs, ensure_ascii=False),
        status=derive_status(checks, rubric, None),
        rubric_score=_rubric_score(rubric),
        created_by_user_id=getattr(created_by, 'id', None),
    )
    db.session.add(record)
    db.session.flush()
    if commit:
        db.session.commit()
    return to_dict(record)


def evaluations_for(user_id, domain=None, project_key=None):
    query = ProjectEvaluation.query.filter_by(user_id=int(user_id))
    if domain is not None:
        query = query.filter_by(domain=domain)
    if project_key is not None:
        query = query.filter_by(project_key=project_key)
    return query.order_by(
        ProjectEvaluation.domain, ProjectEvaluation.project_key,
        ProjectEvaluation.version,
    ).all()


def latest_evaluation(user_id, domain, project_key):
    return (
        ProjectEvaluation.query.filter_by(
            user_id=int(user_id), domain=domain, project_key=project_key,
        )
        .order_by(ProjectEvaluation.version.desc())
        .first()
    )


def to_dict(evaluation, *, include_private=True):
    payload = {
        'id': evaluation.id,
        'user_id': evaluation.user_id,
        'domain': evaluation.domain,
        'project_key': evaluation.project_key,
        'version': evaluation.version,
        'lifecycle_stage': evaluation.lifecycle_stage,
        'status': evaluation.status,
        'rubric_score': evaluation.rubric_score,
        'created_at': evaluation.created_at.isoformat() if evaluation.created_at else None,
    }
    if include_private:
        payload.update({
            'automated_checks': evaluation.get_automated_checks(),
            'rubric_feedback': evaluation.get_rubric_feedback(),
            'evidence_refs': evaluation.get_evidence_refs(),
            'human_review': evaluation.get_human_review(),
            'reviewed_at': evaluation.reviewed_at.isoformat() if evaluation.reviewed_at else None,
        })
    return payload


def _normalised_title(skill_id, title):
    slug_id = re.sub(r'[^a-z0-9]+', '-', skill_id.strip().lower()).strip('-')[:64]
    slug_title = re.sub(r'[^a-z0-9]+', '-', title.strip().lower()).strip('-')[:63]
    return f'{slug_id}-{slug_title}'[:128]


def _ensure_skill_node(competency):
    skill_id = competency['id']
    if db.session.get(SkillNode, skill_id) is not None:
        return
    db.session.add(SkillNode(
        id=skill_id,
        title=competency['title'][:128],
        normalized_title=_normalised_title(skill_id, competency['title']),
        category=competency['category'][:64],
    ))


def link_verified_competencies(evaluation, reviewer, *, commit=False):
    """Attach approved project evidence to the owner's competency record.

    Only called after human approval and an approved/published lifecycle
    stage. Each transition is appended to ``skill_verification`` so a later
    revocation or reassessment keeps a complete audit trail.
    """
    evidence_id = (
        f'{evaluation.domain}:{evaluation.project_key}:eval-{evaluation.version}'
    )
    now = utcnow()
    for competency in competencies_for(evaluation.domain, evaluation.project_key):
        _ensure_skill_node(competency)
        progress = UserSkillProgress.query.filter_by(
            user_id=evaluation.user_id, skill_id=competency['id'],
        ).with_for_update().first()
        from_status = progress.verification_status if progress else 'UNVERIFIED'
        if (
            progress is not None and from_status == 'VERIFIED'
            and progress.evidence_id == evidence_id
        ):
            continue
        if progress is None:
            progress = UserSkillProgress(
                user_id=evaluation.user_id,
                skill_id=competency['id'],
                status='DEMONSTRATED',
                evidence_type='PROJECT',
                evidence_id=evidence_id,
                verification_status='VERIFIED',
                verified_at=now,
                verified_by_user_id=reviewer.id,
                verification_note=f'M4 verified project evaluation {evaluation.id}',
                updated_at=now,
            )
            db.session.add(progress)
        else:
            progress.status = (
                'MASTERED' if progress.status == 'MASTERED' else 'DEMONSTRATED'
            )
            progress.evidence_type = 'PROJECT'
            progress.evidence_id = evidence_id
            progress.verification_status = 'VERIFIED'
            progress.verified_at = now
            progress.verified_by_user_id = reviewer.id
            progress.verification_note = (
                f'M4 verified project evaluation {evaluation.id}'
            )
            progress.updated_at = now
        db.session.add(SkillVerification(
            user_id=evaluation.user_id,
            skill_id=competency['id'],
            from_status=from_status,
            to_status='VERIFIED',
            requested_by_user_id=evaluation.user_id,
            assessed_by_user_id=reviewer.id,
            note=f'M4 project evidence: {evidence_id}',
            created_at=now,
        ))
    if commit:
        db.session.commit()


def record_human_review(evaluation_id, reviewer, decision, note=''):
    """Record a privileged human review and apply its lifecycle/competency effects."""
    from app.services.project_lifecycle import (
        LifecycleError, current_stage, record_transition,
    )

    if decision not in DECISIONS:
        raise EvaluationError('decision must be approved or revision_requested')
    evaluation = db.session.get(ProjectEvaluation, int(evaluation_id))
    if evaluation is None:
        raise EvaluationError('Evaluation not found')
    if not can_assess_competency(reviewer, evaluation.user_id):
        raise EvaluationError('You are not authorized to review this evidence')
    if evaluation.get_human_review() is not None:
        raise EvaluationError('This evaluation has already been reviewed')

    stage = current_stage(evaluation.user_id, evaluation.domain, evaluation.project_key)
    if decision == 'approved' and stage not in EVALUATION_STAGES:
        raise EvaluationError(f'Cannot approve a project at stage {stage!r}')
    if decision == 'revision_requested' and stage not in REVIEWABLE_STAGES:
        raise EvaluationError(f'Cannot request revision at stage {stage!r}')

    now = utcnow()
    human_review = {
        'decision': decision,
        'note': _text(note, 'review note', limit=4000, required=False),
        'reviewer_id': reviewer.id,
        'reviewed_at': now.isoformat(),
    }
    checks = evaluation.get_automated_checks()
    rubric = evaluation.get_rubric_feedback()
    evaluation.human_review_json = json.dumps(human_review, ensure_ascii=False)
    evaluation.status = derive_status(checks, rubric, human_review)
    evaluation.reviewed_by_user_id = reviewer.id
    evaluation.reviewed_at = now

    try:
        if decision == 'approved':
            # A published project is already beyond approval; do not try to
            # move it backwards. Same-stage calls are idempotent.
            if stage in REVIEWABLE_STAGES:
                stage = record_transition(
                    evaluation.user_id, evaluation.domain, evaluation.project_key,
                    'approved', actor=reviewer,
                    note=f'M4 human review of evaluation {evaluation.id}',
                )
            if evaluation.status == 'VERIFIED':
                link_verified_competencies(evaluation, reviewer, commit=False)
        else:
            stage = record_transition(
                evaluation.user_id, evaluation.domain, evaluation.project_key,
                'revision_requested', actor=reviewer,
                note=f'M4 human review requested revision on evaluation {evaluation.id}',
            )
    except LifecycleError as error:
        raise EvaluationError(str(error)) from error
    evaluation.lifecycle_stage = stage
    db.session.commit()
    return to_dict(evaluation)


__all__ = [
    'DOMAINS', 'EVALUATION_STAGES', 'EvaluationError', 'build_domain_evidence',
    'create_evaluation', 'derive_status', 'evaluations_for', 'latest_evaluation',
    'link_verified_competencies', 'record_human_review', 'to_dict',
    'validate_automated_checks', 'validate_evidence_refs', 'validate_rubric_feedback',
]
