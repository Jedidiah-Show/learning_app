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
        estimated_hours = module.get('estimated_hours')
        if (
            not isinstance(estimated_hours, (int, float))
            or isinstance(estimated_hours, bool)
            or estimated_hours <= 0
        ):
            raise ValueError(f'{module_id} must declare a positive estimated_hours')
        lessons = module.get('lessons')
        if not isinstance(lessons, list) or not lessons:
            raise ValueError(f'{module_id} must define at least one planned lesson')
        for lesson in lessons:
            lesson_id = lesson.get('id', '')
            if not lesson_id.startswith('mle.') or lesson_id in lesson_ids:
                raise ValueError('Machine learning lesson IDs must be unique and namespaced')
            lesson_ids.add(lesson_id)
            if lesson.get('status') == 'ready':
                study_minutes = lesson.get('study_minutes')
                if (
                    not isinstance(study_minutes, (int, float))
                    or isinstance(study_minutes, bool)
                    or study_minutes <= 0
                ):
                    raise ValueError(f'{lesson_id} is ready but has no study estimate')
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


def shared_prerequisites_met(user_id):
    """The shared Python and backend module projects gate the ML pathway."""
    from app.models import CourseProject

    completed = {
        row.module_id for row in CourseProject.query.filter(
            CourseProject.user_id == user_id,
            CourseProject.module_id.in_(['01', '02']),
            CourseProject.completed.is_(True),
        ).all()
    }
    return {'01', '02'}.issubset(completed)


def machine_learning_lesson_is_open(user_id, lesson_id):
    """Whether one pathway lesson may be read or acted on for this learner.

    Mirrors the sequential rules of the specialization route: shared
    prerequisites, then every earlier published lesson, with each earlier
    module's project completed before the next module opens. The same check
    backs lesson pages, bookmarks, and notes so the peripheral features cannot
    reach a lesson the catalog still shows as locked.
    """
    from app.models import MLSpecializationLessonCompletion, MLSpecializationProject

    lesson = get_machine_learning_lesson(lesson_id)
    if not lesson or lesson.get('status') != 'ready' or not shared_prerequisites_met(user_id):
        return False
    pathway = machine_learning_pathway()
    prior_modules = [
        module for module in pathway['modules']
        if module['number'] < lesson['module_number']
        and all(item.get('status') == 'ready' for item in module['lessons'])
    ]
    prior_projects = {
        row.module_id for row in MLSpecializationProject.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID, completed=True
        ).all()
    }
    if any(module['id'] not in prior_projects for module in prior_modules):
        return False
    completed = {
        row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID
        ).all()
    }
    ready_lessons = [
        item for item in machine_learning_lessons() if item.get('status') == 'ready'
    ]
    position = next(
        index for index, item in enumerate(ready_lessons) if item['id'] == lesson_id
    )
    return all(item['id'] in completed for item in ready_lessons[:position])


def record_pathway_review(user_id, lesson):
    """Schedule a missed pathway knowledge check into spaced review.

    The specialization keeps its own quiz format (one fixed check per lesson),
    so its review items are namespaced by pathway instead of by the shared
    ``Quiz``/``QuizResult`` tables. Correct answers reset the interval, which
    matches the shared course behaviour in ``app.routes.quizzes``.
    """
    from datetime import datetime, timezone
    import json as _json
    from app import db
    from app.models import ReviewItem

    quiz = lesson['quiz']
    quiz_id = f'{PATHWAY_ID}:{lesson["id"]}'
    now = datetime.now(timezone.utc)
    item = ReviewItem.query.filter_by(
        user_id=user_id, quiz_id=quiz_id, question_id=lesson['id']
    ).first()
    if item is None:
        item = ReviewItem(
            user_id=user_id, quiz_id=quiz_id, question_id=lesson['id'],
            subject_id=PATHWAY_ID, question=quiz['question'],
            options=_json.dumps(quiz['choices'], ensure_ascii=False),
            correct_index=quiz['answer'], explanation=quiz['explanation'],
            due_at=now, interval_days=1, repetitions=0, active=True,
            pathway_id=PATHWAY_ID,
        )
        db.session.add(item)
    else:
        item.question = quiz['question']
        item.options = _json.dumps(quiz['choices'], ensure_ascii=False)
        item.correct_index = quiz['answer']
        item.explanation = quiz['explanation']
        item.due_at = now
        item.interval_days = 1
        item.repetitions = 0
        item.active = True
        item.pathway_id = PATHWAY_ID
    db.session.commit()
    return item


def ml_pathway_pacing(user_id, weekly_hours=None):
    """Derive an ML-scoped plan from the learner's available weekly hours.

    The pathway deliberately reuses the onboarding answer (``CoursePlan.weekly_hours``)
    instead of asking again, but never merges into the AI course plan: the
    returned milestones are ML-module scoped and are only rendered on pathway
    surfaces. Modules stay contiguous and in authored order, and no ML module
    is ever dropped or reordered to make the schedule fit.
    """
    import math
    from app.models import (
        CoursePlan, MLSpecializationLessonCompletion, MLSpecializationProject,
    )

    if weekly_hours is None:
        plan = CoursePlan.query.filter_by(user_id=user_id).first()
        weekly_hours = plan.weekly_hours if plan and plan.weekly_hours else None
    if (
        not isinstance(weekly_hours, int) or isinstance(weekly_hours, bool)
        or weekly_hours <= 0
    ):
        weekly_hours = 6
    pathway = machine_learning_pathway()
    completed = {
        row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID
        ).all()
    }
    completed_projects = {
        row.module_id for row in MLSpecializationProject.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID, completed=True
        ).all()
    }
    modules = []
    total_hours = 0.0
    for module in pathway['modules']:
        hours = float(module.get('estimated_hours') or 0)
        total_hours += hours
        lessons = module['lessons']
        done_lessons = sum(lesson['id'] in completed for lesson in lessons)
        total_lessons = len(lessons)
        project_done = module['id'] in completed_projects
        modules.append({
            'id': module['id'], 'number': module['number'],
            'title': module['title'], 'estimated_hours': round(hours, 1),
            'reading_hours': round(
                sum(lesson.get('study_minutes') or 0 for lesson in lessons) / 60, 1
            ),
            'project_hours': round(hours - sum(
                (lesson.get('study_minutes') or 0) for lesson in lessons
            ) / 60, 1),
            'completed_lessons': done_lessons, 'total_lessons': total_lessons,
            'project_completed': project_done,
            'complete': bool(total_lessons and done_lessons == total_lessons and project_done),
            'percent': round(done_lessons / total_lessons * 100) if total_lessons else 0,
        })
    weeks = math.ceil(total_hours / weekly_hours) if total_hours else 0
    months = max(1, math.ceil(weeks / 4.345)) if weeks else 0
    seen_complete = True
    for index, item in enumerate(modules):
        if item['complete']:
            item['status'] = 'Complete'
        elif seen_complete:
            item['status'] = 'In progress'
            seen_complete = False
        else:
            item['status'] = 'Up next'
    return {
        'pathway_id': PATHWAY_ID,
        'weekly_hours': weekly_hours,
        'total_hours': round(total_hours, 1),
        'estimated_weeks': weeks,
        'estimated_months': months,
        # Catch-up time is metadata, never an extra month (same rule as the
        # shared course milestones).
        'review_hours': round(total_hours * 0.2, 1),
        'modules': modules,
    }


def ml_module_progress(user_id, completed=None, projects=None):
    """Per-module lesson and project progress for the ML pathway.

    Shared by the specialization page and the dashboard's curriculum grid so
    both always report the same numbers for the same module. Callers that
    already hold the completion rows may pass them to avoid a second query.
    """
    from app.models import MLSpecializationLessonCompletion, MLSpecializationProject

    if completed is None:
        completed = {
            row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
                user_id=user_id, pathway_id=PATHWAY_ID
            ).all()
        }
    if projects is None:
        projects = {
            row.module_id: row for row in MLSpecializationProject.query.filter_by(
                user_id=user_id, pathway_id=PATHWAY_ID
            ).all()
        }
    module_progress = {}
    for module in machine_learning_pathway()['modules']:
        module_lessons = [lesson['id'] for lesson in module['lessons']]
        project = projects.get(module['id'])
        module_progress[module['id']] = {
            'completed_lessons': sum(
                lesson_id in completed for lesson_id in module_lessons
            ),
            'total_lessons': len(module_lessons),
            'project_completed': bool(project and project.completed),
        }
    return module_progress


def ml_pathway_overview(user_id):
    """Summarise one learner's specialization standing for cross-page cards.

    Deliberately read-only and independent of the shared course progress so
    the dashboard can show the pathway without touching pacing or milestones.
    """
    from app.models import (
        CourseProject, MLSpecializationLessonCompletion, MLSpecializationProject,
    )

    pathway = machine_learning_pathway()
    prerequisites_met = CourseProject.query.filter(
        CourseProject.user_id == user_id,
        CourseProject.module_id.in_(['01', '02']),
        CourseProject.completed.is_(True),
    ).count() >= 2
    completed = {
        row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID
        ).all()
    }
    ready_lessons = [
        lesson for lesson in machine_learning_lessons() if lesson.get('status') == 'ready'
    ]
    project_modules = {
        row.module_id for row in MLSpecializationProject.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID, completed=True
        ).all()
    }
    ready_modules = [
        module for module in pathway['modules']
        if all(lesson.get('status') == 'ready' for lesson in module['lessons'])
    ]
    if prerequisites_met:
        next_lesson = next(
            (lesson for lesson in ready_lessons if lesson['id'] not in completed),
            None,
        )
    else:
        next_lesson = None
    return {
        'title': pathway['title'],
        'prerequisites_met': prerequisites_met,
        'completed_lessons': sum(lesson['id'] in completed for lesson in ready_lessons),
        'total_lessons': len(ready_lessons),
        'projects_completed': len(project_modules),
        'total_projects': len(ready_modules),
        'complete': bool(
            prerequisites_met
            and all(lesson['id'] in completed for lesson in ready_lessons)
            and all(module['id'] in project_modules for module in ready_modules)
        ),
        'next_lesson_id': next_lesson['id'] if next_lesson else None,
        'next_lesson_title': next_lesson['title'] if next_lesson else None,
    }
