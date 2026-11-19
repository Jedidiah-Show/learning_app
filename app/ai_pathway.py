"""Independent catalog for the AI Engineering specialization.

This manifest loads ``ai_engineering_curriculum.json`` and stays fully
separate from the Machine Learning pathway: AI Engineering and Machine
Learning never depend on one another, and Shared Foundations is the only
allowed shared curriculum dependency.
"""

from functools import lru_cache

PATHWAY_ID = 'ai-engineering'


@lru_cache(maxsize=1)
def ai_engineering_pathway():
    """Load and validate the standalone AI Engineering pathway manifest.

    Validation and caching are shared with the canonical curriculum registry.
    The returned dict keeps the historical ``modules`` shape.
    """
    from app.curriculum_registry import registry
    domain = registry.get_domain('ai-engineering')
    return {
        'id': domain.id,
        'name': domain.name,
        'description': domain.description,
        'version': domain.version,
        'status': domain.status,
        'learning_objectives': list(domain.learning_objectives),
        'modules': domain.modules,
    }


def ai_engineering_project_module_ids():
    """Pathway modules that carry project work (those with lessons)."""
    return {
        module['id'] for module in ai_engineering_pathway()['modules']
        if module.get('lessons')
    }
