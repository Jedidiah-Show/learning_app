"""Sequential lesson and module-project unlock rules."""

from app.curriculum import all_lessons, all_modules
from app.models import CourseProject, LessonCompletion


def completed_lesson_ids(user):
    return {
        lesson_id for (lesson_id,) in LessonCompletion.query.with_entities(
            LessonCompletion.lesson_id
        ).filter_by(user_id=user.id, completed=True).all()
    }


def completed_project_modules(user):
    return {
        module_id for (module_id,) in CourseProject.query.with_entities(
            CourseProject.module_id
        ).filter_by(user_id=user.id, completed=True).all()
    }


def user_track(user):
    """Return the learner's selected plan track, defaulting to standard."""
    from app.course_data import TRACK_IDS
    from app.models import CoursePlan

    plan = CoursePlan.query.filter_by(user_id=user.id).first()
    if plan and plan.track in TRACK_IDS:
        return plan.track
    return 'standard'


def next_unlocked_lesson(user, completed=None, completed_projects=None):
    action = next_course_action(
        user, completed=completed, completed_projects=completed_projects
    )
    return action['lesson_id'] if action and action['type'] == 'lesson' else None


def next_course_action(user, completed=None, completed_projects=None):
    if completed is None:
        completed = completed_lesson_ids(user)
    if completed_projects is None:
        completed_projects = completed_project_modules(user)
    return _next_course_action(completed, completed_projects)


def _next_course_action(completed, project_modules):
    for module in all_modules():
        if any(lesson['id'] not in completed for lesson in module['lessons']):
            lesson = next(item for item in module['lessons'] if item['id'] not in completed)
            return {'type': 'lesson', 'lesson_id': lesson['id']}
        if module['id'] not in project_modules:
            return {'type': 'project', 'module_id': module['id'],
                    'module_title': module['title'],
                    'module_number': module['number']}
    return None


def lesson_is_available(user, lesson_id, completed=None, completed_projects=None):
    from app.curriculum import get_lesson
    lesson = get_lesson(lesson_id)
    if not lesson:
        return False
    if completed is None:
        completed = completed_lesson_ids(user)
    if completed_projects is None:
        completed_projects = completed_project_modules(user)
    if lesson_id in completed:
        return True
    return lesson_id == next_unlocked_lesson(
        user, completed=completed, completed_projects=completed_projects
    )


def module_project_is_available(user, module_id, completed=None):
    from app.curriculum import get_module
    module = get_module(module_id)
    if not module:
        return False
    if completed is None:
        completed = completed_lesson_ids(user)
    return all(lesson['id'] in completed for lesson in module['lessons'])


def course_progress(user, completed=None, completed_projects=None):
    if completed is None:
        completed = completed_lesson_ids(user)
    if completed_projects is None:
        completed_projects = completed_project_modules(user)
    lessons = all_lessons()
    modules = all_modules()
    # Reuse these sets for all progress fields. Re-querying through
    # next_course_action() and next_unlocked_lesson() made dashboard renders
    # issue the same two completion queries three times.
    action = _next_course_action(completed, completed_projects)
    return {
        'total_lessons': len(lessons),
        'completed_lessons': sum(lesson['id'] in completed for lesson in lessons),
        'next_lesson_id': action['lesson_id'] if action and action['type'] == 'lesson' else None,
        'next_action': action,
        'total_projects': len(modules),
        'completed_projects': sum(module['id'] in completed_projects for module in modules),
        'course_complete': (
            all(lesson['id'] in completed for lesson in lessons)
            and all(module['id'] in completed_projects for module in modules)
        ),
        'recalibration': study_recalibration(user, completed, completed_projects),
        'modules': [
            {
                'id': module['id'], 'number': module['number'],
                'title': module['title'], 'total_lessons': len(module['lessons']),
                'estimated_hours': module.get('estimated_hours', 0),
                'completed_lessons': sum(
                    lesson['id'] in completed for lesson in module['lessons']
                ),
            }
            for module in all_modules()
        ],
    }


def monthly_milestone_progress(progress, completed_projects, track='standard'):
    """Group sequential modules into the selected track's monthly milestones."""
    from app.course_data import milestones_for

    modules = {module['id']: module for module in progress['modules']}
    result = []
    for milestone in milestones_for(track):
        grouped = [modules[module_id] for module_id in milestone['modules']]
        done_lessons = sum(item['completed_lessons'] for item in grouped)
        total_lessons = sum(item['total_lessons'] for item in grouped)
        estimated_hours = round(
            sum(item.get('estimated_hours', 0) for item in grouped), 1
        )
        reading_hours = round(
            sum(
                sum(
                    (lesson.get('study_minutes') or 0) for lesson in item.get('lessons') or []
                ) / 60
                for item in grouped
            ),
            1,
        )
        # Catch-up time is metadata for the month, never an extra month.
        review_hours = round(estimated_hours * 0.2, 1)
        done_modules = sum(
            item['completed_lessons'] == item['total_lessons']
            and item['id'] in completed_projects for item in grouped
        )
        complete = done_modules == len(grouped)
        previous_complete = all(item['complete'] for item in result)
        result.append({
            **milestone,
            'complete': complete,
            'status': 'Complete' if complete else (
                'In progress' if previous_complete else 'Up next'
            ),
            'module_titles': [item['title'] for item in grouped],
            'completed_lessons': done_lessons,
            'total_lessons': total_lessons,
            'estimated_hours': estimated_hours,
            'estimated_weekly_hours': round(estimated_hours / 4.345, 1),
            # Asymmetric spread: project work varies more than reading, so the
            # low end is reading-only and the headline figure includes projects.
            'estimated_weekly_hours_low': round(reading_hours / 4.345, 1),
            'review_hours': review_hours,
            'completed_modules': done_modules,
            'total_modules': len(grouped),
            'percent': round(done_lessons / total_lessons * 100) if total_lessons else 0,
        })
    return result


def study_recalibration(user, completed=None, completed_projects=None):
    """Compare observed study minutes against estimates for this learner.

    The comparison is user-scoped: it uses the learner's own
    ``LessonCompletion.time_spent_minutes`` against the curated
    ``_study_minutes`` estimates. It only reports; the learner decides what to
    do with the observed multiplier.
    """
    from app.curriculum import all_lessons
    from app.models import LessonCompletion

    if completed is None:
        completed = completed_lesson_ids(user)
    estimated_minutes = 0.0
    observed_minutes = 0.0
    counted = set()
    for lesson in all_lessons():
        lesson_id = lesson.get('id')
        if lesson_id in counted or lesson_id not in completed:
            continue
        counted.add(lesson_id)
        estimated_minutes += float(lesson.get('study_minutes') or 0)
        row = LessonCompletion.query.filter_by(
            user_id=user.id, lesson_id=lesson_id
        ).first()
        if row is not None and row.time_spent_minutes:
            observed_minutes += float(row.time_spent_minutes)
    estimated_hours = estimated_minutes / 60
    observed_hours = observed_minutes / 60
    multiplier = round(observed_hours / estimated_hours, 2) if estimated_hours > 0 else None
    return {
        'estimated_hours': round(estimated_hours, 1),
        'observed_hours': round(observed_hours, 1),
        'multiplier': multiplier,
        'calibrated': bool(
            multiplier is not None and estimated_hours > 0 and observed_hours > 0
        ),
    }


def next_unlocked_day(user, config=None):
    """Compatibility ordinal for calendar records created before the refactor."""
    lesson_id = next_unlocked_lesson(user)
    if lesson_id is None:
        return len(all_lessons()) + 1
    from app.curriculum import lesson_ordinal
    return lesson_ordinal(lesson_id)


def day_is_available(user, config, day_number):
    if not isinstance(day_number, int) or isinstance(day_number, bool):
        return False
    lessons = all_lessons()
    if day_number < 1 or day_number > len(lessons):
        return False
    return lesson_is_available(user, lessons[day_number - 1]['id'])
