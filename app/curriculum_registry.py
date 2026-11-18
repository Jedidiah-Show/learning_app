"""Canonical curriculum registry for RUACH's three domains.

This is the single resolution point for curriculum structure:

- ``shared-foundations`` — the only curriculum shared across specialisations
- ``ai-engineering``     — AI Engineering specialisation
- ``machine-learning``   — Machine Learning specialisation

The registry loads the three bundled manifests, validates them (unique IDs,
namespace rules, prerequisite resolution, domain ownership, cross-
specialisation rejection), and serves module/lesson/competency/objective
lookups. Application services must resolve curriculum data through this
registry instead of ad-hoc manifest reads.

Domain dependency rules (R2, mandatory):

- Shared Foundations → AI Engineering   (allowed)
- Shared Foundations → Machine Learning (allowed)
- AI Engineering ↔ Machine Learning     (forbidden)
- Machine Learning → AI Engineering     (forbidden)
"""

import json
import re
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DOMAIN_SHARED = 'shared-foundations'
DOMAIN_AI = 'ai-engineering'
DOMAIN_ML = 'machine-learning'
DOMAIN_IDS = (DOMAIN_SHARED, DOMAIN_AI, DOMAIN_ML)

DOMAIN_MANIFESTS = {
    DOMAIN_SHARED: REPO_ROOT / 'shared_foundations_curriculum.json',
    DOMAIN_AI: REPO_ROOT / 'ai_engineering_curriculum.json',
    DOMAIN_ML: REPO_ROOT / 'machine_learning_curriculum.json',
}

# Namespace prefix every module/lesson ID in a domain must carry.
DOMAIN_ID_PREFIX = {
    DOMAIN_SHARED: 'sf.',
    DOMAIN_AI: 'ai.',
    DOMAIN_ML: 'mle.',
}

# Re-exported so callers can branch on domain namespaces without redefining them.
CURRICULUM_NAMESPACES = DOMAIN_ID_PREFIX

# Which foreign namespaces a domain may reference in prerequisites.
# Shared Foundations may not depend on any specialisation; specialisations
# may depend on Shared Foundations and on their own modules only.
ALLOWED_PREREQUISITE_NAMESPACES = {
    DOMAIN_SHARED: ('sf.',),
    DOMAIN_AI: ('sf.', 'ai.'),
    DOMAIN_ML: ('sf.', 'mle.'),
}


class CurriculumError(ValueError):
    """Raised when a manifest fails validation."""


def _load_manifest(domain):
    path = DOMAIN_MANIFESTS.get(domain)
    if path is None:
        raise CurriculumError(f'Unknown domain: {domain}')
    if not path.exists():
        raise CurriculumError(f'Manifest for {domain} not found at {path}')
    with path.open(encoding='utf-8') as source:
        manifest = json.load(source)
    manifest['_manifest_path'] = str(path)
    return manifest


def _validate_manifest(domain, manifest):
    expected_id = domain
    if manifest.get('id') != expected_id:
        raise CurriculumError(
            f'{domain}: manifest id {manifest.get("id")!r} does not match domain'
        )
    prefix = DOMAIN_ID_PREFIX[domain]
    version = manifest.get('version')
    if not isinstance(version, str) or not re.match(r'^\d+\.\d+\.\d+$', version):
        raise CurriculumError(f'{domain}: version must be semver, got {version!r}')

    modules = manifest.get('modules')
    if not isinstance(modules, list) or not modules:
        raise CurriculumError(f'{domain}: manifest must define modules')

    module_ids = set()
    lesson_ids = set()
    module_numbers = set()
    for module in modules:
        module_id = module.get('id', '')
        if not isinstance(module_id, str) or not module_id.startswith(prefix):
            raise CurriculumError(
                f'{domain}: module id {module_id!r} must be namespaced {prefix!r}'
            )
        if module_id in module_ids:
            raise CurriculumError(f'{domain}: duplicate module id {module_id!r}')
        module_ids.add(module_id)

        number = module.get('number')
        if not isinstance(number, int) or isinstance(number, bool):
            raise CurriculumError(f'{domain}: {module_id} number must be an integer')
        if number in module_numbers:
            raise CurriculumError(f'{domain}: duplicate module number {number}')
        module_numbers.add(number)

        lessons = module.get('lessons')
        if not isinstance(lessons, list) or not lessons:
            raise CurriculumError(f'{domain}: {module_id} must define at least one lesson')
        for lesson in lessons:
            lesson_id = lesson.get('id', '')
            if not isinstance(lesson_id, str) or not lesson_id.startswith(prefix):
                raise CurriculumError(
                    f'{domain}: lesson id {lesson_id!r} must be namespaced {prefix!r}'
                )
            if lesson_id in lesson_ids:
                raise CurriculumError(f'{domain}: duplicate lesson id {lesson_id!r}')
            lesson_ids.add(lesson_id)
            if not lesson.get('title'):
                raise CurriculumError(f'{domain}: {lesson_id} is missing a title')

    # Prerequisite validation: referenced modules must exist somewhere and
    # must live in an allowed namespace for this domain. Cross-manifest
    # resolution happens in _cross_manifest_pass().
    allowed_prefixes = ALLOWED_PREREQUISITE_NAMESPACES[domain]
    for module in modules:
        for prereq in module.get('prerequisites') or []:
            if not isinstance(prereq, str):
                raise CurriculumError(
                    f'{domain}: {module["id"]} prerequisite {prereq!r} must be a string'
                )
            if not any(prereq.startswith(p) for p in allowed_prefixes):
                raise CurriculumError(
                    f'{domain}: {module["id"]} prerequisite {prereq!r} crosses a '
                    f'forbidden domain boundary (allowed: {allowed_prefixes or ("nothing",)})'
                )

    return manifest


def _cross_manifest_pass():
    """Validate prerequisites against the union of module IDs across domains."""
    id_owner = {}
    for domain in DOMAIN_IDS:
        manifest = _load_manifest(domain)
        for module in manifest['modules']:
            if module['id'] in id_owner:
                raise CurriculumError(
                    f'Module id {module["id"]!r} defined by both '
                    f'{id_owner[module["id"]]!r} and {domain!r}'
                )
            id_owner[module['id']] = domain
            for lesson in module['lessons']:
                if lesson['id'] in id_owner:
                    raise CurriculumError(
                        f'Lesson id {lesson["id"]!r} defined in two domains'
                    )
                id_owner[lesson['id']] = domain

    for domain in DOMAIN_IDS:
        manifest = _load_manifest(domain)
        for module in manifest['modules']:
            for prereq in module.get('prerequisites') or []:
                owner = id_owner.get(prereq)
                if owner is None:
                    raise CurriculumError(
                        f'{domain}: {module["id"]} prerequisite {prereq!r} '
                        f'does not resolve to any module'
                    )
                if owner != domain:
                    # The only legal cross-domain edge is foundations → specialisation.
                    if not (domain in (DOMAIN_AI, DOMAIN_ML) and owner == DOMAIN_SHARED):
                        raise CurriculumError(
                            f'{domain}: {module["id"]} -> {prereq!r} crosses a '
                            f'forbidden domain boundary ({owner})'
                        )


class Domain:
    """One loaded, validated domain manifest."""

    def __init__(self, domain_id, manifest):
        self.id = domain_id
        self.manifest = manifest
        self.version = manifest['version']
        self.name = manifest.get('name') or domain_id
        self.description = manifest.get('description') or ''
        self.learning_objectives = list(manifest.get('learning_objectives') or [])
        self.status = manifest.get('status') or 'ACTIVE'
        self.modules = list(manifest['modules'])
        self._modules_by_id = {m['id']: m for m in self.modules}
        self._lessons_by_id = {}
        self._module_of_lesson = {}
        for module in self.modules:
            for lesson in module['lessons']:
                self._lessons_by_id[lesson['id']] = lesson
                self._module_of_lesson[lesson['id']] = module['id']

    # --- lookups ---------------------------------------------------------
    def module(self, module_id):
        return self._modules_by_id.get(module_id)

    def lesson(self, lesson_id):
        return self._lessons_by_id.get(lesson_id)

    def module_of_lesson(self, lesson_id):
        return self._module_of_lesson.get(lesson_id)

    def lessons(self):
        return [lesson for m in self.modules for lesson in m['lessons']]

    def competencies(self):
        seen = []
        for module in self.modules:
            for comp in module.get('competencies') or []:
                if comp not in seen:
                    seen.append(comp)
        return seen

    def prerequisites(self, module_id):
        module = self._modules_by_id.get(module_id)
        if module is None:
            return None
        return list(module.get('prerequisites') or [])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'status': self.status,
            'domain': self.id,
            'learning_objectives': list(self.learning_objectives),
            'module_count': len(self.modules),
            'lesson_count': len(self.lessons()),
        }


@lru_cache(maxsize=1)
def _validated_domains():
    domains = {}
    for domain in DOMAIN_IDS:
        manifest = _load_manifest(domain)
        domains[domain] = Domain(domain, _validate_manifest(domain, manifest))
    _cross_manifest_pass()
    return domains


def invalidate_cache():
    _validated_domains.cache_clear()


class CurriculumRegistry:
    """Public API for resolving canonical curriculum data."""

    def domain_ids(self):
        return list(DOMAIN_IDS)

    def get_domain(self, domain_id):
        domains = _validated_domains()
        domain = domains.get(domain_id)
        if domain is None:
            raise CurriculumError(
                f'Unknown domain {domain_id!r}; expected one of {DOMAIN_IDS}'
            )
        return domain

    def validate_domain(self, domain_id):
        """Re-validate one domain (raises CurriculumError on failure)."""
        self.get_domain(domain_id)
        return True

    def validate_all(self):
        _validated_domains()
        return True

    def module(self, domain_id, module_id):
        return self.get_domain(domain_id).module(module_id)

    def lesson(self, domain_id, lesson_id):
        return self.get_domain(domain_id).lesson(lesson_id)

    def find_lesson(self, lesson_id):
        """Locate a lesson across domains; returns (domain, lesson) or (None, None)."""
        for domain_id, domain in _validated_domains().items():
            lesson = domain.lesson(lesson_id)
            if lesson is not None:
                return domain_id, lesson
        return None, None

    def module_of_lesson(self, domain_id, lesson_id):
        return self.get_domain(domain_id).module_of_lesson(lesson_id)

    def competencies(self, domain_id):
        return self.get_domain(domain_id).competencies()

    def prerequisites(self, domain_id, module_id):
        return self.get_domain(domain_id).prerequisites(module_id)

    def learning_objectives(self, domain_id):
        return list(self.get_domain(domain_id).learning_objectives)

    def version(self, domain_id):
        return self.get_domain(domain_id).version

    def resolve_prerequisites(self, domain_id, module_id, _seen=None):
        """Depth-first prerequisite resolution; returns ordered module IDs."""
        _seen = _seen if _seen is not None else set()
        prereqs = self.prerequisites(domain_id, module_id)
        if prereqs is None:
            raise CurriculumError(
                f'{domain_id}: unknown module {module_id!r}'
            )
        ordered = []
        for prereq in prereqs:
            if prereq in _seen:
                raise CurriculumError(
                    f'{domain_id}: prerequisite cycle involving {prereq!r}'
                )
            owner_domain = self._owner_domain(prereq)
            for resolved in self.resolve_prerequisites(owner_domain, prereq, _seen | {prereq}):
                if resolved not in ordered:
                    ordered.append(resolved)
            if prereq not in ordered:
                ordered.append(prereq)
        return ordered

    def _owner_domain(self, module_id):
        domains = _validated_domains()
        for domain_id, domain in domains.items():
            if domain.module(module_id) is not None:
                return domain_id
        raise CurriculumError(f'Prerequisite {module_id!r} does not resolve')

    def summary(self):
        return {
            domain_id: domain.to_dict()
            for domain_id, domain in _validated_domains().items()
        }


registry = CurriculumRegistry()
