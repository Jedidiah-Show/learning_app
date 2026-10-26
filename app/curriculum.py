"""Read-only access to the versioned RuachAI course bundled with the app."""

from functools import lru_cache
import json
from pathlib import Path

from app.videos import build_lesson_video


CURRICULUM_PATH = Path(__file__).parent / 'data' / 'dynamoai_curriculum.json'


@lru_cache(maxsize=1)
def curriculum():
    with CURRICULUM_PATH.open(encoding='utf-8') as source:
        data = json.load(source)
    data['course']['title'] = 'RuachAI Engineering Course'
    data['course']['description'] = (
        'The RuachAI engineering course: 13 modules and 201 lessons, '
        'from Python and backend engineering through production AI systems.'
    )
    resources_path = Path(__file__).parent / 'data' / 'dynamoai_resources.json'
    with resources_path.open(encoding='utf-8') as source:
        resources = json.load(source)
    modules = data.get('modules', [])
    lessons = data.get('lessons', [])
    if len(lessons) != data.get('course', {}).get('total_lessons'):
        raise ValueError('RuachAI curriculum lesson count does not match its manifest')
    module_ids = {module['id'] for module in modules}
    if any(lesson.get('module_id') not in module_ids for lesson in lessons):
        raise ValueError('RuachAI curriculum contains a lesson with an unknown module')
    data['_module_map'] = {module['id']: module for module in modules}
    data['_lesson_map'] = {lesson['id']: lesson for lesson in lessons}
    for module in modules:
        module['resources'] = resources.get(f"module:{module['id']}", {})
    for index, lesson in enumerate(lessons):
        lesson['_ordinal'] = index + 1
        lesson['_module'] = data['_module_map'][lesson['module_id']]
        lesson['resources'] = resources.get(lesson['id'], {})
        lesson['video'] = build_lesson_video(lesson['resources'].get('video'))
    return data


def all_modules():
    return curriculum()['modules']


def all_lessons():
    return curriculum()['lessons']


def get_module(module_id):
    return curriculum()['_module_map'].get(str(module_id))


def get_lesson(lesson_id):
    return curriculum()['_lesson_map'].get(str(lesson_id))


def lesson_ordinal(lesson_id):
    lesson = get_lesson(lesson_id)
    return lesson['_ordinal'] if lesson else None


def module_lessons(module_id):
    module = get_module(module_id)
    return module['lessons'] if module else []


def lesson_context(lesson):
    """Return structured lesson material without duplicated PDF page text."""
    excluded = {'pages', '_ordinal', '_module', 'video'}
    return {key: value for key, value in lesson.items() if key not in excluded}
