"""Evidence-backed portfolio presentation for M4.

Portfolio entries are derived from verified project evaluations, not from
lesson completion or a completed flag alone. An entry appears only when its
lifecycle is approved/published and its evaluation status is VERIFIED.
Internal rubric evidence stays private; the public showcase uses a whitelist.
"""

from __future__ import annotations

import json

from app.models import AISpecializationProject, MLSpecializationProject, ProjectEvaluation
from app.services.project_competencies import competencies_for, project_title
from app.services.project_evaluation import DOMAINS
from app.services.project_lifecycle import current_stage

VISIBLE_STAGES = frozenset({'approved', 'published'})


def _module(domain, project_key):
    if domain == 'ai-engineering':
        from app.ai_pathway import ai_engineering_pathway
        modules = ai_engineering_pathway()['modules']
    else:
        from app.ml_pathway import machine_learning_pathway
        modules = machine_learning_pathway()['modules']
    return next((module for module in modules if module['id'] == project_key), None)


def _submission_urls(domain, user_id, project_key):
    if domain == 'ai-engineering':
        from app.ai_pathway import PATHWAY_ID
        record = AISpecializationProject.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID, module_id=project_key,
        ).first()
    else:
        from app.ml_pathway import PATHWAY_ID
        record = MLSpecializationProject.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID, module_id=project_key,
        ).first()
    if record is None or not record.submission:
        return {}
    try:
        submission = json.loads(record.submission)
    except (TypeError, ValueError):
        return {}
    if not isinstance(submission, dict):
        return {}
    return {
        field: str(submission[field])[:500]
        for field in ('repository_url', 'demo_url', 'checks_url')
        if isinstance(submission.get(field), str) and submission[field]
    }


def _evaluation_summary(evaluation):
    return {
        'id': evaluation.id,
        'version': evaluation.version,
        'status': evaluation.status,
        'rubric_score': evaluation.rubric_score,
        'lifecycle_stage': evaluation.lifecycle_stage,
        'human_review': evaluation.get_human_review(),
    }


def entries(user_id, *, domain=None, include_private=True):
    """Return evidence-backed portfolio entries for one learner."""
    if domain is not None and domain not in DOMAINS:
        return []
    query = ProjectEvaluation.query.filter_by(
        user_id=int(user_id), status='VERIFIED',
    )
    if domain is not None:
        query = query.filter_by(domain=domain)
    evaluations = query.order_by(
        ProjectEvaluation.domain, ProjectEvaluation.project_key,
        ProjectEvaluation.version.desc(),
    ).all()

    seen = set()
    projects = []
    for evaluation in evaluations:
        identity = (evaluation.domain, evaluation.project_key)
        if identity in seen:
            continue
        stage = current_stage(user_id, evaluation.domain, evaluation.project_key)
        if stage not in VISIBLE_STAGES:
            continue
        seen.add(identity)
        module = _module(evaluation.domain, evaluation.project_key) or {}
        urls = _submission_urls(
            evaluation.domain, user_id, evaluation.project_key
        )
        checks = evaluation.get_automated_checks().get('checks') or []
        projects.append({
            'module': {
                'id': evaluation.project_key,
                'number': module.get('number'),
                'title': module.get('title') or evaluation.project_key,
            },
            'project': {
                'title': project_title(evaluation.domain, evaluation.project_key),
                'brief': module.get('project') or module.get('description') or '',
            },
            'module_title': module.get('title') or evaluation.project_key,
            'domain': evaluation.domain,
            'domain_label': (
                'AI Engineering' if evaluation.domain == 'ai-engineering'
                else 'Machine Learning Engineering'
            ),
            'repository_url': urls.get('repository_url'),
            'demo_url': urls.get('demo_url'),
            'checks_url': urls.get('checks_url') if include_private else None,
            'checks_verified': bool(checks) and all(row['passed'] for row in checks),
            'completed': True,
            'evaluation': _evaluation_summary(evaluation) if include_private else None,
            'verification_status': 'Verified',
            'competencies': [
                item['id'] for item in competencies_for(
                    evaluation.domain, evaluation.project_key
                )
            ],
            'evaluation_id': evaluation.id if include_private else None,
        })
    return projects


__all__ = ['VISIBLE_STAGES', 'entries']
