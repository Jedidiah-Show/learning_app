"""Traceable evaluation evidence for AI Engineering projects (M4).

This mapper reads only AI specialization records. It does not assign final
verdicts: it gathers automated checks, stored rubric feedback and references
to durable evidence so the shared evaluation service can apply one consistent
evidence policy. Machine Learning records are never consulted here.
"""

from __future__ import annotations

import json

from app.ai_pathway import PATHWAY_ID, ai_engineering_pathway
from app.models import (
    AIAgentExecutionRecord, AIEvaluationRecord, AIPromptVersion,
    AIRetrievalConfiguration, AISpecializationProject, ProjectArtifact,
    ProjectMilestone,
)

SUCCESS_AGENT_STATUSES = frozenset({'completed', 'success', 'succeeded', 'ok', 'finished'})


class EvidenceError(ValueError):
    """Raised when stored AI project evidence is missing or malformed."""


def module_by_id(module_id):
    return next(
        (
            module for module in ai_engineering_pathway()['modules']
            if module['id'] == module_id
        ),
        None,
    )


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


def _submission(record):
    if record is None or not record.submission:
        return {}
    return _load_json(record.submission, 'submission', expected=dict)


def _rubric_feedback(record):
    if record is None or not record.evaluation:
        raise EvidenceError('No stored rubric feedback for this AI project')
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
        'source': 'ai-engineering:stored-project-review',
        'criteria': criteria,
        'summary': str(evaluation.get('summary') or '')[:6000],
    }


def build_evidence(user_id, module_id):
    """Collect M4 evidence for one AI specialization project.

    Returns a dict with ``automated_checks``, ``rubric_feedback`` and
    ``evidence_refs`` ready for ``project_evaluation.create_evaluation``.
    """
    module = module_by_id(module_id)
    if module is None:
        raise EvidenceError(f'Unknown AI Engineering project {module_id!r}')

    project = AISpecializationProject.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).first()
    prompt_versions = AIPromptVersion.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).order_by(AIPromptVersion.version).all()
    retrieval_configs = AIRetrievalConfiguration.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).order_by(AIRetrievalConfiguration.id).all()
    agent_runs = AIAgentExecutionRecord.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).order_by(AIAgentExecutionRecord.id).all()
    evaluation_rows = AIEvaluationRecord.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).order_by(AIEvaluationRecord.id).all()
    artifacts = []
    if project is not None:
        artifacts = ProjectArtifact.query.filter_by(
            owner_id=user_id, project_type='ai', project_id=project.id,
        ).order_by(ProjectArtifact.id).all()
    milestones = ProjectMilestone.query.filter_by(
        user_id=user_id, domain='ai-engineering', project_key=module_id,
        completed=True,
    ).order_by(ProjectMilestone.id).all()

    checks = [{
        'name': 'prompt-version-recorded',
        'passed': bool(prompt_versions),
        'detail': f'{len(prompt_versions)} prompt version(s) stored',
    }, {
        'name': 'retrieval-configuration-recorded',
        'passed': bool(retrieval_configs),
        'detail': f'{len(retrieval_configs)} retrieval configuration(s) stored',
    }, {
        'name': 'agent-execution-succeeded',
        'passed': any(run.status in SUCCESS_AGENT_STATUSES for run in agent_runs),
        'detail': ', '.join(sorted({run.status for run in agent_runs})) or 'no agent runs',
    }, {
        'name': 'evaluation-dataset-recorded',
        'passed': any(bool(row.evaluation_dataset) for row in evaluation_rows),
        'detail': ', '.join(
            row.evaluation_dataset for row in evaluation_rows if row.evaluation_dataset
        ) or 'no evaluation dataset',
    }]

    for row in evaluation_rows:
        results = _load_json(row.evaluation_results, 'evaluation_results', expected=dict)
        summary = _load_json(row.metric_summary, 'metric_summary', expected=dict)
        for check in results.get('checks') or []:
            if not isinstance(check, dict):
                raise EvidenceError('Stored checks must be objects')
            if isinstance(check.get('passed'), bool):
                checks.append({
                    'name': str(check.get('name') or f'evaluation-{row.id}')[:160],
                    'passed': check['passed'],
                    'detail': str(check.get('detail') or '')[:500],
                })
        for name, metric in summary.items():
            if isinstance(metric, dict) and isinstance(metric.get('passed'), bool):
                checks.append({
                    'name': f'metric:{name}'[:160],
                    'passed': metric['passed'],
                    'detail': json.dumps(metric, ensure_ascii=False)[:500],
                })

    refs = []
    refs.extend({'type': 'prompt_version', 'id': str(row.id),
                 'detail': f'version {row.version}'} for row in prompt_versions)
    refs.extend({'type': 'retrieval_config', 'id': str(row.id),
                 'detail': 'RAG configuration'} for row in retrieval_configs)
    refs.extend({'type': 'agent_execution', 'id': row.execution_id,
                 'detail': row.status} for row in agent_runs)
    refs.extend({'type': 'evaluation_record', 'id': str(row.id),
                 'detail': row.evaluation_dataset or 'evaluation run'}
                for row in evaluation_rows)
    refs.extend({'type': 'artifact', 'id': str(row.id),
                 'detail': row.original_filename} for row in artifacts)
    refs.extend({'type': 'milestone', 'id': row.milestone_id,
                 'detail': 'completed deliverable'} for row in milestones)

    submission = _submission(project)
    for field in ('repository_url', 'demo_url', 'checks_url'):
        if submission.get(field):
            refs.append({'type': field, 'id': str(submission[field])[:500],
                         'detail': 'project submission URL'})

    return {
        'domain': 'ai-engineering',
        'project_key': module_id,
        'automated_checks': {
            'source': 'ai-engineering:stored-artifacts',
            'checks': checks,
        },
        'rubric_feedback': _rubric_feedback(project),
        'evidence_refs': refs,
    }


__all__ = ['EvidenceError', 'build_evidence', 'module_by_id']
