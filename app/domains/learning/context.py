"""Trusted learning-context resolution (M1.4 / M1.5).

The pathway that scopes a tutor session is a property of the *lesson being
studied*, resolved from server-side curriculum records. A learner's dashboard
focus (``CoursePlan.pathway_destination``) is recorded separately for UI and
progress display, but it must never decide which syllabus the tutor uses.

This module is the single source of truth for that distinction. It deliberately
imports no route handlers and no AI provider code.
"""

from dataclasses import dataclass, field
from functools import lru_cache
import json
import os
from typing import Any, Dict, List, Optional

DOMAIN_SHARED_FOUNDATIONS = 'shared-foundations'
DOMAIN_AI_ENGINEERING = 'ai-engineering'
DOMAIN_MACHINE_LEARNING = 'machine-learning'
PATHWAY_IDS = (
    DOMAIN_SHARED_FOUNDATIONS,
    DOMAIN_AI_ENGINEERING,
    DOMAIN_MACHINE_LEARNING,
)

_ALIASES = {
    'ml': DOMAIN_MACHINE_LEARNING,
    'machine_learning': DOMAIN_MACHINE_LEARNING,
    'machine-learning-engineering': DOMAIN_MACHINE_LEARNING,
    'ai': DOMAIN_AI_ENGINEERING,
    'ai_engineering': DOMAIN_AI_ENGINEERING,
    'foundations': DOMAIN_SHARED_FOUNDATIONS,
    'shared': DOMAIN_SHARED_FOUNDATIONS,
    'shared-foundations': DOMAIN_SHARED_FOUNDATIONS,
}


class ContextResolutionError(ValueError):
    """Raised when lesson and pathway context cannot be resolved consistently."""


@dataclass
class LearningContext:
    """The resolved context for one learning activity."""

    learner_id: Optional[int]
    pathway_id: str
    domain: str
    source: str
    dashboard_focus: Optional[str] = None
    lesson_id: Optional[str] = None
    lesson_kind: Optional[str] = None
    lesson: Dict[str, Any] = field(default_factory=dict)
    module: Dict[str, Any] = field(default_factory=dict)
    objectives: List[str] = field(default_factory=list)
    competencies: List[str] = field(default_factory=list)
    syllabus_modules: List[Dict[str, Any]] = field(default_factory=list)
    syllabus_module_titles: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        """Return the compatibility shape consumed by the tutor service."""
        context = {
            # Both values are lesson-derived. Keeping the old key names avoids
            # breaking callers while fixing the value they carry.
            'active_domain': self.domain,
            'active_pathway': self.pathway_id,
            'pathway_source': self.source,
            'dashboard_focus': self.dashboard_focus,
            'syllabus_modules': list(self.syllabus_module_titles),
            'objectives': list(self.objectives),
            'competencies': list(self.competencies),
        }
        if self.module:
            context['current_module'] = dict(self.module)
        if self.lesson_id:
            context['current_lesson'] = {
                'id': self.lesson_id,
                'title': self.lesson.get('title'),
            }
        return context


def normalise_pathway(value: Optional[str]) -> Optional[str]:
    """Normalise legacy/UI pathway tokens to a canonical pathway id."""
    if not isinstance(value, str) or not value.strip():
        return None
    key = value.strip().lower()
    key = _ALIASES.get(key, key)
    if key in ('', 'undecided', 'none'):
        return None
    return key if key in PATHWAY_IDS else None


def _text_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


@lru_cache(maxsize=1)
def _legacy_module_domains() -> Dict[str, str]:
    """Authoritative legacy-module → domain map from the bundled manifest."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        'app', 'data', 'curriculum_legacy_mapping.json',
    )
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return {
            str(number): normalise_pathway(entry.get('domain'))
            for number, entry in (data.get('module_mappings') or {}).items()
            if normalise_pathway(entry.get('domain'))
        }
    except (OSError, ValueError):
        return {}


def _domain_from_legacy_module(module_id: str) -> Optional[str]:
    number = str(module_id).split('.', 1)[0]
    mapped = _legacy_module_domains().get(number)
    if mapped:
        return mapped
    # Deterministic fallback for legacy numbered lessons not covered by the
    # manifest: 00–02 are foundations, 03+ are AI Engineering specialisation.
    if number.isdigit():
        return (
            DOMAIN_SHARED_FOUNDATIONS if int(number) <= 2
            else DOMAIN_AI_ENGINEERING
        )
    return None


def _resolve_lesson(lesson_id: str):
    """Return ``(domain, lesson, source)`` from trusted curriculum records."""
    from app.curriculum_registry import registry

    domain, lesson = registry.find_lesson(str(lesson_id))
    if domain in PATHWAY_IDS and lesson is not None:
        return domain, lesson, 'curriculum-registry'

    from app.ml_pathway import get_machine_learning_lesson
    lesson = get_machine_learning_lesson(str(lesson_id))
    if lesson:
        return DOMAIN_MACHINE_LEARNING, lesson, 'ml-pathway'

    from app.curriculum import get_lesson
    lesson = get_lesson(str(lesson_id))
    if lesson:
        domain = _domain_from_legacy_module(
            lesson.get('module_id') or str(lesson_id)
        )
        if domain:
            return domain, lesson, 'bundled-curriculum'
    return None, None, None


def _module_for(domain: str, lesson: Dict[str, Any]) -> Dict[str, Any]:
    module = lesson.get('_module') or {}
    if not module and lesson.get('module_id'):
        module = {
            'id': lesson.get('module_id'),
            'title': lesson.get('module_title'),
        }
    if not module:
        try:
            from app.curriculum_registry import registry
            module_id = registry.module_of_lesson(domain, lesson.get('id'))
            module = registry.module(domain, module_id) or {}
        except Exception:
            module = {}
    return {
        key: module[key]
        for key in ('id', 'number', 'title', 'description')
        if module.get(key) is not None
    }


def _syllabus(pathway_id: str, user_id: Optional[int]):
    """Modules that legitimately scope the resolved activity's pathway."""
    from app.pathway_scope import course_modules

    modules = course_modules(pathway_id, user_id)
    titles = [module.get('title', '') for module in modules if module.get('title')]
    return list(modules), titles


def resolve_learning_context(
    user_id: Optional[int] = None,
    *,
    lesson_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    project_domain: Optional[str] = None,
    explicit_domain: Optional[str] = None,
    dashboard_focus: Optional[str] = None,
) -> LearningContext:
    """Resolve one learning activity into an authoritative ``LearningContext``.

    Precedence: a resolvable lesson always wins; then a practice problem's
    server-side track; then an explicit project domain; then a normalised
    explicit domain; then the dashboard focus; finally Shared Foundations.
    Client-supplied context may never override a lesson-owned pathway: an
    inconsistent explicit value is rejected instead of silently mis-scoping the
    tutor.
    """
    focus = normalise_pathway(dashboard_focus)
    explicit = normalise_pathway(explicit_domain)
    project = normalise_pathway(project_domain)

    pathway_id = None
    lesson = {}
    lesson_kind = None
    source = 'shared-default'

    if lesson_id:
        pathway_id, lesson, lesson_kind = _resolve_lesson(str(lesson_id))
        if pathway_id is None:
            raise ContextResolutionError(
                f'Lesson {lesson_id!r} does not belong to a known curriculum pathway'
            )
        if explicit is not None and explicit != pathway_id:
            raise ContextResolutionError(
                f'Context {explicit!r} conflicts with lesson pathway {pathway_id!r}'
            )
        source = f'lesson:{lesson_kind}'
    elif problem_id:
        try:
            from app.practice_arena import get_arena_problem
            problem = get_arena_problem(str(problem_id)) or {}
        except Exception:
            problem = {}
        track = normalise_pathway(problem.get('track'))
        if track:
            pathway_id, source = track, 'practice-problem'
        elif explicit:
            pathway_id, source = explicit, 'explicit-context'
        elif project:
            pathway_id, source = project, 'project-context'
        elif focus:
            pathway_id, source = focus, 'dashboard-focus'
        else:
            pathway_id, source = DOMAIN_SHARED_FOUNDATIONS, 'shared-default'
    elif project:
        pathway_id, source = project, 'project-context'
    elif explicit:
        pathway_id, source = explicit, 'explicit-context'
    elif focus:
        pathway_id, source = focus, 'dashboard-focus'
    else:
        pathway_id, source = DOMAIN_SHARED_FOUNDATIONS, 'shared-default'

    modules, titles = _syllabus(pathway_id, user_id)
    return LearningContext(
        learner_id=user_id,
        pathway_id=pathway_id,
        domain=pathway_id,
        source=source,
        dashboard_focus=focus,
        lesson_id=str(lesson_id) if lesson_id else None,
        lesson_kind=lesson_kind,
        lesson=dict(lesson or {}),
        module=_module_for(pathway_id, lesson) if lesson else {},
        objectives=_text_list(
            (lesson or {}).get('outcomes')
            or (lesson or {}).get('goal')
            or (lesson or {}).get('objectives')
        ),
        competencies=_text_list(
            (lesson or {}).get('core_concepts')
            or (lesson or {}).get('key_terms')
            or (lesson or {}).get('skills')
        ),
        syllabus_modules=modules,
        syllabus_module_titles=titles,
    )
