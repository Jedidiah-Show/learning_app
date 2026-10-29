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
    from app.course_blueprint import TRACK_IDS
    from app.models import CoursePlan

    plan = CoursePlan.query.filter_by(user_id=user.id).first()
    if plan and plan.track in TRACK_IDS:
        return plan.track
    return 'standard'


def next_unlocked_lesson(user):
    action = next_course_action(user)
    return action['lesson_id'] if action and action['type'] == 'lesson' else None


def next_course_action(user):
    completed = completed_lesson_ids(user)
    project_modules = completed_project_modules(user)
    return _next_course_action(completed, project_modules)


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


def lesson_is_available(user, lesson_id):
    from app.curriculum import get_lesson
    lesson = get_lesson(lesson_id)
    if not lesson:
        return False
    if lesson_id in completed_lesson_ids(user):
        return True
    unlocked = next_unlocked_lesson(user)
    return lesson_id == unlocked


def module_project_is_available(user, module_id):
    from app.curriculum import get_module
    module = get_module(module_id)
    if not module:
        return False
    completed = completed_lesson_ids(user)
    return all(lesson['id'] in completed for lesson in module['lessons'])


def course_progress(user):
    completed = completed_lesson_ids(user)
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
    from app.course_blueprint import milestones_for

    modules = {module['id']: module for module in progress['modules']}
    result = []
    for milestone in milestones_for(track):
        grouped = [modules[module_id] for module_id in milestone['modules']]
        done_lessons = sum(item['completed_lessons'] for item in grouped)
        total_lessons = sum(item['total_lessons'] for item in grouped)
        estimated_hours = round(
            sum(item.get('estimated_hours', 0) for item in grouped), 1
        )
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
            'completed_modules': done_modules,
            'total_modules': len(grouped),
            'percent': round(done_lessons / total_lessons * 100) if total_lessons else 0,
        })
    return result


def curriculum_days(config=None):
    """Compatibility name for the number of fixed course lessons."""
    return len(all_lessons())


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
