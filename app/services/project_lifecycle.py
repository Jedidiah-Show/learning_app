"""Shared project lifecycle engine (M2.3).

One state machine for both AI Engineering and Machine Learning projects:

    draft → planned → in_progress → submitted → under_review
        → revision_requested → approved → published (→ archived)

Discipline is deliberately left out: this module knows *stages*, not rubrics.
AI and ML keep their own assessment rules; both call ``record_transition``
to make a transition, and this module enforces who may make it.

Rules:
- Learners move their own projects forward through the working stages and
  may archive them.
- Only privileged reviewers (``User.is_admin``, until M4's role model) may
  approve, request revision or move a project into review. A reviewer may
  never approve their own project (separation of duties, same rule as M0).
- Automated/system transitions pass ``actor=None`` and are noted as such.
- Same-stage "transitions" are idempotent no-ops (safe to call from
  submit/retry handlers).
- Every transition appends a row to ``project_lifecycle_event``; history is
  append-only and never rewritten.
"""

from app import db
from app.models import ProjectLifecycleEvent
from app.services.authorization import can_assess_competency

DOMAINS = ('ai-engineering', 'machine-learning')

STAGES = (
    'draft', 'planned', 'in_progress', 'submitted', 'under_review',
    'revision_requested', 'approved', 'published', 'archived',
)

# to_stage -> (allowed from_stages, actor rule)
# Submitted accepts working stages, a prior submission, and an approved
# project being deliberately re-opened for reassessment (history is kept).
# Published and archived are terminal — they require archive/unpublish, not
# a silent overwrite.
TRANSITIONS = {
    'planned': ({'draft'}, 'owner'),
    'in_progress': ({'planned'}, 'owner'),
    'submitted': ({'in_progress', 'revision_requested', 'submitted', 'planned', 'draft', 'approved'}, 'owner'),
    'under_review': ({'submitted'}, 'reviewer'),
    'revision_requested': ({'under_review', 'submitted'}, 'reviewer'),
    'approved': ({'under_review', 'submitted'}, 'reviewer'),
    'published': ({'approved'}, 'owner'),
    'archived': (set(STAGES) - {'archived'}, 'owner_or_reviewer'),
}

LIFECYCLE_DOMAINS = tuple(DOMAINS)


class LifecycleError(Exception):
    """Raised when a transition is not allowed."""


def _require_domain(domain):
    if domain not in DOMAINS:
        raise LifecycleError(f'Unknown project domain {domain!r}; expected one of {DOMAINS}')


def current_stage(user_id, domain, project_key, session=None):
    _require_domain(domain)
    session = session or db.session
    row = (
        session.query(ProjectLifecycleEvent)
        .filter_by(user_id=user_id, domain=domain, project_key=project_key)
        .order_by(ProjectLifecycleEvent.id.desc())
        .first()
    )
    return row.to_stage if row else 'draft'


def history(user_id, domain, project_key):
    _require_domain(domain)
    rows = (
        ProjectLifecycleEvent.query
        .filter_by(user_id=user_id, domain=domain, project_key=project_key)
        .order_by(ProjectLifecycleEvent.created_at.asc(), ProjectLifecycleEvent.id.asc())
        .all()
    )
    return [
        {
            'from_stage': r.from_stage,
            'to_stage': r.to_stage,
            'actor_user_id': r.actor_user_id,
            'note': r.note,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _actor_ok(rule, actor, owner_id):
    if rule == 'owner':
        return actor is not None and int(getattr(actor, 'id', actor)) == int(owner_id)
    if rule == 'reviewer':
        # Automated reviews pass actor=None; human review requires the
        # privileged-reviewer check and separation of duties from the owner.
        if actor is None:
            return True
        if owner_id == getattr(actor, 'id', None):
            return False
        return can_assess_competency(actor, owner_id)
    if rule == 'owner_or_reviewer':
        if actor is None:
            return False
        if int(getattr(actor, 'id', -1)) == int(owner_id):
            return True
        return can_assess_competency(actor, owner_id)
    return False


def record_transition(user_id, domain, project_key, to_stage, actor=None,
                      note=None, session=None):
    """Validate and append a lifecycle transition.

    Flushes but never commits — the caller owns the transaction so the
    transition can be committed atomically with the evidence it describes.
    Returns the resulting stage. Idempotent: same-stage calls are no-ops.
    """
    _require_domain(domain)
    if to_stage not in STAGES:
        raise LifecycleError(f'Unknown stage {to_stage!r}')
    session = session or db.session
    stage = current_stage(user_id, domain, project_key, session=session)
    if stage == to_stage:
        return stage
    rule = TRANSITIONS.get(to_stage)
    if rule is None:
        raise LifecycleError(f'No transitions into {to_stage!r} are defined')
    from_stages, actor_rule = rule
    if stage not in from_stages:
        raise LifecycleError(
            f'Cannot move {domain}/{project_key} from {stage!r} to {to_stage!r}'
        )
    if not _actor_ok(actor_rule, actor, user_id):
        raise LifecycleError(
            f'Actor is not authorized to move this project to {to_stage!r}'
        )
    session.add(ProjectLifecycleEvent(
        user_id=user_id, domain=domain, project_key=project_key,
        from_stage=stage, to_stage=to_stage,
        actor_user_id=getattr(actor, 'id', None) if actor is not None else None,
        note=(note or '')[:300] or None,
    ))
    session.flush()
    return to_stage


def submit(user_id, domain, project_key, actor, note='Project evidence submitted'):
    return record_transition(user_id, domain, project_key, 'submitted',
                             actor=actor, note=note)
