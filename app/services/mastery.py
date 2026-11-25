"""Evidence-driven, concept-level mastery model (M6.2).

Mastery is derived — never stored, never self-declared, and never inferred
from lesson completion alone. Inputs are authoritative records only:

- ``UserSkillProgress``  — evidence-tagged competency status written by the
  practice/lab/project verification flows
- ``SkillVerification``  — append-only verification transitions

States (concept level):

``not_introduced``   — no rows at all
``introduced``       — an evidence row exists but no practice outcome yet
``practising``       — practice evidence (lesson/lab attempts), unverified outcome
``developing``       — developing status with judged practice or project evidence
``proficient``       — demonstrated evidence (≥1 judged/project evidence accepted)
``mastered``         — repeated accepted evidence (status MASTERED)
``needs_review``     — latest verification transition is REVOKED

Lesson completion alone can never reach ``proficient`` or ``mastered``: those
require evidence_type in {PROBLEM, LAB, PROJECT}.
"""

from app import db
from app.models import SkillNode, SkillVerification, UserSkillProgress

MASTERY_STATES = (
    'not_introduced', 'introduced', 'practising', 'developing',
    'proficient', 'mastered', 'needs_review',
)

_EVIDENCE_FOR_PROFICIENT = {'PROBLEM', 'LAB', 'PROJECT'}


def _skill_domain(skill_id, category):
    sid = (skill_id or '').lower()
    category = (category or '').lower()
    if sid.startswith(('ml-', 'mle.')) or category == 'machine-learning':
        return 'machine-learning'
    if sid.startswith(('sf.', 'lesson-sf-', 'curriculum-00', 'curriculum-01',
                       'curriculum-02', 'lesson-0-', 'lesson-1-', 'lesson-2-')):
        return 'shared-foundations'
    if sid.startswith(('ai-', 'lesson-ai-', 'curriculum-', 'project-studio')) or category in {'projects', 'curriculum', 'ai-engineering'}:
        return 'ai-engineering'
    if category in {'algorithms', 'shared-foundations', 'foundations'}:
        return 'shared-foundations'
    return 'shared-foundations'


def _verification_stage(events):
    stage = 'UNVERIFIED'
    for event in events:
        stage = event.to_status
    return stage


def _state_for(progress, events):
    if progress is None:
        return 'needs_review' if _verification_stage(events) == 'REVOKED' else 'not_introduced'
    if _verification_stage(events) == 'REVOKED':
        return 'needs_review'
    status = progress.status or 'NOT_STARTED'
    evidence_type = (progress.evidence_type or '').upper()
    if status == 'MASTERED':
        return 'mastered'
    if status == 'DEMONSTRATED':
        return 'proficient' if evidence_type in _EVIDENCE_FOR_PROFICIENT else 'practising'
    if status == 'DEVELOPING':
        return 'developing' if evidence_type in _EVIDENCE_FOR_PROFICIENT else 'practising'
    return 'introduced'


def concept_mastery(user_id, domain=None):
    """Return concept-level mastery for every skill node the learner has evidence for.

    Each entry: skill_id, title, category, domain, mastery (state),
    evidence_type, verification_status, points (ordering weight).
    """
    rows = UserSkillProgress.query.filter_by(user_id=user_id).all()
    progress_by_skill = {row.skill_id: row for row in rows}
    nodes = {
        node.id: node
        for node in SkillNode.query.filter(
            SkillNode.id.in_(list(progress_by_skill) or ['__none__'])
        ).all()
    } if progress_by_skill else {}

    verification_events = (
        SkillVerification.query
        .filter_by(user_id=user_id)
        .order_by(SkillVerification.created_at.asc(), SkillVerification.id.asc())
        .all()
    )
    events_by_skill = {}
    for event in verification_events:
        events_by_skill.setdefault(event.skill_id, []).append(event)

    items = []
    for skill_id, progress in progress_by_skill.items():
        node = nodes.get(skill_id)
        category = node.category if node else ''
        item_domain = _skill_domain(skill_id, category)
        if domain and item_domain != domain:
            continue
        events = events_by_skill.get(skill_id, [])
        stage = _verification_stage(events)
        items.append({
            'skill_id': skill_id,
            'title': node.title if node else skill_id,
            'category': category,
            'domain': item_domain,
            'mastery': _state_for(progress, events),
            'evidence_type': progress.evidence_type,
            'evidence_id': progress.evidence_id,
            'status': progress.status,
            'verification_status': stage,
        })
    order = {name: index for index, name in enumerate(MASTERY_STATES)}
    items.sort(key=lambda item: (order[item['mastery']], item['domain'], item['skill_id']))
    return items


def domain_summary(user_id):
    items = concept_mastery(user_id)
    summary = {}
    for item in items:
        bucket = summary.setdefault(item['domain'], {
            'total': 0, 'mastered': 0, 'proficient': 0, 'developing': 0,
            'practising': 0, 'introduced': 0, 'needs_review': 0, 'not_introduced': 0,
        })
        bucket['total'] += 1
        bucket[item['mastery']] += 1
    return summary


def weakest_concepts(user_id, limit=5):
    items = concept_mastery(user_id)
    weak = [i for i in items if i['mastery'] in (
        'needs_review', 'practising', 'developing', 'introduced',
    )]
    return weak[:limit]


def strongest_concepts(user_id, limit=5):
    items = concept_mastery(user_id)
    return [i for i in reversed(items) if i['mastery'] in ('proficient', 'mastered')][:limit]
