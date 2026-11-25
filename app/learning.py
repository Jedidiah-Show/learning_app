"""Sequential lesson and module-project unlock rules.

The unlock rules are pathway-aware.  Every learner starts on the shared
foundation (modules 00–02); the AI Engineering specialization opens once it is
complete; the Machine Learning pathway follows its own sequence from the start.
Pointers, availability and progress totals never cross into a specialization
the learner is not in.
"""

from app.curriculum import all_modules
from app.models import CourseProject, LessonCompletion
from app.pathway_scope import _user_id


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

    uq = _user_id(user)
    if not is_ml(destination):
        return set(completed), set(project_modules)
    ml_lessons, ml_projects = ml_completion_state(uq)
    return set(completed) | ml_lessons, set(project_modules) | ml_projects


def completed_lesson_ids(user):
    from flask import has_request_context, g

    uq = _user_id(user)
    if uq is None:
        return set()
    if has_request_context():
        cache = getattr(g, '_completed_lesson_ids_cache', None)
        if cache is None:
            cache = {}
            g._completed_lesson_ids_cache = cache
        if uq in cache:
            return set(cache[uq])

    results = {
        lesson_id for (lesson_id,) in LessonCompletion.query.with_entities(
            LessonCompletion.lesson_id
        ).filter_by(user_id=uq, completed=True).all()
    }
    if has_request_context():
        g._completed_lesson_ids_cache[uq] = set(results)
    return results



def completed_project_modules(user):
    from flask import has_request_context, g

    uq = _user_id(user)
    if uq is None:
        return set()
    if has_request_context():
        cache = getattr(g, '_completed_project_modules_cache', None)
        if cache is None:
            cache = {}
            g._completed_project_modules_cache = cache
        if uq in cache:
            return set(cache[uq])

    results = {
        module_id for (module_id,) in CourseProject.query.with_entities(
            CourseProject.module_id
        ).filter_by(user_id=uq, completed=True).all()
    }
    if has_request_context():
        g._completed_project_modules_cache[uq] = set(results)
    return results


def user_track(user):
    """Return the learner's selected plan track, defaulting to standard."""
    from app.course_data import TRACK_IDS
    from app.pathway_scope import get_user_course_plan

    plan = get_user_course_plan(user)
    if plan and plan.track in TRACK_IDS:
        return plan.track
    return 'standard'


def next_unlocked_lesson(user, completed=None, completed_projects=None,
                         destination=None):
    uq = _user_id(user)
    action = next_course_action(
        uq, completed=completed, completed_projects=completed_projects,
        destination=destination,
    )
    return action['lesson_id'] if action and action['type'] == 'lesson' else None


def next_course_action(user, completed=None, completed_projects=None,
                       destination=None):
    uq = _user_id(user)
    destination = _scope(uq, destination)
    if completed is None:
        completed = completed_lesson_ids(uq)
    if completed_projects is None:
        completed_projects = completed_project_modules(uq)
    completed, completed_projects = _merged_completions(
        uq, destination, completed, completed_projects
    )
    from app.pathway_scope import journey_modules
    # The pointer walks the learner's journey: foundations first, then the
    # specialization; for ML that is the ML sequence, for foundations-only
    # destinations the foundation.
    return _next_course_action(
        completed, completed_projects, modules=journey_modules(destination)
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
    from app.pathway_scope import foundation_course_modules

    uq = _user_id(user)
    destination = _scope(uq, None)
    ai_lesson = get_lesson(lesson_id)
    ml_lesson = get_machine_learning_lesson(lesson_id)
    if ai_lesson is None and ml_lesson is None:
        return False

    # A dual-enrolled learner can open both specialisations.  A learner scoped
    # to exactly one pathway cannot open the other's modules; foundation
    # lessons (00–02) are always shared.
    from app.pathway_scope import active_pathway_enrolments, is_ml
    enrolled_ids = {
        enrolment.pathway_id
        for enrolment, _ in active_pathway_enrolments(uq)
    }
    has_ai = 'ai-engineering' in enrolled_ids
    has_ml = 'machine-learning' in enrolled_ids
    if not enrolled_ids:
        # Legacy single-destination accounts: the plan decides the scope.
        if is_ml(destination):
            has_ml = True
        else:
            has_ai = True
    from app.pathway_scope import FOUNDATION_COURSE_MODULE_IDS
    is_foundation_lesson = (
        ai_lesson is not None
        and (
            str(lesson_id).startswith('sf.')
            or ai_lesson.get('module_id') in FOUNDATION_COURSE_MODULE_IDS
        )
    )
    if ai_lesson is not None and not is_foundation_lesson and not has_ai:
        # AI lessons require AI enrolment only. Shared Foundations progress
        # is standalone and must never gate or inflate the AI pathway.
        return False
    if ml_lesson is not None and not has_ml:
        return False

    if completed is None:
        completed = completed_lesson_ids(uq)
    if completed_projects is None:
        completed_projects = completed_project_modules(uq)
    completed, completed_projects = _merged_completions(
        uq, destination, completed, completed_projects
    )
    if lesson_id in completed:
        return True
    # Foundation lessons are the shared start: they stay open in study order
    # for every learner, forever.  Specialization lessons unlock in their own
    # sequence — the AI specialization once the foundation is complete, the ML
    # pathway within its own order.  Pointer equality within each sequence is
    # the gate, so completed lessons always stay revisitable.
    from app.pathway_scope import (
        ai_specialization_modules, foundation_course_modules, ml_course_modules,
    )
    if is_foundation_lesson:
        if str(lesson_id).startswith('sf.'):
            from app.foundations_pathway import foundation_lesson_is_open
            return foundation_lesson_is_open(uq, lesson_id)
        # Historical 00–02 lessons keep their own study order and never feed
        # AI or ML counters. Their evidence is read from the legacy shared
        # completion table, which is separate from pathway progress.
        legacy_modules = [
            module for module in all_modules()
            if module['id'] in FOUNDATION_COURSE_MODULE_IDS
        ]
        action = _next_course_action(
            completed_lesson_ids(uq), set(), modules=legacy_modules,
        )
        return (
            action is not None
            and action.get('type') == 'lesson'
            and action.get('lesson_id') == lesson_id
        )
    if ai_lesson is not None:
        pointer_modules = ai_specialization_modules()
    else:
        pointer_modules = ml_course_modules()
    action = _next_course_action(
        completed, completed_projects, modules=pointer_modules
    )
    return (
        action is not None
        and action.get('type') == 'lesson'
        and action.get('lesson_id') == lesson_id
    )



def invalidate_completion_caches():
    """Drop the per-request memoized completion sets after a write.

    Completing a lesson or project during a request must not hand the rest of
    that same request the pre-write snapshot — the progress payload built
    right after the commit would otherwise point at the lesson just finished.
    """
    from flask import has_request_context, g

    if not has_request_context():
        return
    g._completed_lesson_ids_cache = {}
    g._completed_project_modules_cache = {}


def module_lessons_missing(user, module_id, completed=None):
    """Return the module's incomplete lessons in study order.

    Each entry carries the lesson id, title and research ordinal so a caller
    can render exactly what stands between the learner and the module project.
    Returns None for unknown module ids.
    """
    from app.curriculum import get_module

    module = get_module(module_id)
    if not module:
        return None
    if completed is None:
        completed = completed_lesson_ids(user)
    return [
        {
            'id': lesson['id'],
            'title': lesson.get('title') or lesson['id'],
            'ordinal': lesson.get('_ordinal'),
        }
        for lesson in module['lessons']
        if lesson['id'] not in completed
    ]


def module_project_is_available(user, module_id, completed=None):
    from app.curriculum import get_module
    module = get_module(module_id)
    if not module:
        return False
    uq = _user_id(user)
    if completed is None:
        completed = completed_lesson_ids(uq)
    return all(lesson['id'] in completed for lesson in module['lessons'])


def course_progress(user, completed=None, completed_projects=None,
                    destination=None, include_journey=False):
    """Progress over the learner's own course, not a fixed catalog.

    Defaults to the confirmed pathway's own modules (each pathway counts only
    its modules), so every caller — the dashboard, the lesson catalog, the
    projects page, the admin portal — reports the same denominators without
    re-deriving the scope.  Pass ``include_journey=True`` to measure the full
    journey instead (foundation plus the AI specialization) — used for the AI
    credential, which certifies the whole course.  Callers that need exactly
    this shape pass ``destination`` explicitly.
    """
    from app.pathway_scope import (
        course_modules, is_ml, journey_modules, module_entry,
    )

    uq = _user_id(user)
    destination = _scope(uq, destination) if destination is None else destination
    if completed is None:
        completed = completed_lesson_ids(uq)
    if completed_projects is None:
        completed_projects = completed_project_modules(uq)
    completed, completed_projects = _merged_completions(
        uq, destination, completed, completed_projects
    )
    modules = (
        journey_modules(destination) if include_journey
        else course_modules(destination)
    )
    lessons = [lesson for module in modules for lesson in module['lessons']]
    # Reuse these sets for all progress fields. Re-querying through
    # next_course_action() and next_unlocked_lesson() made dashboard renders
    # issue the same two completion queries three times.
    pointer_modules = journey_modules(destination)
    action = _next_course_action(completed, completed_projects,
                                 modules=pointer_modules)
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
        'recalibration': study_recalibration(uq, completed, lessons=ai_lessons),
        'modules': [
            module_entry(module, completed, completed_projects)
            for module in modules
        ],
    }



SHARED_FOUNDATION_MODULES = ('00', '01', '02')


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

    uq = _user_id(user)
    if completed is None:
        completed = completed_lesson_ids(uq)
    estimated_minutes = 0.0
    observed_minutes = 0.0
    counted = set()
    candidate_lessons = all_lessons() if lessons is None else lessons
    relevant_ids = [
        lesson['id'] for lesson in candidate_lessons
        if lesson.get('id') and lesson['id'] in completed
    ]
    time_spent_by_lesson = {}
    if relevant_ids:
        rows = (
            LessonCompletion.query
            .filter(
                LessonCompletion.user_id == uq,
                LessonCompletion.lesson_id.in_(relevant_ids),
            )
            .all()
        )
        for r in rows:
            if r.time_spent_minutes:
                time_spent_by_lesson[r.lesson_id] = float(r.time_spent_minutes)

    for lesson in candidate_lessons:
        lesson_id = lesson.get('id')
        if not lesson_id or lesson_id in counted or lesson_id not in completed:
            continue
        counted.add(lesson_id)
        estimated_minutes += float(lesson.get('study_minutes') or 0)
        observed_minutes += time_spent_by_lesson.get(lesson_id, 0.0)
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
