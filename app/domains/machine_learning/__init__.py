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
    get_evaluation_evidence,
    get_ml_competencies,
    get_ml_module,
    get_ml_project_record,
    validate_report,
)

__all__ = [
    'get_ml_module',
    'get_ml_competencies',
    'validate_report',
    'get_ml_project_record',
    'get_evaluation_evidence',
    'ML_COMPETENCIES',
    'ML_LESSON_COMPETENCIES',
    'ML_PROJECT_COMPETENCIES',
]
