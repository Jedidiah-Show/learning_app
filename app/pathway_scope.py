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


# The six Shared Foundations modules in the standalone manifest (sf.00–sf.05)
# and the three foundation modules inside the main AI course (00–02).
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


def destination_for(user_id=None):
    """The learner's confirmed destination as an explicit pathway id.

    Active logic prefers pathway enrolments; when a learner has none (legacy
    accounts or onboarding before enrolment) the deprecated
    ``CoursePlan.pathway_destination`` column is used for rollback
    compatibility and normalised onto the same identifiers.  Returns
    ``'ai-engineering'``, ``'machine-learning'``, ``'shared-foundations'``, or
    ``None`` (undecided / full AI course).

    Failure-tolerant: a database hiccup behaves like no destination rather than
    taking a page down.
    """
    uid = _user_id(user_id)
    if uid is None:
        uid = _current_user_id()
    if uid is None:
        return None

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
                return candidate
        # An unknown enrolment id: preserve it verbatim.
        return next(iter(ids))

    try:
        plan = CoursePlan.query.filter_by(user_id=uid).first()
    except Exception:  # pragma: no cover - defensive
        return None
    if plan is None or not plan.pathway_destination:
        return None
    return normalize_pathway_id(plan.pathway_destination)


def pathway_ids_for(user_id=None):
    """Set of explicit pathway ids the learner can study.

    Learners without enrolments fall back to their legacy destination: an
    ``ml`` learner studies the ML pathway, everyone else the AI course.
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
    if not ids:
        destination = destination_for(uid)
        if destination in ('machine-learning', 'shared-foundations'):
            ids.add(destination)
        elif destination == 'ai-engineering':
            ids.add('ai-engineering')
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
    # Shared Foundations: only foundation modules (sf.00–sf.05)
    if canonical == 'shared-foundations':
        curriculum_path = Path(__file__).parent.parent / 'shared_foundations_curriculum.json'
        with open(curriculum_path) as f:
            curriculum = json.load(f)
        foundation = curriculum['modules']
        # Optionally annotate completion status if user_id given
        if user_id:
            completed_lessons = {
                row.lesson_id
                for row in LessonCompletion.query.filter_by(
                    user_id=user_id, completed=True
                ).all()
            }
            for module in foundation:
                lessons = module.get('lessons') or []
                module['_completed_lessons'] = sum(
                    1 for lesson in lessons if lesson['id'] in completed_lessons
                )
                module['_total_lessons'] = len(lessons)
        return foundation

    # AI Engineering: modules ai.03–ai.11 (foundation modules 00–02 are shared,
    # not duplicated here; they live in Shared Foundations and are referenced
    # via prerequisites)
    if canonical == 'ai-engineering':
        ai_modules = [
            m for m in all_modules()
            if not m['id'].startswith(('00', '01', '02'))
            and m['id'] != '12'
            and not m['id'].startswith('mle.')
        ]
        if user_id:
            completed_lessons = {
                row.lesson_id
                for row in LessonCompletion.query.filter_by(
                    user_id=user_id, completed=True
                ).all()
            }
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
                {**lesson, 'module_id': module['id'], 'module_title': module['title']}
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
            completed_lessons = {
                row.lesson_id
                for row in LessonCompletion.query.filter_by(
                    user_id=user_id, completed=True
                ).all()
            }
            for module in modules:
                lessons = module.get('lessons') or []
                module['_completed_lessons'] = sum(
                    1 for lesson in lessons if lesson['id'] in completed_lessons
                )
                module['_total_lessons'] = len(lessons)
        return modules

    if canonical is None:
        # Undecided learners keep the full AI Engineering course exactly as
        # authored (foundation + specialisation + capstone).
        return list(all_modules())

    # Unknown pathway_id — return empty list
    return []


def foundation_course_modules():
    """The shared foundation modules of the main course (00–02)."""
    return [
        module for module in all_modules()
        if module['id'] in FOUNDATION_COURSE_MODULE_IDS
    ]


def ml_course_modules():
    """The ready ML pathway modules in their shared-course shape."""
    return pathway_modules('machine-learning')


def course_modules(pathway_id, user_id=None):
    """The complete course a learner with this destination studies.

    Unlike :func:`pathway_modules` (which returns a pathway's own authored
    modules), this is the combined catalogue every learner-facing surface
    renders:

    * ``ml`` → shared foundation (00–02) + the ML pathway modules;
    * everything else → the full AI Engineering course (13 modules).
    """
    if is_ml(pathway_id):
        modules = foundation_course_modules() + ml_course_modules()
    else:
        modules = list(all_modules())

    if user_id:
        completed_lessons = {
            row.lesson_id
            for row in LessonCompletion.query.filter_by(
                user_id=_user_id(user_id), completed=True
            ).all()
        }
        for module in modules:
            lessons = module.get('lessons') or []
            module['_completed_lessons'] = sum(
                1 for lesson in lessons if lesson['id'] in completed_lessons
            )
            module['_total_lessons'] = len(lessons)
    return modules


def pathway_lessons(pathway_id, user_id=None):
    """Every lesson for a given pathway, in study order.

    Each entry carries ``_ordinal`` and ``_module`` back-reference so the
    shared templates can render "Lesson N of M" and module captions without
    knowing which manifest a lesson came from.

    ``shared-foundations`` lists the standalone foundation manifest; every
    other destination lists the learner's combined course.
    """
    if normalize_pathway_id(pathway_id) == 'shared-foundations':
        modules = pathway_modules('shared-foundations', user_id=user_id)
    else:
        modules = course_modules(pathway_id, user_id=user_id)
    lessons = []
    for module in modules:
        for lesson in module.get('lessons', []):
            entry = dict(lesson)
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
    completed_lessons = {
        row.lesson_id
        for row in LessonCompletion.query.filter_by(
            user_id=uid, completed=True
        ).all()
    }
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
            'ai_satisfied': complete,
            'ml_satisfied': complete,
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
    """Whether the learner has completed the shared foundation.

    Shared foundation evidence is reusable across both specialisations, so
    either canonical manifestation counts: the standalone Shared Foundations
    manifest (``sf.*``) or the legacy foundation modules (00-02) inside the
    original AI course.  The learner's more advanced representation is
    reported, and completion of either opens the pathway-change gate.
    """
    from app.models import CourseProject

    uid = _user_id(user_id)
    completed_lessons = {
        row.lesson_id for row in LessonCompletion.query.filter_by(
            user_id=uid, completed=True
        ).all()
    }
    completed_projects = {
        row.module_id for row in CourseProject.query.filter_by(
            user_id=uid, completed=True
        ).all()
    }
    shared = _foundation_state_for(
        foundation_modules(), completed_lessons, completed_projects)
    legacy = _foundation_state_for(
        foundation_course_modules(), completed_lessons, completed_projects)

    def progress_ratio(state):
        return (
            state['completed_lessons'] + state['completed_projects']
        ) / max(1, state['total_lessons'] + state['total_projects'])

    chosen = shared if progress_ratio(shared) >= progress_ratio(legacy) else legacy
    return {**chosen, 'complete': shared['complete'] or legacy['complete']}


def foundation_modules():
    """Return the six Shared Foundations module definitions (sf.00–sf.05).

    Each module dict includes lessons, estimated_hours, and other module-level
    metadata.  Used by the foundation completion flow to iterate over all
    foundation modules and create LessonCompletion / CourseProject records.
    """
    from app.curriculum import all_modules as _all_modules
    import json
    from pathlib import Path

    # Load the shared foundations curriculum (6 modules sf.00–sf.05)
    curriculum_path = Path(__file__).parent.parent / 'shared_foundations_curriculum.json'
    with open(curriculum_path) as f:
        curriculum = json.load(f)
    return curriculum['modules']


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

    # Get completed lessons for this user
    completed_lessons = {
        row.lesson_id
        for row in LessonCompletion.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }

    # Get completed project modules
    from app.models import CourseProject
    completed_projects = {
        row.module_id
        for row in CourseProject.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }

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

    if pathway_id == 'shared-foundations':
        return {
            'kicker': 'Shared foundation',
            'title': 'RUACH Shared Foundations',
            'blurb': (
                'Core foundational knowledge common to all engineering pathways: '
                'Programming Foundations, Python Foundations, Software Engineering '
                'Foundations, Development Tools and Workflow, API and Backend '
                'Foundations, and Data and Computational Thinking. Complete these '
                'modules before or alongside either specialisation.'
            ),
            'module_count': len(modules),
            'lesson_count': len(lessons),
            'estimated_hours': hours,
        }
    elif pathway_id == 'ai-engineering':
        return {
            'kicker': 'Complete curriculum',
            'title': 'RUACH AI & ML Engineering',
            'blurb': (
                'A focused path from foundations to production systems. Start with '
                'the beginner route if programming is new to you; it explains what '
                'to expect and where to get support. Your pace is chosen separately '
                'on the Projects page. Lessons unlock in order, and each module '
                'project helps you apply what you learned.'
            ),
            'module_count': len(modules),
            'lesson_count': len(lessons),
            'estimated_hours': hours,
        }
    elif pathway_id == 'machine-learning':
        return {
            'kicker': 'Shared foundation and your ML pathway',
            'title': 'RUACH ML Engineering',
            'blurb': (
                'The shared foundation — Programming Foundations, Python Foundations, '
                'Software Engineering Foundations, Development Tools and Workflow, '
                'API and Backend Foundations, and Data and Computational Thinking — '
                'then the 12 ML pathway modules: AI tools, math foundations, data '
                'and problem formulation, classical ML, classification models, '
                'unsupervised learning, deep learning from scratch, computer vision, '
                'reproducible training, Neural Networks with PyTorch, deployment and '
                'operations, and Capstone Integration. The AI Engineering continuation '
                'belongs to the AI Engineering pathway and is not part of your course. '
                'Lessons unlock in order, and each module project helps you apply what '
                'you learned.'
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
    from app.models import LessonCompletion

    return {
        lesson_id for (lesson_id,) in LessonCompletion.query.with_entities(
            LessonCompletion.lesson_id
        ).filter_by(user_id=user_id, completed=True).all()
    }


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
    """
    from app.ml_pathway import PATHWAY_ID
    from app.models import MLSpecializationLessonCompletion, MLSpecializationProject

    uid = _user_id(user_id)
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
    return completed_lessons, completed_projects


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
