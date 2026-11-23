"""Traceable evaluation evidence for Machine Learning projects (M4).

Reads only ML specialization records. Deterministic report checks come from
the same domain validator used by submission handling; experiment metadata and
durable artifacts are added as references. AI Engineering records are never
consulted here.
"""

from __future__ import annotations

import json

from app.domains.machine_learning.report import module_by_id, report_matches
from app.ml_pathway import PATHWAY_ID
from app.models import (
    MLSpecializationProject, MLProjectExperiment, ProjectArtifact,
    ProjectMilestone,
)


class EvidenceError(ValueError):
    """Raised when stored ML project evidence is missing or malformed."""


def _load_json(value, field_name, *, expected=None):
    if not value:
        return {} if expected is dict else []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError) as error:
        raise EvidenceError(f'{field_name} must contain valid JSON') from error
    if expected is not None and not isinstance(parsed, expected):
        raise EvidenceError(f'{field_name} must contain a JSON {expected.__name__}')
    return parsed


def _rubric_feedback(record):
    if record is None or not record.evaluation:
        raise EvidenceError('No stored rubric feedback for this ML project')
    evaluation = _load_json(record.evaluation, 'project evaluation', expected=dict)
    raw = evaluation.get('criterion_feedback') or evaluation.get('criteria') or []
    if not isinstance(raw, list) or not raw:
        raise EvidenceError('Stored project evaluation has no rubric criteria')
    criteria = []
    for item in raw:
        if not isinstance(item, dict):
            raise EvidenceError('Each rubric criterion must be an object')
        criterion = item.get('criterion') or item.get('name')
        score = item.get('score')
        evidence = item.get('evidence')
        if (
            not isinstance(criterion, str) or not criterion.strip()
            or isinstance(score, bool) or not isinstance(score, int)
            or not 0 <= score <= 100
            or not isinstance(evidence, str) or not evidence.strip()
        ):
            raise EvidenceError('Rubric criteria need criterion, score and evidence')
        criteria.append({
            'criterion': criterion.strip()[:300],
            'score': score,
            'evidence': evidence.strip()[:2000],
            'gap': str(item.get('gap') or '')[:2000],
        })
    return {
        'source': 'machine-learning:stored-project-review',
        'criteria': criteria,
        'summary': str(evaluation.get('summary') or '')[:6000],
    }


def build_evidence(user_id, module_id):
    """Collect M4 evidence for one ML specialization project."""
    module = module_by_id(module_id)
    if module is None:
        raise EvidenceError(f'Unknown ML project {module_id!r}')

    project = MLSpecializationProject.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).first()
    submission = {}
    if project is not None and project.submission:
        submission = _load_json(project.submission, 'submission', expected=dict)
    report = submission.get('report') if isinstance(submission.get('report'), dict) else {}

    experiments = MLProjectExperiment.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).order_by(MLProjectExperiment.id).all()
    experiment_ids = [row.id for row in experiments]
    artifacts = []
    if experiment_ids:
        artifacts = ProjectArtifact.query.filter(
            ProjectArtifact.owner_id == user_id,
            ProjectArtifact.project_type == 'ml',
            ProjectArtifact.project_id.in_(experiment_ids),
        ).order_by(ProjectArtifact.id).all()
    milestones = ProjectMilestone.query.filter_by(
        user_id=user_id, domain='machine-learning', project_key=module_id,
        completed=True,
    ).order_by(ProjectMilestone.id).all()

    checks = [{
        'name': 'report-contract',
        'passed': report_matches(module_id, report),
        'detail': 'Deterministic report check against the published contract',
    }, {
        'name': 'experiment-recorded',
        'passed': bool(experiments),
        'detail': f'{len(experiments)} tracked experiment(s)',
    }, {
        'name': 'experiment-metrics-recorded',
        'passed': any(bool(row.evaluation_metrics) for row in experiments),
        'detail': 'Evaluation metrics stored on at least one experiment',
    }, {
        'name': 'model-or-report-artifact',
        'passed': any(
            row.artifact_type in {'model', 'report', 'notebook', 'output'}
            for row in artifacts
        ),
        'detail': f'{len(artifacts)} durable artifact(s)',
    }]

    for row in experiments:
        metrics = _load_json(row.evaluation_metrics, 'evaluation_metrics', expected=dict)
        for name, value in metrics.items():
            if isinstance(value, dict) and isinstance(value.get('passed'), bool):
                checks.append({
                    'name': f'metric:{name}'[:160],
                    'passed': value['passed'],
                    'detail': json.dumps(value, ensure_ascii=False)[:500],
                })

    refs = []
    refs.extend({'type': 'experiment', 'id': str(row.id),
                 'detail': row.experiment_name} for row in experiments)
    refs.extend({'type': 'artifact', 'id': str(row.id),
                 'detail': row.original_filename} for row in artifacts)
    refs.extend({'type': 'milestone', 'id': row.milestone_id,
                 'detail': 'completed deliverable'} for row in milestones)
    for field in ('repository_url', 'checks_url', 'demo_url'):
        if submission.get(field):
            refs.append({'type': field, 'id': str(submission[field])[:500],
                         'detail': 'project submission URL'})

    return {
        'domain': 'machine-learning',
        'project_key': module_id,
        'automated_checks': {
            'source': 'machine-learning:deterministic-and-tracked',
            'checks': checks,
        },
        'rubric_feedback': _rubric_feedback(project),
        'evidence_refs': refs,
    }


__all__ = ['EvidenceError', 'build_evidence', 'module_by_id']
