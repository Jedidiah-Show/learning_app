"""AI Engineering domain rules.

Independent from the Machine Learning domain. Evaluation evidence mappers here
read AI specialization records only and never credit ML competencies.
"""

from app.domains.ai_engineering.service import (
    get_ai_competencies,
    get_ai_module,
    get_ai_project_record,
    get_ai_project_records,
    get_evaluation_evidence,
    get_or_create_ai_project,
)

__all__ = [
    'get_ai_module',
    'get_ai_competencies',
    'get_ai_project_record',
    'get_or_create_ai_project',
    'get_ai_project_records',
    'get_evaluation_evidence',
]
