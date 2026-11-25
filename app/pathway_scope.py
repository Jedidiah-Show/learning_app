"""What a learner studies, determined by their active pathway enrolments.

``pathway_destination`` on ``CoursePlan`` is kept deprecated during M0–M2
for rollback, but active application logic reads from
``LearnerPathwayEnrollment`` instead.  A learner may have zero, one, or multiple
active enrolments — each independently scopes the lesson catalog, progress
calculations, and pacing.

``active_pathway_enrolments(user_id)`` returns all active enrolments for a learner.
Each enrolment's ``pathway_id`` ('shared-foundations', 'ai-engineering',
'machine-learning') maps to a curriculum domain definition.

A learner who is enrolled in both AI Engineering and ML will yield two enrolments;
pausing one does not affect the other.
"""

from app.curriculum import all_modules
from flask import g
import json
from pathlib import Path
from app.models import (
    CoursePlan,
    LessonCompletion,
    CourseProject,
    LearnerPathwayEnrollment,
    LearningPathway,
)
from app import db


# Per-request cache for completed lesson IDs, keyed by user_id.  Avoids
# re-scanning LessonCompletion on every pathway_modules / course_modules call
# within the same request.
def _completed_lesson_ids(user_id):
    """Return the set of completed lesson ids for a user, cached per request."""
    cache = getattr(g, '_completed_lesson_ids_cache', None)
    if cache is None:
        cache = {}
        g._completed_lesson_ids_cache = cache
    if user_id not in cache:
        rows = LessonCompletion.query.filter_by(
            user_id=user_id, completed=True
        ).all()
        cache[user_id] = {row.lesson_id for row in rows}
    return cache[user_id]


def _completion_state(user_id, pathway_id):
    """``(lesson ids, project module ids)`` completed in one pathway.

    AI Engineering and the shared foundation record evidence in
    ``LessonCompletion``/``CourseProject``; the ML pathway has its own tables
    (see :func:`ml_completion_state`).  Every counting surface must go through
    this helper so a completion in one discipline can never inflate the other.
    """
    if is_ml(pathway_id):
        return ml_completion_state(user_id)
    if normalize_pathway_id(pathway_id) in (None, 'shared-foundations'):
        from app.foundations_pathway import foundation_completed_lesson_ids
        return foundation_completed_lesson_ids(user_id), set()
    return _completed_lesson_ids(user_id), _ai_project_modules(user_id)


# The six Shared Foundations modules in the standalone manifest (sf.00–sf.05)
# and the three foundation modules of the bundled manifest (00–02).
FOUNDATION_MODULE_IDS = {'sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04', 'sf.05'}
FOUNDATION_COURSE_MODULE_IDS = ('00', '01', '02')

PATHWAY_LABELS = {
    'shared-foundations': 'Shared Foundations',
    'ai-engineering': 'AI Engineering',
    'machine-learning': 'Machine Learning',
}


def pathway_label(pathway_id):
    """Full discipline name for a pathway id.

    Accepts both explicit ids and legacy destination tokens; an undecided
    learner falls back to the AI Engineering course they actually study.
    """
    canonical = normalize_pathway_id(pathway_id)
    if canonical is None:
        # Never present AI Engineering as the default discipline: an
        # undecided learner is simply not enrolled in a specialisation yet.
        return 'Undecided'
    return PATHWAY_LABELS.get(canonical, str(pathway_id))

# The application historically stored ``ai``/``ml``/``undecided`` on
# ``CoursePlan.pathway_destination``.  Enrolments use the longer, explicit
# domain identifiers.  Both must describe the same course.
_LEGACY_ALIASES = {
    'ai': 'ai-engineering',
    'ai-engineering': 'ai-engineering',
    'ml': 'machine-learning',
    'machine-learning': 'machine-learning',
    'shared': 'shared-foundations',
    'foundation': 'shared-foundations',
    'shared-foundations': 'shared-foundations',
}

_SPECIALISATION_PRIORITY = (
    'ai-engineering', 'machine-learning', 'shared-foundations',
)


def _user_id(user):
    """Normalise a ``User`` object, an id, or ``None`` to an integer id."""
    if user is None:
        return None
    if isinstance(user, int):
        return user
    return getattr(user, 'id', user)


def _current_user_id():
    from flask_login import current_user as lc_current_user

    if getattr(lc_current_user, 'is_authenticated', False):
        return lc_current_user.id
    return None


def normalize_pathway_id(value):
    """Map legacy destination tokens onto explicit pathway identifiers.

    ``None`` and ``undecided`` mean "no confirmed specialisation" and keep the
    full AI Engineering course, so they normalise to ``None``.
    """
    if value is None:
        return None
    key = str(value).strip().lower()
    if key in ('', 'undecided', 'none'):
        return None
    return _LEGACY_ALIASES.get(key, key)


def active_pathway_enrolments(user_id=None):
    """Return all active pathway enrolments for a learner.

    Yields ``(LearnerPathwayEnrollment, LearningPathway)`` tuples; each enrolment
    has a ``pathway_id`` ('shared-foundations', 'ai-engineering',
    'machine-learning') that maps to a curriculum domain definition.

    A learner enrolled in both AI Engineering and ML yields two enrolments;
    pausing one does not affect the other.  Accepts either a ``User`` object or
    an integer id so callers never hand SQLAlchemy a model instance.
    """
    from flask import has_request_context, g

    uid = _user_id(user_id)
    if uid is None:
        uid = _current_user_id()
    if uid is None:
        return []

    if has_request_context():
        cache = getattr(g, '_pathway_enrolment_cache', None)
        if cache is None:
            cache = {}
            g._pathway_enrolment_cache = cache
        if uid in cache:
            return cache[uid]

    enrolments = (
        db.session.query(LearnerPathwayEnrollment, LearningPathway)
        .join(LearningPathway, LearnerPathwayEnrollment.pathway_id == LearningPathway.id)
        .filter(LearnerPathwayEnrollment.learner_id == uid)
        .filter(LearnerPathwayEnrollment.status.in_(('ENROLLED', 'ACTIVE')))
        .all()
    )
    if has_request_context():
        g._pathway_enrolment_cache[uid] = enrolments
    return enrolments


def is_pathway(user_id, pathway_id):
    """Check whether a learner has an active enrolment in the given pathway."""
    wanted = normalize_pathway_id(pathway_id)
    enrolments = active_pathway_enrolments(user_id)
    return any(
        normalize_pathway_id(enrolment.pathway_id) == wanted
        for enrolment, _ in enrolments
    )


def get_user_course_plan(user_id):
    """Return the CoursePlan for a user, cached per request in flask.g."""
    from flask import has_request_context, g

    uid = _user_id(user_id)
    if uid is None:
        return None
    if has_request_context():
        cache = getattr(g, '_course_plan_cache', None)
        if cache is None:
            cache = {}
            g._course_plan_cache = cache
        if uid in cache:
            return cache[uid]
    try:
        plan = CoursePlan.query.filter_by(user_id=uid).first()
    except Exception:
        plan = None
    if has_request_context():
        g._course_plan_cache[uid] = plan
    return plan


def destination_for(user_id=None):
    """The learner's chosen specialization as an explicit pathway id.

    The learner's chosen specialisation is the single source of truth for
    which pathway the whole app leads with.  The explicit
    ``CoursePlan.pathway_destination`` column — written by onboarding or by the
    instant pathway switcher — wins when set; the learner may change it at any
    time (see :func:`switch_pathway`).  When the column is unset, active
    ``LearnerPathwayEnrollment`` rows decide — one active specialisation
    enrolment wins, and two fall back to the historical AI Engineering
    priority.  Learners without enrolments *and* without an explicit choice
    have ``None`` — they are not silently assigned a specialisation via the
    deprecated column.  Returns ``'ai-engineering'``, ``'machine-learning'``,
    ``'shared-foundations'``, or ``None`` (undecided).

    Failure-tolerant: a database hiccup behaves like no destination rather than
    taking a page down.
    """
    from flask import has_request_context, g

    uid = _user_id(user_id)
    if uid is None:
        uid = _current_user_id()
    if uid is None:
        return None

    if has_request_context():
        dest_cache = getattr(g, '_destination_cache', None)
        if dest_cache is None:
            dest_cache = {}
            g._destination_cache = dest_cache
        if uid in dest_cache:
            return dest_cache[uid]

    plan = get_user_course_plan(uid)
    result = None
    if plan is not None and plan.pathway_destination:
        explicit = normalize_pathway_id(plan.pathway_destination)
        if explicit is not None:
            result = explicit

    if result is None:
        try:
            enrolments = active_pathway_enrolments(uid)
        except Exception:  # pragma: no cover - defensive: never fail a page render
            enrolments = []

        if enrolments:
            ids = {
                normalize_pathway_id(enrolment.pathway_id)
                for enrolment, _ in enrolments
            }
            for candidate in _SPECIALISATION_PRIORITY:
                if candidate in ids:
                    result = candidate
                    break
            if result is None:
                # An unknown enrolment id: preserve it verbatim.
                result = next(iter(ids))

    if has_request_context():
        g._destination_cache[uid] = result
    return result


def pathway_ids_for(user_id=None):
    """Set of explicit pathway ids the learner can study.

    Returns only pathway ids from active ``LearnerPathwayEnrollment`` rows.
    Learners without enrolments have an empty set — they are not silently
    assigned to a specialisation via the deprecated
    ``CoursePlan.pathway_destination`` column.
    """
    uid = _user_id(user_id)
    if uid is None:
        uid = _current_user_id()
    try:
        ids = {
            normalize_pathway_id(enrolment.pathway_id)
            for enrolment, _ in active_pathway_enrolments(uid)
        }
    except Exception:  # pragma: no cover - defensive
        ids = set()
    return ids


def pathway_modules(pathway_id, user_id=None):
    """Module dicts in study order for a given pathway.

    Parameters:
        pathway_id: One of 'shared-foundations', 'ai-engineering', 'machine-learning'.
        user_id: Optional; if provided, foundation evidence is checked for
            prerequisite satisfaction.

    Returns the pathway's *own* authored modules.  This is the workspace view
    (M2/M3): Shared Foundations, the AI specialisation modules, or the ML
    pathway modules.  A learner's combined course — foundation plus
    specialisation — is assembled by :func:`course_modules`.
    """
    canonical = normalize_pathway_id(pathway_id)
    # Shared Foundations: the common course every specialisation builds on.
    # The legacy foundation modules (00–02) of the bundled manifest carry every
    # lesson and project record, so the learner-facing foundations course is
    # assembled from them; the sf.* authoring manifest remains available for
    # evidence and passport grouping.
    if canonical == 'shared-foundations':
        return foundation_course_modules(user_id)

    # AI Engineering: only ai.* modules. Foundation progress is independent and
    # never gates, injects or inflates AI lessons/projects.
    if canonical == 'ai-engineering':
        ai_modules = ai_specialization_modules()
        if user_id:
            completed_lessons = _completed_lesson_ids(user_id)
            for module in ai_modules:
                lessons = module.get('lessons') or []
                module['_completed_lessons'] = sum(
                    1 for lesson in lessons if lesson['id'] in completed_lessons
                )
                module['_total_lessons'] = len(lessons)
        return ai_modules

    # Machine Learning: the 12 mle.* modules (outside app.curriculum)
    if canonical == 'machine-learning':
        from app.ml_pathway import machine_learning_pathway
        pathway = machine_learning_pathway()
        modules = []
        for module in pathway['modules']:
            lessons = [
                {**lesson, 'module_id': module['id'], 'module_title': module['title'],
                 'source': 'ml'}
                for lesson in module['lessons']
                if lesson.get('status') == 'ready'
            ]
            if not lessons:
                continue
            modules.append({
                'id': module['id'],
                'number': module['number'],
                'title': module['title'],
                'description': module.get('summary') or '',
                'estimated_hours': module.get('estimated_hours', 0),
                'assumed_prerequisites': '',
                'readiness_check': 'Work through every lesson in this module, then submit its project to unlock the next module.',
                'resources': {},
                'project': module.get('project') or '',
                'project_rubric': module.get('project_rubric') or [],
                'lessons': lessons,
                'source': 'ml',
                'badge': f'ML pathway · Module {module["number"]}',
                'outcome': module.get('summary') or module.get('title', ''),
            })
        if user_id:
            # ML completions live in the ML-specific tables, never in the
            # shared LessonCompletion/CourseProject tables.
            completed_lessons, _ = _completion_state(user_id, 'machine-learning')
            for module in modules:
                lessons = module.get('lessons') or []
                module['_completed_lessons'] = sum(
                    1 for lesson in lessons
                    if lesson.get('id') in completed_lessons
                )
                module['_total_lessons'] = len(lessons)
        return modules

    if canonical is None:
        # Undecided learners see the canonical Shared Foundations catalogue.
        return foundation_course_modules(user_id)

    # Unknown pathway_id — return empty list
    return []


def ai_specialization_modules():
    """The AI Engineering specialization modules (all non-foundation modules)."""
    return [
        module for module in all_modules()
        if not module['id'].startswith('sf.')
        and not module['id'].startswith('mle.')
        and module['id'] not in FOUNDATION_COURSE_MODULE_IDS
    ]


def foundation_course_modules(user_id=None):
    """The ONE learner-facing Shared Foundations catalogue: six sf.* modules.

    Modules and lessons come from the canonical registry/content manifest;
    progress comes only from ``FoundationLessonProgress``. The legacy
    00–02 course IDs are historical evidence aliases, never displayed as a
    competing foundation curriculum and never used to gate AI or ML progress.
    """
    from app.foundations_pathway import (
        foundation_completed_lesson_ids, shared_foundations_lessons,
    )

    content = shared_foundations_lessons()
    completed = foundation_completed_lesson_ids(user_id) if user_id else set()
    modules = []
    for module in foundation_modules():
        lessons = [
            {**lesson, 'source': 'foundations'}
            for lesson in content if lesson['module_id'] == module['id']
        ]
        entry = {
            **module,
            'lessons': lessons,
            'source': 'foundations',
            'badge': f'Foundations · Module {module["number"]}',
            'outcomes': module.get('competencies') or [],
            'readiness_check': 'Complete the published lessons in order; results stay within Shared Foundations.',
            'resources': {},
            'project': '',
            'project_rubric': [],
        }
        if user_id:
            entry['_completed_lessons'] = sum(
                1 for lesson in lessons if lesson['id'] in completed
            )
            entry['_total_lessons'] = len(lessons)
        modules.append(entry)
    return modules


def ml_course_modules():
    """The ready ML pathway modules in their shared-course shape."""
    return pathway_modules('machine-learning')


def course_modules(pathway_id, user_id=None):
    """The catalogue every learner-facing surface renders for a pathway.

    Each pathway **counts only its own modules**:

    * ``shared-foundations`` (and undecided) → the shared foundation only;
    * ``ai-engineering`` → the AI specialization modules only;
    * ``machine-learning`` → the ML pathway modules only.

    The combined journey — foundation first, then the specialization — is
    assembled by :func:`journey_modules`, e.g. for sequential pointers and
    credential eligibility.
    """
    canonical = normalize_pathway_id(pathway_id)
    if canonical == 'machine-learning':
        modules = ml_course_modules()
    elif canonical == 'ai-engineering':
        modules = ai_specialization_modules()
    elif canonical in ('shared-foundations', None):
        modules = foundation_course_modules()
    else:
        modules = []

    if user_id:
        # An ML catalogue must count ML-table evidence; a foundation or AI
        # catalogue keeps reading the shared completion tables.
        completed_lessons, _ = _completion_state(_user_id(user_id), canonical)
        for module in modules:
            lessons = module.get('lessons') or []
            module['_completed_lessons'] = sum(
                1 for lesson in lessons if lesson.get('id') in completed_lessons
            )
            module['_total_lessons'] = len(lessons)
    return modules


def journey_modules(pathway_id, user_id=None):
    """The full learning journey for a destination, in study order.

    The foundation is always first; the specialization follows.  Used for
    sequential pointers, credential eligibility and full-course checks —
    never rendered as a single catalogue.
    """
    canonical = normalize_pathway_id(pathway_id)
    if canonical == 'machine-learning':
        # The ML pathway is independently sequenced from the start.
        return ml_course_modules()
    if canonical == 'shared-foundations':
        modules = foundation_course_modules()
    else:
        # AI Engineering is an independent journey. Foundations are their own
        # standalone pathway and must never gate or inflate AI progress.
        modules = ai_specialization_modules()
    if user_id:
        # An ML catalogue must count ML-table evidence; a foundation or AI
        # catalogue keeps reading the shared completion tables.
        completed_lessons, _ = _completion_state(_user_id(user_id), canonical)
        for module in modules:
            lessons = module.get('lessons') or []
            module['_completed_lessons'] = sum(
                1 for lesson in lessons if lesson.get('id') in completed_lessons
            )
            module['_total_lessons'] = len(lessons)
    return modules


def pathway_lessons(pathway_id, user_id=None):
    """Every lesson for a given pathway, in study order.

    Each entry carries ``_ordinal`` and ``_module`` back-reference so the
    shared templates can render "Lesson N of M" and module captions without
    knowing which manifest a lesson came from.

    ``shared-foundations`` lists the foundations catalogue; every other
    destination lists that pathway's own modules.
    """
    if normalize_pathway_id(pathway_id) == 'shared-foundations':
        modules = pathway_modules('shared-foundations', user_id=user_id)
    else:
        modules = course_modules(pathway_id, user_id=user_id)
    lessons = []
    for module in modules:
        for lesson in module.get('lessons', []):
            entry = dict(lesson)
            # The ML manifest carries its source on the module; expose it on
            # each lesson too so lesson_href() (and catalog templates) route an
            # mle.* lesson to the pathway rather than the AI lesson page.
            if entry.get('source') is None and module.get('source') == 'ml':
                entry['source'] = 'ml'
            entry['_ordinal'] = len(lessons) + 1
            entry['_module'] = module
            lessons.append(entry)
    return lessons


def lesson_by_id(pathway_id, lesson_id, user_id=None):
    """Scoped catalog lookup for a lesson within a pathway."""
    if not lesson_id:
        return None
    return next(
        (lesson for lesson in pathway_lessons(pathway_id, user_id=user_id)
         if lesson['id'] == lesson_id),
        None,
    )


def pathway_lesson_count(pathway_id, user_id=None):
    """Lesson count denominator for a given pathway."""
    return len(pathway_lessons(pathway_id, user_id=user_id))


def active_pathway_ids(user_id):
    """Return the set of pathway_ids the learner is actively enrolled in."""
    enrolments = active_pathway_enrolments(user_id)
    return {enrolment_pathway_id for enrolment, _ in enrolments
            for enrolment_pathway_id in [enrolment.pathway_id]}


def foundation_evidence(user_id):
    """Return foundation competency evidence for a learner.

    Reuses existing ``LessonCompletion`` records.  A foundation competency
    is considered verified if the learner has completed all foundation lessons
    associated with it (via LessonCompletion), regardless of which pathway
    they are enrolled in.

    Returns a dict mapping foundation module ids to competency evidence, including
    domain-specific completion status for AI Engineering and Machine Learning
    pathways.
    """
    from app.models import CourseProject

    uid = _user_id(user_id)
    completed_lessons = _completed_lesson_ids(uid)
    completed_projects = {
        row.module_id
        for row in CourseProject.query.filter_by(
            user_id=uid, completed=True
        ).all()
    }

    evidence = {}
    for module in foundation_modules():
        module_id = module['id']
        if module_id not in FOUNDATION_MODULE_IDS:
            continue
        lessons = module.get('lessons') or []
        done_lessons = sum(1 for lesson in lessons if lesson['id'] in completed_lessons)
        done_projects = 1 if module_id in completed_projects else 0
        complete = done_lessons == len(lessons) and done_projects > 0
        # Foundation evidence is reusable: both specialisations may claim it.
        evidence[module_id] = {
            'completed_lessons': done_lessons,
            'total_lessons': len(lessons),
            'completed_projects': done_projects,
            'complete': complete,
            # Evidence reuse is explicit and per-pathway: completing a
            # foundation never auto-credits either specialisation.
            'ai_satisfied': False,
            'ml_satisfied': False,
            'evidence_source': 'lesson_completion' if complete else 'none',
        }
    return evidence


def _foundation_state_for(modules, completed_lessons, completed_projects):
    lessons = [
        lesson for module in modules for lesson in module.get('lessons') or []
    ]
    done_lessons = sum(lesson['id'] in completed_lessons for lesson in lessons)
    done_projects = sum(
        module['id'] in completed_projects for module in modules
    )
    total_lessons, total_projects = len(lessons), len(modules)
    return {
        'completed_lessons': done_lessons,
        'total_lessons': total_lessons,
        'completed_projects': done_projects,
        'total_projects': total_projects,
        'complete': (
            total_lessons > 0
            and done_lessons == total_lessons
            and done_projects == total_projects
        ),
    }


def foundation_completion_state(user_id):
    """Canonical Shared Foundations progress, isolated from both specialisations.

    Six sf.* modules, 21 lessons, counted only from FoundationLessonProgress.
    Legacy 00–02 evidence remains in the database for historical/credential
    record integrity but is not a competing curriculum and cannot satisfy AI
    or ML requirements.
    """
    from app.foundations_pathway import (
        foundation_completed_lesson_ids, shared_foundations_lessons,
    )
    uid = _user_id(user_id)
    completed = foundation_completed_lesson_ids(uid)
    lessons = shared_foundations_lessons()
    done = sum(1 for lesson in lessons if lesson['id'] in completed)
    total = len(lessons)
    return {
        'completed_lessons': done,
        'total_lessons': total,
        'completed_projects': 0,
        'total_projects': 0,
        'complete': bool(total and done == total),
    }


def foundation_modules():
    """Return the six Shared Foundations module definitions (sf.00–sf.05).

    Each module dict includes lessons, estimated_hours, and other module-level
    metadata.  Used by the foundation completion flow to iterate over all
    foundation modules and create LessonCompletion / CourseProject records.
    """
    # Resolve through the canonical registry (validated, cached) instead of
    # re-reading the manifest from disk on every call.
    from app.curriculum_registry import registry
    return registry.get_domain('shared-foundations').modules


def pathway_pace(user_id, pathway_id, weekly_hours=None):
    """Pacing plan scoped to a specific pathway_id.

    Parameters:
        user_id: The learner's user id.
        pathway_id: One of 'shared-foundations', 'ai-engineering', 'machine-learning'.
        weekly_hours: Optional; if not provided, reads from CoursePlan.

    Returns a pacing dict for the given pathway only.  A learner enrolled in
    both AI Engineering and ML can call this twice with different pathway_ids and
    get independent results — no cross-contamination.

    Only the ML pathway gets this plan: its course spans two manifests, so
    neither the 12/10/5-month AI tracks nor an ML-only plan describes it.  The
    AI course keeps its monthly milestones, which is why this returns ``None``
    for every other destination.
    """
    import math

    if not is_ml(pathway_id):
        return None

    # Get the complete course modules for this pathway
    modules = course_modules(pathway_id, user_id=user_id)

    if not modules:
        return None

    # Resolve weekly_hours
    if weekly_hours is None:
        plan = CoursePlan.query.filter_by(user_id=user_id).first()
        weekly_hours = plan.weekly_hours if plan and plan.weekly_hours else None
    if (
        not isinstance(weekly_hours, int)
        or isinstance(weekly_hours, bool)
        or weekly_hours <= 0
    ):
        weekly_hours = 6

    # Read evidence from the tables that own this pathway.  ML progress is
    # recorded in MLSpecialization* tables (scoped by pathway_id); reading the
    # shared tables here used to report zero lessons/projects for ML learners.
    completed_lessons, completed_projects = _completion_state(user_id, pathway_id)

    total_hours = 0.0
    total_lessons = 0
    completed_lesson_count = 0

    module_data = []
    for module in modules:
        hours = float(module.get('estimated_hours') or 0)
        total_hours += hours
        lessons = module.get('lessons', [])
        done = sum(1 for lesson in lessons if lesson['id'] in completed_lessons)
        total = len(lessons)
        total_lessons += total
        completed_lesson_count += done
        project_done = module['id'] in completed_projects

        reading_hours = round(
            sum(lesson.get('study_minutes') or 0 for lesson in lessons) / 60, 1
        )

        module_data.append({
            'id': module['id'],
            'number': module['number'],
            'title': module['title'],
            'badge': module.get('badge') or f'Module {module["number"]}',
            'source': module.get('source') or 'unknown',
            'estimated_hours': round(hours, 1),
            'reading_hours': reading_hours,
            'project_hours': round(max(hours - reading_hours, 0), 1),
            'completed_lessons': done,
            'total_lessons': total,
            'project_completed': project_done,
            'complete': bool(total and done == total and project_done),
            'percent': round(done / total * 100) if total else 0,
        })

    weeks = math.ceil(total_hours / weekly_hours) if total_hours else 0
    months = max(1, math.ceil(weeks / 4.345)) if weeks else 0

    # Set module statuses
    seen_complete = True
    for item in module_data:
        if item['complete']:
            item['status'] = 'Complete'
        elif seen_complete:
            item['status'] = 'In progress'
            seen_complete = False
        else:
            item['status'] = 'Up next'

    label = PATHWAY_LABELS.get(pathway_id, pathway_id)

    return {
        'pathway_id': pathway_id,
        'scope': 'pathway',
        'label': label,
        'weekly_hours': weekly_hours,
        'total_hours': round(total_hours, 1),
        'estimated_weeks': weeks,
        'estimated_months': months,
        'review_hours': round(total_hours * 0.2, 1),
        'total_lessons': total_lessons,
        'completed_lessons': completed_lesson_count,
        'modules': module_data,
    }


def pathway_header(pathway_id, user_id=None):
    """Copy for the lesson catalog header, scoped to a given pathway_id."""
    modules = course_modules(pathway_id, user_id=user_id)
    lessons = [lesson for module in modules for lesson in module.get('lessons', [])]
    hours = round(sum(
        float(module.get('estimated_hours') or 0) for module in modules
    ), 1)

    if pathway_id == 'shared-foundations' or pathway_id is None:
        return {
            'kicker': 'Everyone starts here',
            'title': 'RUACH Shared Foundations',
            'blurb': (
                'The common start of every RUACH specialization: Engineering '
                'Foundations, Python for Engineers, and Backend Engineering. '
                'Complete these modules and their projects to unlock the '
                'AI Engineering specialization; the Machine Learning pathway '
                'carries its own on-ramp and can be started now. Your choice '
                'of specialization stays open — switch at any time.'
            ),
            'module_count': len(modules),
            'lesson_count': len(lessons),
            'estimated_hours': hours,
        }
    elif pathway_id == 'ai-engineering':
        return {
            'kicker': 'AI Engineering specialization',
            'title': 'RUACH AI Engineering',
            'blurb': (
                'The AI Engineering specialization: LLM foundations, application '
                'engineering, RAG, agents, orchestration, MCP, production AI, '
                'deployment, system design, and the capstone. Finish the Shared '
                'Foundations first — they unlock this course. Your pace is chosen '
                'separately on the Projects page. Lessons unlock in order, and '
                'each module project helps you apply what you learned.'
            ),
            'module_count': len(modules),
            'lesson_count': len(lessons),
            'estimated_hours': hours,
        }
    elif pathway_id == 'machine-learning':
        return {
            'kicker': 'Machine Learning specialization',
            'title': 'RUACH Machine Learning Engineering',
            'blurb': (
                'The 12-module Machine Learning specialization: AI tools, math '
                'foundations, data and problem formulation, classical ML, '
                'classification models, unsupervised learning, deep learning from '
                'scratch, computer vision, reproducible training, Neural Networks '
                'with PyTorch, deployment and operations, and Capstone '
                'Integration. This pathway is sequenced from day one and does not '
                'depend on the AI Engineering pathway — switch at any time. '
                'Lessons unlock in order, and each module project helps you '
                'apply what you learned.'
            ),
            'module_count': len(modules),
            'lesson_count': len(lessons),
            'estimated_hours': hours,
        }

    # Fallback
    return {
        'kicker': 'Complete curriculum',
        'title': 'RUACH Engineering',
        'blurb': 'Your learning pathway.',
        'module_count': len(modules),
        'lesson_count': len(lessons),
        'estimated_hours': hours,
    }


def lesson_href(lesson, lesson_id):
    """Where one catalog row opens, given which catalog it came from."""
    from flask import url_for

    source = lesson.get('source', 'ai')
    if source == 'ml':
        return url_for('main.machine_learning_lesson', lesson_id=lesson_id)
    return url_for('main.lesson_detail', lesson_id=lesson_id)


def _ai_completions(user_id):
    return _completed_lesson_ids(user_id)


def _ai_project_modules(user_id):
    from app.models import CourseProject

    return {
        module_id for (module_id,) in CourseProject.query.with_entities(
            CourseProject.module_id
        ).filter_by(user_id=user_id, completed=True).all()
    }

# Backward-compatible alias (M0–M2 transition)
# Original: module_entry(module, completed, project_modules)
# Returns progress fields for one module, shared by every catalog surface.
def module_entry(module, completed, project_modules):
    """Progress fields for one module, shared by every catalog surface."""

    lessons = module.get('lessons') or []
    entry = {
        'id': module['id'],
        'number': module['number'],
        'title': module['title'],
        'total_lessons': len(lessons),
        'estimated_hours': module.get('estimated_hours', 0),
        'project_completed': module['id'] in project_modules,
        'outcome': (
            module.get('outcome')
            or ((module.get('outcomes') or [])[0] if module.get('outcomes')
                else module.get('project') or module.get('description', ''))
        ),
        'study_minutes': sum(
            (lesson.get('study_minutes') or 0) for lesson in lessons
        ),
        'completed_lessons': sum(lesson['id'] in completed for lesson in lessons),
    }
    if module.get('badge'):
        entry['badge'] = module['badge']
    return entry


# Backward-compatible alias (M0–M2 transition)
# Original: is_ml(destination)
def is_ml(destination):
    """Whether a destination token scopes the learner to the ML pathway.

    Accepts both the legacy ``ml`` token and the explicit ``machine-learning``
    identifier so old plans and new enrolments agree.
    """
    return normalize_pathway_id(destination) == 'machine-learning'


# Backward-compatible alias (M0–M2 transition)
# Original: ml_completion_state(user_id)
def ml_completion_state(user_id):
    """Lesson and project completions recorded against the ML pathway.

    ML completions live in their own tables — never in ``LessonCompletion`` or
    ``CourseProject`` — which is what keeps AI and ML progress independent.
    Both tables are multi-pathway, so every query is scoped by ``pathway_id``:
    a row written for a different ML pathway variant must not credit this one.
    """
    from flask import has_request_context, g
    from app.ml_pathway import PATHWAY_ID
    from app.models import MLSpecializationLessonCompletion, MLSpecializationProject

    uid = _user_id(user_id)
    cache = None
    if has_request_context():
        cache = getattr(g, '_ml_completion_state_cache', None)
        if cache is None:
            cache = {}
            g._ml_completion_state_cache = cache
        if uid in cache:
            return cache[uid]
    completed_lessons = {
        row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
            user_id=uid, pathway_id=PATHWAY_ID
        ).all()
    }
    completed_projects = {
        row.module_id for row in MLSpecializationProject.query.filter_by(
            user_id=uid, pathway_id=PATHWAY_ID, completed=True
        ).all()
    }
    state = (completed_lessons, completed_projects)
    if cache is not None:
        cache[uid] = state
    return state


# --------------------------------------------------------------------------
# Enrolment service (M2.1 / M2.6)
# --------------------------------------------------------------------------
PATHWAY_SEEDS = (
    {
        'id': 'shared-foundations',
        'slug': 'shared-foundations',
        'name': 'Shared Foundations',
        'description': 'Core foundational knowledge common to all '
                       'engineering pathways',
        'domain_type': 'FOUNDATION',
    },
    {
        'id': 'ai-engineering',
        'slug': 'ai-engineering',
        'name': 'AI Engineering',
        'description': 'Build intelligent applications and systems with LLMs, '
                       'agents, and production deployment',
        'domain_type': 'SPECIALIZATION',
    },
    {
        'id': 'machine-learning',
        'slug': 'machine-learning',
        'name': 'Machine Learning',
        'description': 'Learn from data and engineer predictive systems',
        'domain_type': 'SPECIALIZATION',
    },
)


def seed_learning_pathways():
    """Idempotently insert the three canonical pathway rows.

    The Alembic migration does this for a managed database; fresh
    ``db.create_all()`` databases (tests, local development) need the same
    rows before enrolments can reference them.
    """
    created = []
    for spec in PATHWAY_SEEDS:
        if db.session.get(LearningPathway, spec['id']) is None:
            db.session.add(LearningPathway(version='1.0.0', status='ACTIVE',
                                           **spec))
            created.append(spec['id'])
    if created:
        db.session.commit()
    return created


SPECIALIZATION_IDS = ('ai-engineering', 'machine-learning')


def _ensure_enrolled(uid, pathway_id):
    """Create or reactivate an enrolment without committing.

    Internal helper for :func:`switch_pathway`, which commits once at the end.
    Mirrors :func:`enrol_learner` semantics: an existing paused row in the
    target pathway is reactivated; other pathways are never touched.
    """
    enrolment = LearnerPathwayEnrollment.query.filter_by(
        learner_id=uid, pathway_id=pathway_id).first()
    if enrolment is None:
        db.session.add(LearnerPathwayEnrollment(
            learner_id=uid, pathway_id=pathway_id, status='ENROLLED'))
    elif enrolment.status not in ('ENROLLED', 'ACTIVE'):
        enrolment.status = 'ENROLLED'


def switch_pathway(user_id, pathway_id):
    """Switch the learner's active specialization, at any time.

    The switch updates only the learner's *focus*: it writes the explicit
    ``CoursePlan.pathway_destination`` the whole app reads, and makes sure the
    learner is enrolled in the shared foundations and the target
    specialisation.  The other specialisation — and its enrolment, progress,
    projects, and credential — is left exactly as it was, so the learner can
    move back and forth freely without losing work.

    Returns the canonical pathway id that is now active.  Raises ``ValueError``
    for anything other than the two specialisations.
    """
    canonical = normalize_pathway_id(pathway_id)
    if canonical not in SPECIALIZATION_IDS:
        raise ValueError(
            "Choose 'ai-engineering' or 'machine-learning' to switch pathways."
        )
    uid = _user_id(user_id)
    if uid is None:
        raise ValueError('A learner id is required to switch pathways.')

    plan = CoursePlan.query.filter_by(user_id=uid).first()
    if plan is None:
        plan = CoursePlan(user_id=uid, track='standard')
        db.session.add(plan)
    plan.pathway_destination = canonical

    seed_learning_pathways()
    # Foundations are the shared start of both courses, so make sure the
    # learner is enrolled in them; the untouched specialisation keeps its
    # enrolment and all of its progress.
    _ensure_enrolled(uid, 'shared-foundations')
    _ensure_enrolled(uid, canonical)
    db.session.commit()
    # The enrolment list changed; drop the per-request cache so the nav and
    # the very next render reflect the switch.
    try:
        from flask import has_request_context, g
        if has_request_context():
            cache = getattr(g, '_pathway_enrolment_cache', None)
            if cache:
                cache.pop(uid, None)
    except Exception:  # pragma: no cover - cache hygiene only
        pass
    return canonical


def enrol_learner(user_id, pathway_id, status='ENROLLED'):
    """Create or reactivate a learner's enrolment in a pathway.

    Idempotent: enrolling in a pathway that is already active returns the
    existing row, so onboarding can be retried safely.  Enrolling in a second
    specialisation never touches the first — that independence is the point of
    the Parallel Pathways model.
    """
    canonical = normalize_pathway_id(pathway_id)
    if canonical is None:
        raise ValueError('A pathway id is required to enrol a learner.')
    seed_learning_pathways()
    uid = _user_id(user_id)
    enrolment = LearnerPathwayEnrollment.query.filter_by(
        learner_id=uid, pathway_id=canonical).first()
    if enrolment is None:
        enrolment = LearnerPathwayEnrollment(
            learner_id=uid, pathway_id=canonical, status=status)
        db.session.add(enrolment)
    elif status in ('ENROLLED', 'ACTIVE') and enrolment.status not in (
            'ENROLLED', 'ACTIVE'):
        enrolment.status = status
    db.session.commit()
    return enrolment


def enrol_learner_in_all(user_id, pathway_ids):
    """Enrol a learner in several pathways independently (e.g. both
    specialisations) and return the enrolments."""
    return [enrol_learner(user_id, pathway_id) for pathway_id in pathway_ids]
