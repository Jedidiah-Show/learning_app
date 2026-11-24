"""Machine Learning domain service.

Encapsulates ML curriculum rules, competencies, report contract validation,
and evidence collection without any cross-domain coupling to AI logic.
"""

from __future__ import annotations

from app.core.exceptions import EntityNotFoundError, ValidationError
from app.domains.machine_learning.competencies import ML_COMPETENCIES, ML_PROJECT_COMPETENCIES
from app.domains.machine_learning.evaluation import build_evidence
from app.domains.machine_learning.report import module_by_id, report_matches
from app.ml_pathway import PATHWAY_ID, machine_learning_pathway
from app.models import MLSpecializationProject


def get_ml_module(module_id: str) -> dict:
    """Retrieve Machine Learning module definition from the pathway manifest."""
    manifest = machine_learning_pathway()
    for mod in manifest.get('modules', []):
        if mod.get('id') == module_id:
            return mod
    raise EntityNotFoundError('ML Module', module_id)


def get_ml_competencies(module_id: str) -> list[dict]:
    """Return competencies authored for a Machine Learning module."""
    get_ml_module(module_id)
    competency_keys = ML_PROJECT_COMPETENCIES.get(module_id, ())
    result = []
    for key in competency_keys:
        info = ML_COMPETENCIES.get(key, {})
        result.append({
            'id': key,
            'title': info.get('title') or key.replace('-', ' ').title(),
            'category': info.get('category') or 'Machine Learning',
        })
    return result


def validate_report(module_id: str, report_data: dict) -> bool:
    """Validate report data against the published deterministic contract."""
    return report_matches(module_id, report_data)


def get_ml_project_record(user_id: int, module_id: str) -> MLSpecializationProject | None:
    """Query stored ML specialization project record for learner."""
    return MLSpecializationProject.query.filter_by(
        user_id=user_id,
        module_id=module_id,
    ).first()


def get_evaluation_evidence(module_id: str, user_id: int) -> dict:
    """Collect traceable evaluation evidence for a Machine Learning project."""
    return build_evidence(user_id=user_id, module_id=module_id)
