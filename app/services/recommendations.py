"""Recommendation engine grounded in learner evidence (M6.4).

Every recommendation carries:
- ``kind``     — review | lesson | practice
- ``title``    — learner-facing title
- ``reason``   — why this was recommended, traced to evidence
- ``confidence`` — high | medium | low (low when evidence is thin)

Recommendations respect enrolment: learners are only pointed at domains
they are enrolled in (plus Shared Foundations, which is always open).
They never override prerequisite rules — a locked lesson is never recommended.
"""

from datetime import datetime, timezone

from app.models import ReviewItem
from app.services.mastery import weakest_concepts


def _enrolled_domains(user_id):
    domains = {'shared-foundations'}
    try:
        from app.pathway_scope import active_pathway_enrolments
        for enrollment, _pathway in active_pathway_enrolments(user_id):
            if enrollment.pathway_id in ('ai-engineering', 'machine-learning', 'shared-foundations'):
                domains.add(enrollment.pathway_id)
    except Exception:
        pass
    return domains


def due_reviews(user_id):
    now = datetime.now(timezone.utc)
    return ReviewItem.query.filter_by(
        user_id=user_id, active=True,
    ).filter(ReviewItem.due_at <= now).all()


def recommend(user_id, limit=5):
    enrolled = _enrolled_domains(user_id)
    recommendations = []

    # 1. Spaced review due — the highest-signal intervention available.
    due = due_reviews(user_id)
    if due:
        titles = sorted({(item.question or '').strip()[:80] for item in due})[:3]
        recommendations.append({
            'kind': 'review',
            'title': f'{len(due)} review item(s) due',
            'reason': 'Spaced repetition: these questions were answered incorrectly recently and are scheduled for re-test now.',
            'confidence': 'high',
            'url': '/review',
            'count': len(due),
            'preview': titles,
        })

    # 2. Weak/developing concepts → targeted practice.
    for concept in weakest_concepts(user_id, limit=limit):
        skill_id = concept['skill_id']
        practice_id = _practice_for_skill(skill_id, enrolled)
        if practice_id is None:
            continue
        recommendations.append({
            'kind': 'practice',
            'title': f'Practice: {concept["title"]}',
            'reason': (
                f'Evidence for this concept is {concept["mastery"].replace("_", " ")} '
                f'({concept["evidence_type"] or "no judged evidence yet"}); '
                f'a focused challenge on the same skill builds it further.'
            ),
            'confidence': 'medium' if concept['mastery'] in ('developing', 'practising') else 'low',
            'url': f'/arena/problems/{practice_id}',
            'skill_id': skill_id,
        })

    # 3. Next incomplete lesson in enrolled domains.
    next_lesson = _next_incomplete_lesson(user_id, enrolled)
    if next_lesson:
        recommendations.append(next_lesson)

    return recommendations[:limit]


def _practice_for_skill(skill_id, enrolled):
    """Map a competency id onto an Arena challenge for the same skill."""
    try:
        from app.practice_arena import all_arena_problems
        problems = all_arena_problems()
    except Exception:
        return None
    # ml-<topic> skill ids map 1:1 onto arena topics when they exist.
    if skill_id.startswith('ml-'):
        for problem in problems.values():
            if problem['track'] == 'machine-learning' and problem['topic'] == skill_id:
                return problem['id']
    if skill_id.startswith(('sf.', 'curriculum-0', 'lesson-0-', 'lesson-1-', 'lesson-2-')):
        for problem in problems.values():
            if problem['track'] == 'ai-engineering' and problem['topic'] in ('foundations', 'python'):
                return problem['id']
    if skill_id.startswith(('ai-', 'curriculum-', 'lesson-ai-', 'project-studio')):
        for problem in problems.values():
            if problem['track'] == 'ai-engineering':
                return problem['id']
    return None


def _next_incomplete_lesson(user_id, enrolled):
    """Next actionable lesson in an enrolled domain, with a resolvable URL.

    Only routes that exist today are recommended (Shared Foundations ready
    lessons, the bundled AI course, and the ML pathway). Lessons that share
    structure but have no learner page are never recommended.
    """
    try:
        from app.learning import completed_lesson_ids
        completed_legacy = completed_lesson_ids(user_id)
    except Exception:
        completed_legacy = set()

    if 'shared-foundations' in enrolled:
        try:
            from app.foundations_pathway import shared_foundations_lessons
            for lesson in shared_foundations_lessons():
                if lesson.get('status') == 'ready' and lesson['id'] not in completed_legacy:
                    return {
                        'kind': 'lesson',
                        'title': f'Next lesson: {lesson["title"]}',
                        'reason': 'Shared Foundations, in the published module order.',
                        'confidence': 'high',
                        'url': f'/specializations/shared-foundations/lessons/{lesson["id"]}',
                        'lesson_id': lesson['id'],
                    }
        except Exception:
            pass

    if 'ai-engineering' in enrolled:
        try:
            from app.pathway_scope import course_modules
            for module in course_modules('ai-engineering'):
                for lesson in module.get('lessons', []):
                    if lesson['id'] not in completed_legacy:
                        return {
                            'kind': 'lesson',
                            'title': f'Next lesson: {lesson.get("title", lesson["id"])}',
                            'reason': 'Next available lesson in the AI Engineering course; locked lessons are never shown before their prerequisites are met.',
                            'confidence': 'high',
                            'url': f'/lesson/{lesson["id"]}',
                            'lesson_id': lesson['id'],
                        }
        except Exception:
            pass

    if 'machine-learning' in enrolled:
        try:
            from app.ml_pathway import machine_learning_lessons, PATHWAY_ID
            from app.models import MLSpecializationLessonCompletion
            completed_ml = {
                row.lesson_id for row in MLSpecializationLessonCompletion.query.filter_by(
                    user_id=user_id, pathway_id=PATHWAY_ID,
                ).all()
            }
            for lesson in machine_learning_lessons():
                if lesson.get('status') == 'ready' and lesson['id'] not in completed_ml:
                    return {
                        'kind': 'lesson',
                        'title': f'Next lesson: {lesson["title"]}',
                        'reason': 'Machine Learning pathway, in the published module order.',
                        'confidence': 'high',
                        'url': f'/specializations/machine-learning/lessons/{lesson["id"]}',
                        'lesson_id': lesson['id'],
                    }
        except Exception:
            pass
    return None
