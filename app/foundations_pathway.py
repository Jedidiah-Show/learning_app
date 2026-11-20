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


@lru_cache(maxsize=1)
def shared_foundations_pathway():
    """Load and validate the Shared Foundations lesson manifest."""
    with PATHWAY_PATH.open(encoding='utf-8') as source:
        pathway = json.load(source)

    if pathway.get('id') != PATHWAY_ID:
        raise ValueError('Shared Foundations manifest has an unexpected ID')

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
    for module in modules:
        module_id = module.get('id', '')
        if module_id not in registry_modules:
            raise ValueError(f'{module_id!r} is not a canonical Shared Foundations module')
        if module_id in seen_module_ids:
            raise ValueError(f'duplicate module {module_id!r}')
        seen_module_ids.add(module_id)
        canonical = registry_modules[module_id]
        if module.get('title') != canonical['title']:
            raise ValueError(
                f'{module_id}: title drift from canonical manifest: '
                f'{module.get("title")!r} != {canonical["title"]!r}'
            )
        for lesson in module.get('lessons', []):
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
                if lesson.get('sections') or lesson.get('quiz') or lesson.get('goal'):
                    raise ValueError(
                        f'{lesson_id} is pending but carries content; '
                        f'review and set status to "ready" explicitly'
                    )
            else:
                _validate_ready_lesson(lesson)
    if seen_lesson_ids != registry_lessons:
        missing = registry_lessons - seen_lesson_ids
        raise ValueError(f'Shared Foundations manifest is missing lessons: {sorted(missing)}')
    return pathway


def _validate_ready_lesson(lesson):
    lesson_id = lesson['id']
    study_minutes = lesson.get('study_minutes')
    if (
        not isinstance(study_minutes, (int, float))
        or isinstance(study_minutes, bool)
        or study_minutes <= 0
    ):
        raise ValueError(f'{lesson_id} is ready but has no study estimate')
    sections = lesson.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ValueError(f'{lesson_id} is ready but has no sections')
    for section in sections:
        if (
            not isinstance(section, dict)
            or not isinstance(section.get('heading'), str)
            or not section['heading'].strip()
            or not isinstance(section.get('body'), list)
            or not section['body']
            or not all(isinstance(p, str) and p.strip() for p in section['body'])
        ):
            raise ValueError(f'{lesson_id}: every section needs a heading and content paragraphs')
    if not isinstance(lesson.get('goal'), str) or not lesson['goal'].strip():
        raise ValueError(f'{lesson_id} is ready but has no goal')
    quiz = lesson.get('quiz')
    if (
        not isinstance(quiz, dict)
        or not isinstance(quiz.get('question'), str)
        or not quiz['question'].strip()
        or not isinstance(quiz.get('choices'), list)
        or len(quiz['choices']) < 2
        or not all(isinstance(c, str) and c.strip() for c in quiz['choices'])
        or not isinstance(quiz.get('answer'), int)
        or isinstance(quiz.get('answer'), bool)
        or not 0 <= quiz['answer'] < len(quiz['choices'])
        or not isinstance(quiz.get('explanation'), str)
        or not quiz['explanation'].strip()
    ):
        raise ValueError(f'{lesson_id} is ready but its quiz is invalid')


def shared_foundations_lessons():
    """Return lessons in module order, enriched with module metadata."""
    return [
        {**lesson, 'module_id': module['id'], 'module_title': module['title'],
         'module_number': module['number']}
        for module in shared_foundations_pathway()['modules']
        for lesson in module['lessons']
    ]


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


def foundation_completed_lesson_ids(user_id):
    """Canonical foundation completions, independent of any pathway lesson.

    Existing ``LessonCompletion`` rows with ``sf.*`` ids are mirrored once
    (idempotently) so learners keep progress earned before this dedicated
    table existed. No other LessonCompletion row is consulted.
    """
    from app import db
    from app.models import FoundationLessonProgress, LessonCompletion, utcnow

    records = FoundationLessonProgress.query.filter_by(user_id=user_id).all()
    completed = {row.lesson_id for row in records}
    legacy_rows = LessonCompletion.query.filter(
        LessonCompletion.user_id == user_id,
        LessonCompletion.completed.is_(True),
        LessonCompletion.lesson_id.like('sf.%'),
    ).all()
    missing = [row for row in legacy_rows if row.lesson_id not in completed]
    if missing:
        for row in missing:
            db.session.add(FoundationLessonProgress(
                user_id=user_id, lesson_id=row.lesson_id,
                completed_at=row.completed_at or utcnow(),
            ))
        db.session.commit()
        completed.update(row.lesson_id for row in missing)
    return completed


def mark_foundation_lesson_complete(user_id, lesson_id):
    """Persist a foundation lesson completion in the foundation-only table."""
    from app import db
    from app.models import FoundationLessonProgress, utcnow

    row = FoundationLessonProgress.query.filter_by(
        user_id=user_id, lesson_id=lesson_id,
    ).first()
    if row is None:
        db.session.add(FoundationLessonProgress(
            user_id=user_id, lesson_id=lesson_id, completed_at=utcnow(),
        ))
        db.session.commit()


def foundation_lesson_is_open(user_id, lesson_id):
    """A foundation lesson opens only when every earlier foundation lesson is complete.

    No pathway lesson, module project, enrolment state, or legacy course
    content can lock or unlock a Shared Foundations lesson.
    """
    completed = foundation_completed_lesson_ids(user_id)
    chain = shared_foundations_lessons()
    for earlier in chain:
        if earlier['id'] == lesson_id:
            return True
        if earlier['id'] not in completed:
            return False
    return False


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
