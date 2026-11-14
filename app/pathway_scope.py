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


FOUNDATION_MODULE_IDS = {'sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04', 'sf.05'}

PATHWAY_LABELS = {
    'shared-foundations': 'Shared Foundations',
    'ai-engineering': 'AI Engineering',
    'machine-learning': 'Machine Learning',
}


def active_pathway_enrolments(user_id):
    """Return all active pathway enrolments for a learner.

    Yields ``(LearnerPathwayEnrollment, LearningPathway)`` tuples; each enrolment
    has a ``pathway_id`` ('shared-foundations', 'ai-engineering',
    'machine-learning') that maps to a curriculum domain definition.

    A learner enrolled in both AI Engineering and ML yields two enrolments;
    pausing one does not affect the other.
    """
    from flask import has_request_context, g, session
    from flask_login import current_user as lc_current_user

    key = 'active_pathway_enrolments'
    if has_request_context() and getattr(g, key, None) is not None:
        return g.pathway_destination  # reuse g key for backward compatibility

    enrolments = (
        db.session.query(LearnerPathwayEnrollment, LearningPathway)
        .join(LearningPathway, LearnerPathwayEnrollment.pathway_id == LearningPathway.id)
        .filter(LearnerPathwayEnrollment.learner_id == user_id)
        .filter(LearnerPathwayEnrollment.status.in_(('ENROLLED', 'ACTIVE')))
        .all()
    )
    g.pathway_destination = enrolments  # reuse g key; templates expect iterable
    return enrolments


def is_pathway(user_id, pathway_id):
    """Check whether a learner has an active enrolment in the given pathway."""
    enrolments = active_pathway_enrolments(user_id)
    return any(enrolment.pathway_id == pathway_id for enrolment, _ in enrolments)


def destination_for(user_id=None):
    """Deprecated: use active_pathway_enrolments(user_id) instead.

    Returns the first active pathway_id, or ``None`` if the learner has no
    active enrolments.
    """
    from flask_login import current_user as lc_current_user

    if user_id is None:
        if lc_current_user.is_authenticated:
            user_id = lc_current_user.id
        else:
            return None
    enrolments = active_pathway_enrolments(user_id)
    if enrolments:
        # Return the first enrolment's pathway_id for backward compatibility
        enrolment, _ = enrolments[0]
        return enrolment.pathway_id if hasattr(enrolment, 'pathway_id') else str(enrolment[0].pathway_id)
    return None


def pathway_modules(pathway_id, user_id=None):
    """Module dicts in study order for a given pathway.

    Parameters:
        pathway_id: One of 'shared-foundations', 'ai-engineering', 'machine-learning'.
        user_id: Optional; if provided, foundation evidence is checked for
            prerequisite satisfaction.

    Returns module dicts scoped to the pathway.  For foundation modules,
    completion status is based on existing ``LessonCompletion`` records.
    """
    # Shared Foundations: only foundation modules (sf.00–sf.05)
    if pathway_id == 'shared-foundations':
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
    if pathway_id == 'ai-engineering':
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
    if pathway_id == 'machine-learning':
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

    # Unknown pathway_id — return empty list
    return []


def pathway_lessons(pathway_id, user_id=None):
    """Every lesson for a given pathway, in study order.

    Each entry carries ``_ordinal`` and ``_module`` back-reference so the
    shared templates can render "Lesson N of M" and module captions without
    knowing which manifest a lesson came from.
    """
    lessons = []
    for module in pathway_modules(pathway_id, user_id=user_id):
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

    completed_lessons = {
        row.lesson_id
        for row in LessonCompletion.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }
    completed_projects = {
        row.module_id
        for row in CourseProject.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }

    # Foundation modules: sf.00–sf.05 each have lessons; check completion
    foundation_evidence = {}
    for module_id in sorted(FOUNDATION_MODULE_IDS):
        # Find the module definition from all_modules
        from app.curriculum import all_modules as _all_modules
        for m in _all_modules():
            if m['id'] == module_id:
                lessons = m.get('lessons') or []
                done_lessons = sum(
                    1 for lesson in lessons if lesson['id'] in completed_lessons
                )
                done_projects = sum(
                    module_id in completed_projects
                )
                # Domain-specific competency: both AI and ML can claim satisfied
                # foundation evidence from Shared Foundations regardless of enrolment
                foundation_evidence[module_id] = {
                    'completed_lessons': done_lessons,
                    'total_lessons': len(lessons),
                    'completed_projects': done_projects,
                    'complete': done_lessons == len(lessons) and done_projects > 0,
                    # M3: track competency per pathway (both can claim shared foundation)
                    'ai_satisfied': done_lessons == len(lessons) and done_projects > 0,
                    'ml_satisfied': done_lessons == len(lessons) and done_projects > 0,
                    'evidence_source': 'lesson_completion',  # or 'course_project', 'dual_enrolment'
                }
                break
        if module_id not in foundation_evidence:
            foundation_evidence[module_id] = {
                'completed_lessons': 0,
                'total_lessons': 0,
                'completed_projects': 0,
                'complete': False,
                'ai_satisfied': False,
                'ml_satisfied': False,
                'evidence_source': 'none',
            }

    return foundation_evidence


def foundation_completion_state(user_id):
    """Return whether the learner has completed all foundation modules.

    A foundation is considered complete if the learner has completed all
    foundation lessons (via LessonCompletion) AND has completed at least one
    foundation course project (via CourseProject).
    """
    from app.models import LessonCompletion, CourseProject

    completed_lessons = {
        row.lesson_id
        for row in LessonCompletion.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }
    completed_projects = {
        row.module_id
        for row in CourseProject.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }

    # Check all 6 foundation modules (sf.00–sf.05)
    from app.curriculum import all_modules as _all_modules
    foundation_modules = [
        m for m in _all_modules() if m['id'] in {'sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04', 'sf.05'}
    ]

    all_complete = True
    for module in foundation_modules:
        lessons = module.get('lessons') or []
        done_lessons = sum(1 for lesson in lessons if lesson['id'] in completed_lessons)
        if done_lessons != len(lessons):
            all_complete = False
            break

    if all_complete and len(completed_projects) > 0:
        return True
    return False


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
    """
    import math

    # Get the curriculum modules for this pathway
    modules = pathway_modules(pathway_id, user_id=user_id)

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
    modules = pathway_modules(pathway_id, user_id=user_id)
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
# Returns True if the destination is 'ml'.
def is_ml(destination):
    """Deprecated: use is_pathway(user_id, 'machine-learning') instead."""
    return destination == 'ml'


# Backward-compatible alias (M0–M2 transition)
# Original: ml_completion_state(user_id)
# Returns completed lessons and projects for the ML pathway.
def ml_completion_state(user_id):
    """Deprecated: use foundation_evidence(user_id) for foundations,
    or query MLSpecializationLessonCompletion directly for ML-specific data."""
    from app.models import LessonCompletion, CourseProject
    completed_lessons = {
        row.lesson_id
        for row in LessonCompletion.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }
    completed_projects = {
        row.module_id
        for row in CourseProject.query.filter_by(
            user_id=user_id, completed=True
        ).all()
    }
    return completed_lessons, completed_projects
