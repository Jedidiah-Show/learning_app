"""Independent catalog for the optional Machine Learning Engineering path.

This manifest deliberately stays outside ``app.curriculum``: that module feeds
the shared AI Engineering course, completion sequence, and pacing plans.
"""

from functools import lru_cache
import json
from pathlib import Path


PATHWAY_PATH = Path(__file__).parent / 'data' / 'machine_learning_pathway.json'
PATHWAY_ID = 'machine-learning-engineering'


@lru_cache(maxsize=1)
def machine_learning_pathway():
    """Load and validate the standalone pathway manifest."""
    with PATHWAY_PATH.open(encoding='utf-8') as source:
        pathway = json.load(source)

    if pathway.get('id') != PATHWAY_ID:
        raise ValueError('Machine learning pathway has an unexpected ID')
    modules = pathway.get('modules')
    if not isinstance(modules, list) or not modules:
        raise ValueError('Machine learning pathway must define modules')

    module_ids = set()
    lesson_ids = set()
    module_numbers = set()
    for module in modules:
        module_id = module.get('id', '')
        if not module_id.startswith('mle.') or module_id in module_ids:
            raise ValueError('Machine learning module IDs must be unique and namespaced')
        number = module.get('number')
        if not isinstance(number, int) or isinstance(number, bool) or number in module_numbers:
            raise ValueError('Machine learning modules must have unique integer numbers')
        module_ids.add(module_id)
        module_numbers.add(number)
        lessons = module.get('lessons')
        if not isinstance(lessons, list) or not lessons:
            raise ValueError(f'{module_id} must define at least one planned lesson')
        for lesson in lessons:
            lesson_id = lesson.get('id', '')
            if not lesson_id.startswith('mle.') or lesson_id in lesson_ids:
                raise ValueError('Machine learning lesson IDs must be unique and namespaced')
            lesson_ids.add(lesson_id)
            if lesson.get('status') == 'ready':
                sections = lesson.get('sections')
                quiz = lesson.get('quiz')
                if (
                    not isinstance(lesson.get('title'), str) or not lesson['title'].strip()
                    or not isinstance(lesson.get('goal'), str) or not lesson['goal'].strip()
                    or not isinstance(sections, list) or not sections
                    or any(
                        not isinstance(section, dict)
                        or not isinstance(section.get('heading'), str)
                        or not section['heading'].strip()
                        or not isinstance(section.get('body'), list)
                        or not section['body']
                        or not all(isinstance(paragraph, str) and paragraph.strip()
                                   for paragraph in section['body'])
                        for section in sections
                    )
                    or not isinstance(quiz, dict)
                    or not isinstance(quiz.get('question'), str)
                    or not quiz['question'].strip()
                    or not isinstance(quiz.get('choices'), list)
                    or len(quiz['choices']) < 2
                    or not all(isinstance(choice, str) and choice.strip()
                               for choice in quiz['choices'])
                    or not isinstance(quiz.get('answer'), int)
                    or isinstance(quiz.get('answer'), bool)
                    or not 0 <= quiz['answer'] < len(quiz['choices'])
                    or not isinstance(quiz.get('explanation'), str)
                    or not quiz['explanation'].strip()
                ):
                    raise ValueError(f'{lesson_id} is ready but its lesson or quiz content is invalid')
    return pathway


def machine_learning_lessons():
    """Return pathway lessons in their authored module order."""
    return [
        {**lesson, 'module_id': module['id'], 'module_title': module['title'],
         'module_number': module['number']}
        for module in machine_learning_pathway()['modules']
        for lesson in module['lessons']
    ]


def get_machine_learning_lesson(lesson_id):
    return next(
        (lesson for lesson in machine_learning_lessons() if lesson['id'] == lesson_id),
        None,
    )
