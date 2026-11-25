"""AI Engineering domain service.

Encapsulates AI curriculum rules, competencies, submission validation,
and evidence collection without any cross-domain coupling to ML logic.
"""

from __future__ import annotations

import json
from app.ai_pathway import PATHWAY_ID, ai_engineering_pathway
from app.core.exceptions import EntityNotFoundError, ValidationError
from app.core.extensions import db
from app.domains.ai_engineering.evaluation import build_evidence
from app.models import AISpecializationProject


def get_ai_module(module_id: str) -> dict:
    """Retrieve AI Engineering module definition from the pathway manifest."""
    manifest = ai_engineering_pathway()
    for mod in manifest.get('modules', []):
        if mod.get('id') == module_id:
            return mod
    raise EntityNotFoundError('AI Module', module_id)


def get_ai_competencies(module_id: str) -> list[dict]:
    """Return competencies authored for an AI Engineering module."""
    module = get_ai_module(module_id)
    competencies = []
    for raw in module.get('competencies', []):
        title = str(raw).strip()
        if not title:
            continue
        slug = title.lower().replace(' ', '-')[:64]
        competencies.append({
            'id': f'ai-competency-{slug}',
            'title': title,
            'category': 'AI Engineering',
        })
    return competencies


def get_ai_project_record(user_id: int, module_id: str) -> AISpecializationProject | None:
    """Query stored AI specialization project record for learner."""
    return AISpecializationProject.query.filter_by(
        user_id=user_id,
        module_id=module_id,
    ).first()


def get_or_create_ai_project(user_id: int, module_id: str) -> AISpecializationProject:
    """Retrieve or create AI specialization project record for learner."""
    record = AISpecializationProject.query.filter_by(
        user_id=user_id, pathway_id=PATHWAY_ID, module_id=module_id,
    ).first()
    if record is None:
        record = AISpecializationProject(
            user_id=user_id, pathway_id=PATHWAY_ID,
            module_id=module_id,
        )
        db.session.add(record)
        db.session.commit()
    return record


def get_ai_project_records(user_id: int) -> list[AISpecializationProject]:
    """Query all AI specialization project records for learner."""
    return AISpecializationProject.query.filter_by(
        user_id=user_id,
        pathway_id=PATHWAY_ID,
    ).all()


def get_evaluation_evidence(module_id: str, user_id: int) -> dict:
    """Collect traceable evaluation evidence for an AI Engineering project."""
    return build_evidence(user_id=user_id, module_id=module_id)
