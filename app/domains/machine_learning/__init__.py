"""Machine Learning Engineering domain rules.

Independent from the AI Engineering domain. Deterministic report checks and
evaluation evidence mappers here read ML specialization records only.
"""

from app.domains.machine_learning.competencies import (
    ML_COMPETENCIES,
    ML_LESSON_COMPETENCIES,
    ML_PROJECT_COMPETENCIES,
)
from app.domains.machine_learning.service import (
    are_previous_projects_complete,
    get_completed_ml_modules,
    get_evaluation_evidence,
    get_ml_competencies,
    get_ml_lesson_completions,
    get_ml_module,
    get_ml_project_record,
    get_or_create_ml_project,
    is_module_lessons_complete,
    record_ml_lesson_completion,
    validate_report,
)

__all__ = [
    'get_ml_module',
    'get_ml_competencies',
    'validate_report',
    'get_ml_project_record',
    'get_or_create_ml_project',
    'get_evaluation_evidence',
    'get_completed_ml_modules',
    'get_ml_lesson_completions',
    'record_ml_lesson_completion',
    'is_module_lessons_complete',
    'are_previous_projects_complete',
    'ML_COMPETENCIES',
    'ML_LESSON_COMPETENCIES',
    'ML_PROJECT_COMPETENCIES',
]
