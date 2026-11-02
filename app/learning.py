"""Sequential lesson and module-project unlock rules.

The unlock rules are pathway-aware: a learner who confirmed ``ml`` studies the
shared foundation plus the ML pathway, so their pointer, availability checks,
and progress totals never reach an AI-only module 03-12 lesson.  ``ai``,
``undecided``, and unset destinations keep the full AI Engineering course.
"""

from app.curriculum import all_modules
from app.models import CourseProject, LessonCompletion


def _scope(user, destination):
    """Resolve this learner's destination once for a bundle of queries."""
    from app.pathway_scope import destination_for

    return destination_for(user) if destination is None else destination


def _merged_completions(user, destination, completed, project_modules):
    """AI completions plus this pathway's completions.

    Module and lesson IDs are namespaced (``00``-``12`` vs ``mle.*``), so the
    union is safe and lets one pointer walk the foundation into the pathway.
    """
    from app.pathway_scope import is_ml, ml_completion_state

    if not is_ml(destination):
        return set(completed), set(project_modules)
    ml_lessons, ml_projects = ml_completion_state(user.id)
    return set(completed) | ml_lessons, set(project_modules) | ml_projects


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


def next_unlocked_lesson(user, completed=None, completed_projects=None,
                         destination=None):
    action = next_course_action(
        user, completed=completed, completed_projects=completed_projects,
        destination=destination,
    )
    return action['lesson_id'] if action and action['type'] == 'lesson' else None


def next_course_action(user, completed=None, completed_projects=None,
                       destination=None):
    destination = _scope(user, destination)
    if completed is None:
        completed = completed_lesson_ids(user)
    if completed_projects is None:
        completed_projects = completed_project_modules(user)
    completed, completed_projects = _merged_completions(
        user, destination, completed, completed_projects
    )
    from app.pathway_scope import pathway_modules
    # Scoped to the learner's own modules: for an ML destination the pointer
    # walks the foundation straight into the pathway and stops there.
    return _next_course_action(
        completed, completed_projects, modules=pathway_modules(destination)
    )



def _next_course_action(completed, project_modules, modules=None):
    # ``modules`` lets a pathway scope the pointer to its own curriculum;
    # defaulting to the full course keeps every existing caller unchanged.
    for module in (all_modules() if modules is None else modules):
        if any(lesson['id'] not in completed for lesson in module['lessons']):
            lesson = next(item for item in module['lessons'] if item['id'] not in completed)
            return {'type': 'lesson', 'lesson_id': lesson['id']}
        if module['id'] not in project_modules:
            return {'type': 'project', 'module_id': module['id'],
                    'module_title': module['title'],
                    'module_number': module['number']}
    return None


def lesson_is_available(user, lesson_id, completed=None, completed_projects=None):
    """Whether one catalog lesson may be opened by this learner.

    Two rules apply together: the lesson must belong to the learner's pathway
    (an ML learner can never open a module 03-12 lesson, and an AI learner is
    never handed a ``mle.*`` lesson), and the sequential unlock rules must have
    reached it.  Pathway lessons are reached by the same pointer, which is why
    one scoped walk serves both catalogs.
    """
    from app.curriculum import get_lesson
    from app.ml_pathway import get_machine_learning_lesson
    from app.pathway_scope import FOUNDATION_MODULE_IDS, is_ml

    destination = _scope(user, None)
    ai_lesson = get_lesson(lesson_id)
    ml_lesson = get_machine_learning_lesson(lesson_id)
    if ai_lesson is None and ml_lesson is None:
        return False
    if is_ml(destination):
        if ai_lesson is not None and ai_lesson['module_id'] not in FOUNDATION_MODULE_IDS:
            return False
    elif ml_lesson is not None:
        return False

    if completed is None:
        completed = completed_lesson_ids(user)
    if completed_projects is None:
        completed_projects = completed_project_modules(user)
    completed, completed_projects = _merged_completions(
        user, destination, completed, completed_projects
    )
    if lesson_id in completed:
        return True
    return lesson_id == next_unlocked_lesson(
        user, completed=completed, completed_projects=completed_projects,
        destination=destination,
    )



def module_project_is_available(user, module_id, completed=None):
    from app.curriculum import get_module
    module = get_module(module_id)
    if not module:
        return False
    if completed is None:
        completed = completed_lesson_ids(user)
    return all(lesson['id'] in completed for lesson in module['lessons'])


def course_progress(user, completed=None, completed_projects=None,
                    destination=None):
    """Progress over the learner's own course, not a fixed catalog.

    Defaults to the confirmed pathway, so every caller — the dashboard, the
    lesson catalog, the projects page, the admin portal — reports the same
    denominators without re-deriving the scope.  Callers that need the AI
    course as authored (credential eligibility) pass ``destination='ai'``.
    """
    from app.pathway_scope import (
        destination_for, is_ml, module_entry, pathway_modules,
    )

    destination = _scope(user, destination) if destination is None else destination
    if completed is None:
        completed = completed_lesson_ids(user)
    if completed_projects is None:
        completed_projects = completed_project_modules(user)
    completed, completed_projects = _merged_completions(
        user, destination, completed, completed_projects
    )
    modules = pathway_modules(destination)
    lessons = [lesson for module in modules for lesson in module['lessons']]
    # Reuse these sets for all progress fields. Re-querying through
    # next_course_action() and next_unlocked_lesson() made dashboard renders
    # issue the same two completion queries three times.
    action = _next_course_action(completed, completed_projects, modules=modules)
    ai_lessons = [
        lesson for module in modules if module.get('source') != 'ml'
        for lesson in module['lessons']
    ]
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
        'recalibration': study_recalibration(user, completed, lessons=ai_lessons),
        'modules': [
            module_entry(module, completed, completed_projects)
            for module in modules
        ],
    }



SHARED_FOUNDATION_MODULES = ('00', '01', '02')


def pathway_dashboard_progress(user, destination, progress,
                               completed=None, completed_projects=None):
    """Re-scope the dashboard's course block onto a confirmed ML destination.

    An ``ml`` learner's course is the shared foundation (modules 00-02) plus
    the ML pathway's four modules.  Modules 03-12 are the AI continuation and
    belong to a different course, so they drop out of the curriculum grid, the
    header totals, and the "next step" pointers; every other destination keeps
    the full AI curriculum exactly as it is.

    ``progress`` comes from :func:`course_progress` and is left untouched, so a
    caller can still compare against the shared-course numbers.
    """
    if destination != 'ml':
        return progress

    from app.ml_pathway import machine_learning_pathway, ml_module_progress

    if completed is None:
        completed = completed_lesson_ids(user)
    if completed_projects is None:
        completed_projects = completed_project_modules(user)
    foundation = [
        module for module in all_modules()
        if module['id'] in SHARED_FOUNDATION_MODULES
    ]
    foundation_ids = {module['id'] for module in foundation}
    ml_progress = ml_module_progress(user.id)

    # The foundation entries already carry their own lesson and project
    # progress in ``progress['modules']``; only the badge is added, so the
    # shared foundation reports exactly what the AI course reports for it.
    modules = [
        {**entry, 'badge': f'Shared foundation · Module {entry["number"]}'}
        for entry in progress['modules'] if entry['id'] in foundation_ids
    ]
    for module in machine_learning_pathway()['modules']:
        state = ml_progress.get(module['id'], {})
        modules.append({
            'id': module['id'], 'number': module['number'],
            'title': module['title'],
            'total_lessons': state.get('total_lessons', len(module['lessons'])),
            'estimated_hours': module.get('estimated_hours', 0),
            'project_completed': bool(state.get('project_completed')),
            'outcome': module.get('summary') or module.get('title', ''),
            'study_minutes': sum(
                (lesson.get('study_minutes') or 0)
                for lesson in module['lessons']
            ),
            'completed_lessons': state.get('completed_lessons', 0),
            # Foundation numbers 0-2 and the pathway's 1-4 collide, so the grid
            # needs to say which course a module belongs to.
            'badge': f'ML pathway · Module {module["number"]}',
        })

    foundation_modules = modules[:len(foundation)]
    pathway_modules = modules[len(foundation):]
    # Foundation 01 and 02 projects are the pathway's prerequisites, so a
    # finished foundation implies they are met; no extra query is needed.
    foundation_complete = all(
        module['completed_lessons'] == module['total_lessons']
        and module['project_completed']
        for module in foundation_modules
    )
    pathway_complete = all(
        module['completed_lessons'] == module['total_lessons']
        and module['project_completed']
        for module in pathway_modules
    )
    # The shared pointer is scoped to the foundation only: the ML continuation
    # belongs to the pathway card, and modules 03-12 are never this learner's
    # next step.
    action = _next_course_action(
        completed, completed_projects, modules=foundation
    )
    return {
        **progress,
        'total_lessons': sum(module['total_lessons'] for module in modules),
        'completed_lessons': sum(
            module['completed_lessons'] for module in modules
        ),
        'total_projects': len(modules),
        'completed_projects': sum(
            1 for module in modules if module['project_completed']
        ),
        'course_complete': foundation_complete and pathway_complete,
        'next_lesson_id': (
            action['lesson_id'] if action and action['type'] == 'lesson' else None
        ),
        'next_action': action,
        'modules': modules,
    }


def monthly_milestone_progress(
    progress, completed_projects, track='standard', calibration_multiplier=None
):
    """Group modules into balanced, contiguous months for the selected track.

    Module hours still come from the curated curriculum, but their month
    boundaries are chosen by a dynamic program rather than hard-coded lists.
    That keeps the five-month intensive plan and the 9–12 month standard plan
    balanced when lesson estimates change, without ever splitting a module or
    reordering the course.
    """
    from app.course_data import milestones_for, partition_module_groups

    milestones = milestones_for(track)
    if not milestones:
        return []
    ordered_modules = list(progress['modules'])
    groups = partition_module_groups(
        [item.get('estimated_hours', 0) for item in ordered_modules],
        len(milestones),
    )
    multiplier = (
        calibration_multiplier
        if isinstance(calibration_multiplier, (int, float))
        and not isinstance(calibration_multiplier, bool)
        and calibration_multiplier > 0
        else None
    )
    # Avoid letting one unusually fast or slow lesson produce an absurd target.
    multiplier = min(3.0, max(0.5, multiplier)) if multiplier else None

    result = []
    for milestone, group in zip(milestones, groups):
        grouped = [ordered_modules[index] for index in group]
        done_lessons = sum(item['completed_lessons'] for item in grouped)
        total_lessons = sum(item['total_lessons'] for item in grouped)
        estimated_hours = round(
            sum(item.get('estimated_hours', 0) for item in grouped), 1
        )
        reading_hours = round(
            sum(item.get('study_minutes', 0) for item in grouped) / 60, 1
        )
        # Catch-up time is metadata for the month, never an extra month.
        review_hours = round(estimated_hours * 0.2, 1)
        done_modules = sum(
            item['completed_lessons'] == item['total_lessons']
            and item['id'] in completed_projects for item in grouped
        )
        complete = bool(grouped) and done_modules == len(grouped)
        previous_complete = all(item['complete'] for item in result)
        calibrated_hours = (
            round(estimated_hours * multiplier, 1) if multiplier else None
        )
        result.append({
            **milestone,
            'modules': [item['id'] for item in grouped],
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
            'calibrated_hours': calibrated_hours,
            'calibrated_weekly_hours': (
                round(calibrated_hours / 4.345, 1)
                if calibrated_hours is not None else None
            ),
            'calibration_multiplier': multiplier,
            'completed_modules': done_modules,
            'total_modules': len(grouped),
            'percent': round(done_lessons / total_lessons * 100) if total_lessons else 0,
        })
    return result


def study_recalibration(user, completed=None, completed_projects=None,
                        lessons=None):
    """Compare observed study minutes against estimates for this learner.

    The comparison is user-scoped: it uses the learner's own
    ``LessonCompletion.time_spent_minutes`` against the curated
    ``_study_minutes`` estimates. It only reports; the learner decides what to
    do with the observed multiplier. ``lessons`` narrows the estimate to the
    courses that record study time — pathway lessons live in their own tables.
    """
    from app.curriculum import all_lessons
    from app.models import LessonCompletion

    if completed is None:
        completed = completed_lesson_ids(user)
    estimated_minutes = 0.0
    observed_minutes = 0.0
    counted = set()
    for lesson in all_lessons() if lessons is None else lessons:
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
    from app.pathway_scope import pathway_lessons

    lesson_id = next_unlocked_lesson(user)
    lessons = pathway_lessons(_scope(user, None))
    if lesson_id is None:
        return len(lessons) + 1
    for index, lesson in enumerate(lessons, start=1):
        if lesson['id'] == lesson_id:
            return index
    return len(lessons) + 1


def day_is_available(user, config, day_number):
    if not isinstance(day_number, int) or isinstance(day_number, bool):
        return False
    from app.pathway_scope import pathway_lessons

    # Scoped to the learner's pathway: an ML learner's calendar never reaches
    # a day that maps onto an AI-only module 03-12 lesson.
    lessons = pathway_lessons(_scope(user, None))
    if day_number < 1 or day_number > len(lessons):
        return False
    return lesson_is_available(user, lessons[day_number - 1]['id'])
