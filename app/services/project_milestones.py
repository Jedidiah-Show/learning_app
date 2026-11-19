"""Project milestones derived from published deliverable lists (M2.4).

Each AI/ML module publishes ``project_deliverables`` in its manifest. Those
are the milestone *definitions* — stable, ordered, and shared with the
learner. Per-milestone state (completed + note) is stored in
``project_milestone``.

Domain context is enforced here and in the routes: ML milestone state never
credits AI projects and vice versa.
"""

from app import db
from app.models import ProjectMilestone

DOMAINS = ('ai-engineering', 'machine-learning')


def _module(domain, project_key):
    if domain == 'machine-learning':
        from app.ml_pathway import machine_learning_pathway
        modules = machine_learning_pathway()['modules']
    elif domain == 'ai-engineering':
        from app.ai_pathway import ai_engineering_pathway
        modules = ai_engineering_pathway()['modules']
    else:
        return None
    return next((m for m in modules if m['id'] == project_key), None)


def milestone_definitions(domain, project_key):
    module = _module(domain, project_key)
    if module is None:
        return None
    return [
        {'id': f'm{index + 1}', 'index': index, 'label': label}
        for index, label in enumerate(module.get('project_deliverables') or [])
    ]


def milestone_state(user_id, domain, project_key):
    definitions = milestone_definitions(domain, project_key)
    if definitions is None:
        return None
    rows = {
        row.milestone_id: row
        for row in ProjectMilestone.query.filter_by(
            user_id=user_id, domain=domain, project_key=project_key,
        ).all()
    }
    return [
        {
            'id': d['id'],
            'index': d['index'],
            'label': d['label'],
            'completed': bool(rows.get(d['id']) and rows[d['id']].completed),
            'note': (rows[d['id']].note if d['id'] in rows else None),
            'completed_at': (
                rows[d['id']].completed_at.isoformat()
                if d['id'] in rows and rows[d['id']].completed_at else None
            ),
        }
        for d in definitions
    ]


def set_milestone(user_id, domain, project_key, milestone_id, completed, note=None):
    if domain not in DOMAINS:
        raise ValueError(f'Unknown domain {domain!r}')
    definitions = milestone_definitions(domain, project_key)
    if definitions is None:
        raise ValueError('Unknown project')
    valid_ids = {d['id'] for d in definitions}
    if milestone_id not in valid_ids:
        raise ValueError(f'Unknown milestone {milestone_id!r}; expected one of {sorted(valid_ids)}')
    if note is not None and (not isinstance(note, str) or len(note) > 4000):
        raise ValueError('note must be a string of at most 4000 characters')
    from datetime import datetime, timezone
    row = ProjectMilestone.query.filter_by(
        user_id=user_id, domain=domain, project_key=project_key,
        milestone_id=milestone_id,
    ).first()
    if row is None:
        row = ProjectMilestone(
            user_id=user_id, domain=domain, project_key=project_key,
            milestone_id=milestone_id,
        )
        db.session.add(row)
    row.completed = bool(completed)
    row.note = (note or '').strip() or None
    row.completed_at = datetime.now(timezone.utc) if completed else None
    db.session.commit()
    return milestone_state(user_id, domain, project_key)


def progress(user_id, domain, project_key):
    state = milestone_state(user_id, domain, project_key)
    if state is None:
        return None
    done = sum(1 for item in state if item['completed'])
    return {'total': len(state), 'completed': done}
