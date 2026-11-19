"""Arena-facing recommendations, traced to competency evidence (M3.5).

Reuses the mastery-derived weak/developing concepts; every recommendation
points at a concrete published challenge, carries a reason, respects track
enrolment and problem prerequisites, and can be dismissed by the learner.
"""

from app.models import ArenaRecommendationDismissal


def _enrolled_tracks(user_id):
    tracks = {'algorithms'}  # algorithms track is always open
    try:
        from app.pathway_scope import active_pathway_enrolments
        for enrollment, _pathway in active_pathway_enrolments(user_id):
            if enrollment.pathway_id == 'machine-learning':
                tracks.add('machine-learning')
            elif enrollment.pathway_id == 'ai-engineering':
                tracks.add('ai-engineering')
    except Exception:
        pass
    return tracks


def dismissed_ids(user_id):
    return {
        row.problem_id
        for row in ArenaRecommendationDismissal.query.filter_by(user_id=user_id).all()
    }


def dismiss(user_id, problem_id):
    if not problem_id or not isinstance(problem_id, str) or len(problem_id) > 120:
        raise ValueError('problem_id must be a short string')
    from app import db
    from app.models import utcnow
    row = ArenaRecommendationDismissal.query.filter_by(
        user_id=user_id, problem_id=problem_id,
    ).first()
    if row is None:
        db.session.add(ArenaRecommendationDismissal(
            user_id=user_id, problem_id=problem_id, dismissed_at=utcnow(),
        ))
        db.session.commit()
    return problem_id


def recommendations_for(user_id, limit=6):
    tracks = _enrolled_tracks(user_id)
    dismissed = dismissed_ids(user_id)
    from app.practice_arena import all_arena_problems
    from app.services.mastery import weakest_concepts

    problems = all_arena_problems()
    picks = []
    seen = set()
    for concept in weakest_concepts(user_id, limit=limit * 2):
        skill_id = concept['skill_id']
        match = None
        for problem in problems.values():
            if problem['id'] in dismissed or problem['id'] in seen:
                continue
            if problem['track'] not in tracks:
                continue
            if problem['track'] == 'machine-learning' and problem['topic'] == skill_id:
                match = problem
                break
            if problem['track'] == 'ai-engineering' and problem['topic'] in ('foundations', 'python', 'backend'):
                match = problem
                break
        if match is None:
            continue
        seen.add(match['id'])
        picks.append({
            'problem_id': match['id'],
            'title': match['title'],
            'difficulty': match['difficulty'],
            'estimated_minutes': match['estimated_minutes'],
            'url': f"/arena/problems/{match['id']}",
            'reason': (
                f"Builds directly on '{concept['title']}', which shows as "
                f"{concept['mastery'].replace('_', ' ')} in your evidence "
                f"({concept['evidence_type'] or 'no judged outcome yet'})."
            ),
            'confidence': 'medium' if concept['mastery'] in ('developing', 'practising') else 'low',
        })
        if len(picks) >= limit:
            break
    return picks
