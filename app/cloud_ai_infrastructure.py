"""Independent catalog for the Cloud & AI Infrastructure specialization.

Lesson content is validated on load: a ready lesson must carry the same study
apparatus as the other pathways (outcomes, mental model, worked example, common
mistakes, key terms and checkpoint answers). Broken or thin content therefore
fails loudly instead of producing a hollow lesson page.
"""

from functools import lru_cache
import json
from pathlib import Path


PATHWAY_PATH = Path(__file__).parent / 'data' / 'cloud_ai_infrastructure_pathway.json'
PATHWAY_ID = 'cloud-ai-infrastructure'


def _text(value, label, minimum=1):
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f'{label} must be text of at least {minimum} characters')
    return value.strip()


def _text_list(value, label, minimum=1):
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f'{label} must be a list of at least {minimum} items')
    for item in value:
        _text(item, f'{label} item')
    return value


def _validate_lesson(module_id, lesson, expected_id):
    lesson_id = lesson.get('id', '')
    if lesson_id != expected_id:
        raise ValueError(f'{module_id}: expected lesson {expected_id}, got {lesson_id!r}')
    status = lesson.get('status')
    if status not in ('pending', 'ready'):
        raise ValueError(f'{lesson_id}: status must be pending|ready, got {status!r}')
    if status == 'pending':
        if any(lesson.get(field) for field in ('sections', 'quiz', 'goal', 'outcomes')):
            raise ValueError(f'{lesson_id} is pending but carries learner-facing content')
        return
    _text(lesson.get('goal'), f'{lesson_id} goal', minimum=20)
    study = lesson.get('study_minutes')
    if not isinstance(study, (int, float)) or isinstance(study, bool) or not 5 <= study <= 240:
        raise ValueError(f'{lesson_id}: study_minutes must be between 5 and 240')
    sections = lesson.get('sections')
    if not isinstance(sections, list) or len(sections) < 2:
        raise ValueError(f'{lesson_id}: ready lessons need at least two sections')
    headings = []
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError(f'{lesson_id}: sections must be objects')
        heading = _text(section.get('heading'), f'{lesson_id} section heading')
        headings.append(heading.casefold())
        body = section.get('body')
        if not isinstance(body, list) or len(body) < 2:
            raise ValueError(f'{lesson_id}: each section needs at least two paragraphs')
        for paragraph in body:
            _text(paragraph, f'{lesson_id} paragraph', minimum=20)
    if len(set(headings)) != len(headings):
        raise ValueError(f'{lesson_id}: section headings must be unique')
    _text(lesson.get('task'), f'{lesson_id} task', minimum=40)
    quiz = lesson.get('quiz')
    if not isinstance(quiz, dict):
        raise ValueError(f'{lesson_id}: ready lessons need a quiz')
    _text(quiz.get('question'), f'{lesson_id} quiz question', minimum=10)
    choices = _text_list(quiz.get('choices'), f'{lesson_id} quiz choices', minimum=2)
    if len({choice.casefold() for choice in choices}) != len(choices):
        raise ValueError(f'{lesson_id}: quiz choices must be unique')
    answer = quiz.get('answer')
    if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(choices):
        raise ValueError(f'{lesson_id}: quiz answer must index a choice')
    _text(quiz.get('explanation'), f'{lesson_id} quiz explanation', minimum=20)

    # Depth parity with the shared foundations and ML lesson surfaces.
    _text_list(lesson.get('outcomes'), f'{lesson_id} outcomes', minimum=2)
    _text(lesson.get('mental_model'), f'{lesson_id} mental model', minimum=40)
    for example in _text_list(lesson.get('worked_example'), f'{lesson_id} worked example'):
        _text(example, f'{lesson_id} worked example', minimum=60)
    _text_list(lesson.get('common_mistakes'), f'{lesson_id} common mistakes', minimum=2)
    terms = lesson.get('key_terms')
    if not isinstance(terms, list) or len(terms) < 1 or not all(isinstance(t, dict) for t in terms):
        raise ValueError(f'{lesson_id} needs at least one key term')
    for term in terms:
        _text(term.get('term'), f'{lesson_id} key term')
        _text(term.get('definition'), f'{lesson_id} key term definition')
    checkpoints = lesson.get('checkpoint')
    if (
        not isinstance(checkpoints, list) or len(checkpoints) < 2
        or not all(isinstance(item, dict) for item in checkpoints)
    ):
        raise ValueError(f'{lesson_id} needs at least two checkpoints')
    for checkpoint in checkpoints:
        _text(checkpoint.get('question'), f'{lesson_id} checkpoint question', minimum=10)
        _text(checkpoint.get('answer'), f'{lesson_id} checkpoint answer', minimum=10)


@lru_cache(maxsize=1)
def cloud_ai_infrastructure_pathway():
    with PATHWAY_PATH.open(encoding='utf-8') as source:
        pathway = json.load(source)
    if pathway.get('id') != PATHWAY_ID:
        raise ValueError('Cloud AI infrastructure pathway has an unexpected ID')

    modules = pathway.get('modules')
    if not isinstance(modules, list) or not modules:
        raise ValueError('Cloud AI infrastructure pathway must define modules')
    seen_modules, seen_lessons, numbers = set(), set(), []
    for index, module in enumerate(modules):
        module_id = module.get('id', '')
        if not isinstance(module_id, str) or not module_id.startswith('cai.'):
            raise ValueError(f'{module_id!r} is not a cloud pathway module id')
        if module_id in seen_modules:
            raise ValueError(f'duplicate cloud module {module_id!r}')
        seen_modules.add(module_id)
        number = module.get('number')
        if not isinstance(number, int) or isinstance(number, bool) or number != index:
            raise ValueError(f'{module_id}: module numbers must be 0-based and contiguous')
        numbers.append(number)
        lessons = module.get('lessons')
        if not isinstance(lessons, list) or not lessons:
            raise ValueError(f'{module_id}: no lessons defined')
        for position, lesson in enumerate(lessons, start=1):
            if not isinstance(lesson, dict):
                raise ValueError(f'{module_id}: lessons must be objects')
            lesson_id = lesson.get('id', '')
            if lesson_id in seen_lessons:
                raise ValueError(f'duplicate lesson {lesson_id!r}')
            seen_lessons.add(lesson_id)
            _validate_lesson(module_id, lesson, f'{module_id}.{position:02d}')
    return pathway


def cloud_ai_infrastructure_lessons():
    from app.lesson_videos import attach_curated_video
    out = []
    for module in cloud_ai_infrastructure_pathway()['modules']:
        for lesson in module['lessons']:
            out.append(attach_curated_video(
                {**lesson, 'module_id': module['id'], 'module_title': module['title'],
                 'module_number': module['number']}))
    return out


def get_cloud_ai_infrastructure_lesson(lesson_id):
    return next(
        (lesson for lesson in cloud_ai_infrastructure_lessons() if lesson['id'] == lesson_id),
        None,
    )
