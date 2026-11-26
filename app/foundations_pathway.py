"""Standalone Shared Foundations lesson catalogue.

The Shared Foundations pathway is the only curriculum shared by both
specialisations. This module loads the lesson *content* manifest
(``app/data/shared_foundations_lessons.json``) and validates it against the
canonical curriculum registry, so structural IDs can never drift between the
two files.

Lesson status lifecycle: ``pending`` (seeded, no learner-facing content) →
``ready`` (human-authored and reviewed; full sections/quiz present). A ready
lesson that fails content validation fails app startup loudly instead of
rendering a broken page.
"""

import json
from functools import lru_cache
from pathlib import Path

PATHWAY_PATH = Path(__file__).parent / 'data' / 'shared_foundations_lessons.json'
PATHWAY_ID = 'shared-foundations'

# Content floors. A ready lesson is learner-facing, so thin content fails the
# manifest check at startup instead of producing a hollow lesson page.
MIN_SECTIONS = 2
MIN_PARAGRAPHS_PER_SECTION = 2
MIN_PARAGRAPH_CHARS = 20
MIN_GOAL_CHARS = 60
MIN_TAKEAWAY_CHARS = 40
MIN_TASK_CHARS = 80
MIN_QUIZ_CHOICES = 2
MAX_QUIZ_CHOICES = 6
MAX_STUDY_MINUTES = 240
MIN_WORKED_EXAMPLE_CHARS = 60
MIN_KEY_TERMS = 1
MIN_CHECKPOINTS = 2


@lru_cache(maxsize=1)
def shared_foundations_pathway():
    """Load and validate the Shared Foundations lesson manifest."""
    with PATHWAY_PATH.open(encoding='utf-8') as source:
        pathway = json.load(source)

    if pathway.get('id') != PATHWAY_ID:
        raise ValueError('Shared Foundations manifest has an unexpected ID')
    if pathway.get('pathway_id') not in (None, PATHWAY_ID):
        raise ValueError('Shared Foundations manifest has an unexpected pathway_id')

    # Structural validation and cross-check against the canonical registry.
    from app.curriculum_registry import registry
    domain = registry.get_domain(PATHWAY_ID)
    registry_modules = {module['id']: module for module in domain.modules}
    registry_lessons = {
        lesson['id'] for module in domain.modules for lesson in module['lessons']
    }

    modules = pathway.get('modules')
    if not isinstance(modules, list) or not modules:
        raise ValueError('Shared Foundations manifest must define modules')

    seen_module_ids = set()
    seen_lesson_ids = set()
    module_numbers = []
    for module in modules:
        module_id = module.get('id', '')
        if module_id not in registry_modules:
            raise ValueError(f'{module_id!r} is not a canonical Shared Foundations module')
        if module_id in seen_module_ids:
            raise ValueError(f'duplicate module {module_id!r}')
        seen_module_ids.add(module_id)
        canonical = registry_modules[module_id]
        module_numbers.append(module.get('number'))
        _validate_module(module, canonical, registry_modules)
        for lesson in module.get('lessons') or []:
            lesson_id = lesson.get('id', '')
            if lesson_id not in registry_lessons:
                raise ValueError(f'{lesson_id!r} is not a canonical Shared Foundations lesson')
            if lesson_id in seen_lesson_ids:
                raise ValueError(f'duplicate lesson {lesson_id!r}')
            seen_lesson_ids.add(lesson_id)
            canonical_lesson = next(
                l for m in domain.modules for l in m['lessons'] if l['id'] == lesson_id
            )
            if lesson.get('title') != canonical_lesson['title']:
                raise ValueError(f'{lesson_id}: title drift from canonical manifest')
            status = lesson.get('status')
            if status not in ('pending', 'ready'):
                raise ValueError(f'{lesson_id}: status must be pending|ready, got {status!r}')
            if status == 'pending':
                if any(lesson.get(field) for field in (
                    'sections', 'quiz', 'goal', 'takeaway', 'task', 'study_minutes',
                )):
                    raise ValueError(
                        f'{lesson_id} is pending but carries content; '
                        f'review and set status to "ready" explicitly'
                    )
            else:
                _validate_ready_lesson(lesson)
    if sorted(module_numbers) != list(range(len(modules))):
        raise ValueError('Shared Foundations module numbers must be 0-based and contiguous')
    if seen_lesson_ids != registry_lessons:
        missing = registry_lessons - seen_lesson_ids
        raise ValueError(f'Shared Foundations manifest is missing lessons: {sorted(missing)}')
    return pathway


def _text(value, label, minimum=1):
    """Return stripped text or fail with a precise manifest error."""
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f'{label} must be text of at least {minimum} characters')
    return value.strip()


def _text_list(value, label, minimum=1, maximum=None):
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f'{label} must be a list of at least {minimum} items')
    if maximum is not None and len(value) > maximum:
        raise ValueError(f'{label} has too many items')
    for item in value:
        _text(item, f'{label} item')
    return value


def _validate_module(module, canonical, registry_modules):
    """Check a content module against its canonical counterpart."""
    module_id = module['id']
    number = module.get('number')
    if (
        not isinstance(number, int) or isinstance(number, bool)
        or number < 0 or number != canonical['number']
    ):
        raise ValueError(f'{module_id}: module number drift from canonical manifest')
    if module.get('title') != canonical['title']:
        raise ValueError(
            f'{module_id}: title drift from canonical manifest: '
            f'{module.get("title")!r} != {canonical["title"]!r}'
        )
    _text(module.get('description'), f'{module_id} description', minimum=20)
    hours = module.get('estimated_hours')
    if (
        not isinstance(hours, (int, float)) or isinstance(hours, bool)
        or not 0 < hours <= 400 or hours != canonical.get('estimated_hours')
    ):
        raise ValueError(f'{module_id}: estimated_hours must match the canonical manifest')
    if set(_text_list(module.get('competencies'), f'{module_id} competencies')) != set(
        canonical.get('competencies') or []
    ):
        raise ValueError(f'{module_id}: competencies drift from canonical manifest')
    prerequisites = _text_list(
        module.get('prerequisites') or [], f'{module_id} prerequisites', minimum=0,
    )
    if prerequisites != list(canonical.get('prerequisites') or []):
        raise ValueError(f'{module_id}: prerequisites drift from canonical manifest')
    if any(prereq not in registry_modules for prereq in prerequisites):
        raise ValueError(f'{module_id}: prerequisite does not resolve to a module')
    # Outcomes drive learner-facing copy in both the catalogue and the API.
    outcomes = _text_list(module.get('outcomes'), f'{module_id} outcomes', minimum=2)
    canonical_outcomes = _text_list(
        canonical.get('outcomes'), f'{module_id} canonical outcomes', minimum=2,
    )
    if outcomes != canonical_outcomes:
        raise ValueError(f'{module_id}: outcomes drift from canonical manifest')

    lessons = module.get('lessons')
    if not isinstance(lessons, list) or not all(isinstance(l, dict) for l in lessons):
        raise ValueError(f'{module_id}: lessons must be a list of objects')
    _text_list([lesson.get('id', '') for lesson in lessons], f'{module_id} lessons')
    canonical_ids = [lesson['id'] for lesson in canonical['lessons']]
    expected_ids = [f'{module_id}.{index:02d}' for index in range(1, len(canonical_ids) + 1)]
    if canonical_ids != expected_ids or [l.get('id') for l in lessons] != canonical_ids:
        raise ValueError(f'{module_id}: lessons must be sequential and match the canonical manifest')


def _validate_ready_lesson(lesson):
    lesson_id = lesson['id']
    study_minutes = lesson.get('study_minutes')
    if (
        not isinstance(study_minutes, (int, float))
        or isinstance(study_minutes, bool)
        or not 5 <= study_minutes <= MAX_STUDY_MINUTES
    ):
        raise ValueError(f'{lesson_id}: ready lessons need a study estimate of 5–{MAX_STUDY_MINUTES} minutes')

    sections = lesson.get('sections')
    if not isinstance(sections, list) or len(sections) < MIN_SECTIONS:
        raise ValueError(f'{lesson_id}: ready lessons need at least {MIN_SECTIONS} sections')
    headings = []
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError(f'{lesson_id}: every section must be an object')
        heading = _text(section.get('heading'), f'{lesson_id} section heading')
        headings.append(heading.casefold())
        paragraphs = section.get('body')
        if not isinstance(paragraphs, list) or len(paragraphs) < MIN_PARAGRAPHS_PER_SECTION:
            raise ValueError(
                f'{lesson_id}: every section needs at least {MIN_PARAGRAPHS_PER_SECTION} paragraphs'
            )
        for paragraph in paragraphs:
            _text(paragraph, f'{lesson_id} section paragraph', minimum=MIN_PARAGRAPH_CHARS)
    if len(set(headings)) != len(headings):
        raise ValueError(f'{lesson_id}: section headings must be unique')

    _text(lesson.get('goal'), f'{lesson_id} goal', minimum=MIN_GOAL_CHARS)
    _text(lesson.get('takeaway'), f'{lesson_id} takeaway', minimum=MIN_TAKEAWAY_CHARS)
    _text(lesson.get('task'), f'{lesson_id} task', minimum=MIN_TASK_CHARS)

    quiz = lesson.get('quiz')
    if not isinstance(quiz, dict):
        raise ValueError(f'{lesson_id} is ready but its quiz is invalid')
    _text(quiz.get('question'), f'{lesson_id} quiz question', minimum=20)
    choices = _text_list(
        quiz.get('choices'), f'{lesson_id} quiz choices',
        minimum=MIN_QUIZ_CHOICES, maximum=MAX_QUIZ_CHOICES,
    )
    if len({choice.casefold() for choice in choices}) != len(choices):
        raise ValueError(f'{lesson_id}: quiz choices must be unique')
    answer = quiz.get('answer')
    if (
        not isinstance(answer, int) or isinstance(answer, bool)
        or not 0 <= answer < len(choices)
    ):
        raise ValueError(f'{lesson_id}: quiz answer must index a choice')
    _text(quiz.get('explanation'), f'{lesson_id} quiz explanation', minimum=40)

    # Legacy 00-02 lessons carried much more scaffolding than the first shared
    # curriculum. A ready foundation lesson must now ship that same depth, so
    # the standalone pathway can never become the thinner copy again.
    _text_list(lesson.get('outcomes'), f'{lesson_id} outcomes', minimum=2)
    _text(lesson.get('mental_model'), f'{lesson_id} mental model', minimum=40)
    for example in _text_list(lesson.get('worked_example'), f'{lesson_id} worked example'):
        _text(example, f'{lesson_id} worked example', minimum=MIN_WORKED_EXAMPLE_CHARS)
    _text_list(lesson.get('common_mistakes'), f'{lesson_id} common mistakes', minimum=2)
    terms = lesson.get('key_terms')
    if (
        not isinstance(terms, list) or len(terms) < MIN_KEY_TERMS
        or not all(isinstance(term, dict) for term in terms)
    ):
        raise ValueError(f'{lesson_id} needs at least one key term')
    for term in terms:
        _text(term.get('term'), f'{lesson_id} key term')
        _text(term.get('definition'), f'{lesson_id} key term definition')
    checkpoints = lesson.get('checkpoint')
    if (
        not isinstance(checkpoints, list) or len(checkpoints) < MIN_CHECKPOINTS
        or not all(isinstance(item, dict) for item in checkpoints)
    ):
        raise ValueError(f'{lesson_id} needs at least {MIN_CHECKPOINTS} checkpoints')
    for checkpoint in checkpoints:
        _text(checkpoint.get('question'), f'{lesson_id} checkpoint question', minimum=10)
        _text(checkpoint.get('answer'), f'{lesson_id} checkpoint answer', minimum=10)
    _text(lesson.get('source_legacy_id'), f'{lesson_id} source legacy id', minimum=3)


def shared_foundations_lessons():
    """Return lessons in module order, enriched with module metadata + curated video."""
    from app.lesson_videos import attach_curated_video
    out = []
    for module in shared_foundations_pathway()['modules']:
        for lesson in module['lessons']:
            out.append(attach_curated_video(
                {**lesson, 'module_id': module['id'], 'module_title': module['title'],
                 'module_number': module['number']}))
    return out


def get_shared_foundations_lesson(lesson_id):
    return next(
        (lesson for lesson in shared_foundations_lessons() if lesson['id'] == lesson_id),
        None,
    )


def foundation_module_of_lesson(lesson_id):
    for module in shared_foundations_pathway()['modules']:
        for lesson in module['lessons']:
            if lesson['id'] == lesson_id:
                return module
    return None


def canonical_foundation_lesson_ids():
    """Every lesson ID this manifest publishes (cached with the manifest)."""
    return frozenset(lesson['id'] for lesson in shared_foundations_lessons())


def foundation_completed_lesson_ids(user_id):
    """Canonical foundation completions, independent of any pathway lesson.

    Existing ``LessonCompletion`` rows with canonical ``sf.*`` ids are mirrored
    once (idempotently) so learners keep progress earned before this dedicated
    table existed. Unknown IDs never enter the foundation table and no other
    LessonCompletion row is consulted.
    """
    from app import db
    from app.models import FoundationLessonProgress, LessonCompletion, utcnow

    canonical = canonical_foundation_lesson_ids()
    records = FoundationLessonProgress.query.filter_by(user_id=user_id).all()
    completed = {row.lesson_id for row in records if row.lesson_id in canonical}
    legacy_rows = LessonCompletion.query.filter(
        LessonCompletion.user_id == user_id,
        LessonCompletion.completed.is_(True),
        LessonCompletion.lesson_id.like('sf.%'),
    ).all()
    missing = [
        row for row in legacy_rows
        if row.lesson_id in canonical and row.lesson_id not in completed
    ]
    if missing:
        for row in missing:
            db.session.add(FoundationLessonProgress(
                user_id=user_id, lesson_id=row.lesson_id,
                completed_at=row.completed_at or utcnow(),
            ))
        db.session.commit()
        completed.update(row.lesson_id for row in missing)
    return completed


def mark_foundation_lesson_complete(user_id, lesson_id, commit=True):
    """Persist a foundation lesson completion in the foundation-only table.

    Pass ``commit=False`` when the caller owns the surrounding transaction, so
    the pathway completion and its foundation mirror land atomically.
    """
    if lesson_id not in canonical_foundation_lesson_ids():
        raise ValueError(f'{lesson_id!r} is not a canonical Shared Foundations lesson')
    from app import db
    from app.models import FoundationLessonProgress, utcnow

    row = FoundationLessonProgress.query.filter_by(
        user_id=user_id, lesson_id=lesson_id,
    ).first()
    if row is None:
        db.session.add(FoundationLessonProgress(
            user_id=user_id, lesson_id=lesson_id, completed_at=utcnow(),
        ))
        if commit:
            db.session.commit()
    elif commit:
        db.session.commit()


def foundation_open_lesson_ids(user_id):
    """Completed lessons plus the first incomplete one are open.

    Computing the open set once lets catalogues and APIs mark every other
    lesson as locked without a database round trip per lesson.
    """
    completed = foundation_completed_lesson_ids(user_id)
    open_ids = set(completed)
    for lesson in shared_foundations_lessons():
        if lesson['id'] not in completed:
            open_ids.add(lesson['id'])
            break
    return frozenset(open_ids)


def foundation_lesson_is_open(user_id, lesson_id):
    """A foundation lesson opens only when every earlier foundation lesson is complete.

    No pathway lesson, module project, enrolment state, or legacy course
    content can lock or unlock a Shared Foundations lesson.
    """
    return lesson_id in foundation_open_lesson_ids(user_id)


def foundation_completion_state(user_id):
    completed = foundation_completed_lesson_ids(user_id)
    modules = []
    for module in shared_foundations_pathway()['modules']:
        lessons = module['lessons']
        ready = [l for l in lessons if l['status'] == 'ready']
        modules.append({
            'id': module['id'],
            'title': module['title'],
            'total': len(lessons),
            'ready': len(ready),
            'completed': sum(1 for l in lessons if l['id'] in completed),
        })
    return {'completed': completed, 'modules': modules}


def foundation_progress_summary(user_id):
    """One read model for every surface showing foundation progress.

    Lessons unlock strictly in manifest order, so at most one lesson is open:
    the first one not yet completed. Keeping that rule here prevents the API,
    catalogue and lesson page from disagreeing about what a learner can open.
    """
    state = foundation_completion_state(user_id)
    chain = shared_foundations_lessons()
    completed_count = sum(1 for lesson in chain if lesson['id'] in state['completed'])
    total = len(chain)
    next_lesson = next(
        (lesson for lesson in chain if lesson['id'] not in state['completed']), None,
    )
    return {
        'total_lessons': total,
        'completed_lessons': completed_count,
        'percent': round(completed_count / total * 100) if total else 0,
        'complete': total > 0 and completed_count == total,
        'next_lesson': (
            {
                'id': next_lesson['id'],
                'title': next_lesson['title'],
                'module_id': next_lesson['module_id'],
                'module_title': next_lesson['module_title'],
            } if next_lesson else None
        ),
        'modules': state['modules'],
    }
