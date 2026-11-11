"""What a learner studies, decided by their confirmed pathway.

``CoursePlan.pathway_destination`` is the single source of truth for the
pathway a learner confirmed during onboarding.  Every shared surface — the
lesson catalog, the projects page, pacing, search, the admin portal — asks this
module what to show instead of reaching straight for ``app.curriculum``, which
only ever holds the AI Engineering course.

A destination of ``ml`` narrows the course to the shared foundation (modules
00-02) plus the ML pathway's six namespaced modules; ``ai``, ``undecided``,
and unset keep the full AI Engineering course exactly as authored.  The ML
manifest stays outside ``app.curriculum`` (see ``app.ml_pathway``), so ML
modules are normalised here into the same shape the shared templates render.
"""

from app.curriculum import all_modules
from app.ml_pathway import PATHWAY_ID, machine_learning_pathway
from app.models import CoursePlan


FOUNDATION_MODULE_IDS = ('00', '01', '02')

PATHWAY_NAMES = {
    'ml': 'Machine Learning Engineering',
    'ai': 'AI Engineering',
}

PATHWAY_NAV_LABELS = {
    'ml': 'ML Pathway',
    'ai': 'AI Pathway',
}


def is_ml(destination):
    """Only a confirmed ML destination narrows the shared surfaces."""
    return destination == 'ml'


def pathway_label(destination):
    """Full discipline name for a destination (undecided falls back to AI)."""
    return PATHWAY_NAMES.get(destination, PATHWAY_NAMES['ai'])


def pathway_nav_label(destination):
    """Nav item that names the destination the learner actually chose."""
    return PATHWAY_NAV_LABELS.get(destination, PATHWAY_NAV_LABELS['ai'])


def destination_for(user):
    """Confirmed destination for ``user``, cached on ``g`` for the owner.

    Failure-tolerant by design: a missing plan or a database hiccup must never
    take a page down, so an unreadable destination behaves like no destination
    and the learner keeps the full shared course.
    """
    from flask import has_request_context
    from flask_login import current_user

    if (
        has_request_context()
        and current_user.is_authenticated
        and getattr(current_user, 'id', None) == getattr(user, 'id', None)
    ):
        from app import current_pathway_destination
        return current_pathway_destination()
    try:
        plan = CoursePlan.query.filter_by(user_id=user.id).first()
        return plan.pathway_destination if plan else None
    except Exception:  # pragma: no cover - defensive: never fail a page render
        return None


def foundation_modules():
    """The shared foundation: modules 00-02 of the AI Engineering course."""
    return [
        module for module in all_modules()
        if module['id'] in FOUNDATION_MODULE_IDS
    ]


def ml_completion_state(user_id):
    """Lesson and project completions recorded against the ML pathway."""
    from app.models import MLSpecializationLessonCompletion, MLSpecializationProject

    completed = {
        row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID
        ).all()
    }
    projects = {
        row.module_id for row in MLSpecializationProject.query.filter_by(
            user_id=user_id, pathway_id=PATHWAY_ID, completed=True
        ).all()
    }
    return completed, projects


def _ml_module_lessons(module):
    """Published pathway lessons, in authored order, marked as ML content."""
    return [
        {**lesson,
         'module_id': module['id'],
         'module_title': module['title'],
         'module_number': module['number'],
         'source': 'ml'}
        for lesson in module['lessons']
        if lesson.get('status') == 'ready'
    ]


def ml_modules():
    """ML pathway modules normalised into the shared module shape.

    The shared templates read ``description``, ``assumed_prerequisites``,
    ``readiness_check``, ``resources``, and ``project`` on every module, so the
    manifest's namespaced modules supply equivalents rather than leaving the
    catalog page with holes.
    """
    pathway = machine_learning_pathway()
    entry_requirements = pathway.get('entry_requirements') or ''
    modules = []
    for module in pathway['modules']:
        lessons = _ml_module_lessons(module)
        if not lessons:
            # Keep authored-but-unpublished modules out of learner counts and
            # navigation until they contain at least one ready lesson.
            continue
        modules.append({
            'id': module['id'],
            'number': module['number'],
            'title': module['title'],
            'description': module.get('summary') or '',
            'estimated_hours': module.get('estimated_hours', 0),
            'assumed_prerequisites': entry_requirements,
            'readiness_check': (
                'Work through every lesson in this module, then submit its '
                'project to unlock the next module.'
            ),
            'resources': {},
            'project': module.get('project') or '',
            'project_rubric': module.get('project_rubric') or [],
            'lessons': lessons,
            'source': 'ml',
            # Foundation 0-2 and the pathway's 1-4 collide, so every shared
            # surface has to say which course a module belongs to.
            'badge': f'ML pathway · Module {module["number"]}',
            'outcome': module.get('summary') or module.get('title', ''),
        })
    return modules


def pathway_modules(destination):
    """Module dicts in study order for this destination.

    Entries are copies: ``app.curriculum`` and ``app.ml_pathway`` cache their
    manifests, and a route that stamped a badge onto a shared dict would leak
    it into every later render.
    """
    if not is_ml(destination):
        return list(all_modules())
    modules = [
        {**module, 'badge': f'Shared foundation · Module {module["number"]}'}
        for module in foundation_modules()
    ]
    return modules + ml_modules()


def pathway_lessons(destination):
    """Every lesson this learner may study, in study order.

    Each entry carries the scoped ``_ordinal`` and a ``_module`` back-reference
    so the shared templates can render "Lesson N of M" and module captions
    without knowing which manifest a lesson came from.  Entries are copies:
    both manifests are cached and must not be stamped per request.
    """
    lessons = []
    for module in pathway_modules(destination):
        for lesson in module['lessons']:
            entry = dict(lesson)
            entry['_ordinal'] = len(lessons) + 1
            entry['_module'] = module
            lessons.append(entry)
    return lessons


def lesson_by_id(destination, lesson_id):
    """Scoped catalog lookup that understands both manifests."""
    if not lesson_id:
        return None
    return next(
        (lesson for lesson in pathway_lessons(destination)
         if lesson['id'] == lesson_id),
        None,
    )


def pathway_lesson_count(destination):
    """Denominator for this destination, used where counts are rendered."""
    return len(pathway_lessons(destination))


def foundation_completion_state(user_id):
    """Whether the shared foundation (modules 00-02) is fully complete.

    Gates the learner's single pathway-change request: the request opens only
    after every foundation lesson and every foundation module project is done,
    so the lock cannot be undone before the shared modules are finished.
    Returns a dict with the lesson/project counts and a ``complete`` flag.
    """
    from app.models import CourseProject, LessonCompletion

    foundation = foundation_modules()
    lessons = [
        lesson for module in foundation for lesson in module.get('lessons') or []
    ]
    completed_lessons = {
        row.lesson_id for row in LessonCompletion.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }
    completed_projects = {
        row.module_id for row in CourseProject.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }
    done_lessons = sum(lesson['id'] in completed_lessons for lesson in lessons)
    done_projects = sum(
        module['id'] in completed_projects for module in foundation
    )
    total_lessons, total_projects = len(lessons), len(foundation)
    return {
        'completed_lessons': done_lessons,
        'total_lessons': total_lessons,
        'completed_projects': done_projects,
        'total_projects': total_projects,
        'complete': (
            done_lessons == total_lessons and done_projects == total_projects
        ),
    }


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


def pathway_pace(user_id, destination, weekly_hours=None):
    """One unified plan over the learner's whole course, or ``None``.

    Only a confirmed ML destination gets this: its course spans the shared
    foundation and the pathway, and neither the 12/10/5-month AI tracks nor
    the ML-only plan describes that combination.  The plan is derived from the
    weekly hours the learner chose during onboarding and is presented in weeks
    and months, so the pace follows the pathway instead of the AI course.
    """
    import math

    if not is_ml(destination):
        return None
    if weekly_hours is None:
        plan = CoursePlan.query.filter_by(user_id=user_id).first()
        weekly_hours = plan.weekly_hours if plan and plan.weekly_hours else None
    if (
        not isinstance(weekly_hours, int) or isinstance(weekly_hours, bool)
        or weekly_hours <= 0
    ):
        weekly_hours = 6

    completed_ai = _ai_completions(user_id)
    completed_ml, project_ml = ml_completion_state(user_id)
    completed = completed_ai | completed_ml
    project_modules = _ai_project_modules(user_id) | project_ml

    modules = []
    total_hours = 0.0
    total_lessons = 0
    completed_lessons = 0
    for module in pathway_modules(destination):
        hours = float(module.get('estimated_hours') or 0)
        total_hours += hours
        lessons = module['lessons']
        done = sum(lesson['id'] in completed for lesson in lessons)
        total = len(lessons)
        project_done = module['id'] in project_modules
        reading_hours = round(
            sum(lesson.get('study_minutes') or 0 for lesson in lessons) / 60, 1
        )
        total_lessons += total
        completed_lessons += done
        modules.append({
            'id': module['id'], 'number': module['number'],
            'title': module['title'],
            'badge': module.get('badge') or f'Module {module["number"]}',
            'source': module.get('source') or 'ai',
            'estimated_hours': round(hours, 1),
            'reading_hours': reading_hours,
            'project_hours': round(max(hours - reading_hours, 0), 1),
            'completed_lessons': done, 'total_lessons': total,
            'project_completed': project_done,
            'complete': bool(total and done == total and project_done),
            'percent': round(done / total * 100) if total else 0,
        })

    weeks = math.ceil(total_hours / weekly_hours) if total_hours else 0
    months = max(1, math.ceil(weeks / 4.345)) if weeks else 0
    seen_complete = True
    for item in modules:
        if item['complete']:
            item['status'] = 'Complete'
        elif seen_complete:
            item['status'] = 'In progress'
            seen_complete = False
        else:
            item['status'] = 'Up next'
    return {
        'pathway_id': PATHWAY_ID,
        'scope': 'pathway',
        'label': pathway_label(destination),
        'weekly_hours': weekly_hours,
        'total_hours': round(total_hours, 1),
        'estimated_weeks': weeks,
        'estimated_months': months,
        # Catch-up time is metadata, never an extra unit of schedule (same rule
        # as the shared course milestones).
        'review_hours': round(total_hours * 0.2, 1),
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'modules': modules,
    }


def pathway_header(destination):
    """Copy for the lesson catalog header, so it names the right course."""
    modules = pathway_modules(destination)
    lessons = [lesson for module in modules for lesson in module['lessons']]
    hours = round(sum(
        float(module.get('estimated_hours') or 0) for module in modules
    ), 1)
    if is_ml(destination):
        return {
            'kicker': 'Shared foundation and your ML pathway',
            'title': 'RUACH ML Engineering',
            'blurb': (
                'The shared foundation — AI Engineering Foundations, Python, '
                'and Backend Engineering — then the six ML pathway modules: '
                'production tabular machine learning from data and problem '
                'formulation through classical ML, reproducible training, '
                'serving, Advanced PyTorch, and Capstone Integration. The AI '
                'Engineering continuation belongs to the AI Pathway and is not '
                'part of your course. Lessons unlock in order, and each module '
                'project helps you apply what you learned.'
            ),
            'module_count': len(modules),
            'lesson_count': len(lessons),
            'estimated_hours': hours,
        }
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


def lesson_href(lesson, lesson_id):
    """Where one catalog row opens, given which catalog it came from."""
    from flask import url_for

    if lesson.get('source') == 'ml':
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
