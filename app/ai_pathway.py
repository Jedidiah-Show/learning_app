"""Independent catalog for the AI Engineering specialization.

This manifest loads ``ai_engineering_curriculum.json`` and stays fully
separate from the Machine Learning pathway: AI Engineering and Machine
Learning never depend on one another, and Shared Foundations is the only
allowed shared curriculum dependency.
"""

from functools import lru_cache
import json
from pathlib import Path

PATHWAY_PATH = Path(__file__).parents[1] / 'ai_engineering_curriculum.json'
PATHWAY_ID = 'ai-engineering'


@lru_cache(maxsize=1)
def ai_engineering_pathway():
    """Load and validate the standalone AI Engineering pathway manifest."""
    with PATHWAY_PATH.open(encoding='utf-8') as source:
        pathway = json.load(source)

    if pathway.get('id') != PATHWAY_ID:
        raise ValueError('AI Engineering pathway has an unexpected ID')
    modules = pathway.get('modules')
    if not isinstance(modules, list) or not modules:
        raise ValueError('AI Engineering pathway must define modules')

    module_ids = set()
    lesson_ids = set()
    module_numbers = set()
    for module in modules:
        module_id = module.get('id', '')
        if not module_id.startswith('ai.') or module_id in module_ids:
            raise ValueError('AI Engineering module IDs must be unique and namespaced')
        number = module.get('number')
        if not isinstance(number, int) or isinstance(number, bool) or number in module_numbers:
            raise ValueError('AI Engineering modules must have unique integer numbers')
        module_ids.add(module_id)
        module_numbers.add(number)
        lessons = module.get('lessons')
        if not isinstance(lessons, list) or not lessons:
            raise ValueError(f'{module_id} must define at least one lesson')
        for lesson in lessons:
            lesson_id = lesson.get('id', '')
            if not lesson_id.startswith(f'{module_id}.') or lesson_id in lesson_ids:
                raise ValueError(f'{module_id} lesson IDs must be unique and namespaced')
            lesson_ids.add(lesson_id)

    return pathway


def ai_engineering_project_module_ids():
    """Pathway modules that carry project work (those with lessons)."""
    return {
        module['id'] for module in ai_engineering_pathway()['modules']
        if module.get('lessons')
    }
