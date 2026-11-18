"""Service-layer facade over the canonical curriculum registry.

Application code should import from ``app.services.curriculum`` rather than
reading manifests directly. This keeps a single seam for caching, telemetry
and future curriculum-version handling.
"""

from app.curriculum_registry import (
    CURRICULUM_NAMESPACES,  # re-exported for callers that branch on namespaces
    CurriculumError,
    CurriculumRegistry,
    DOMAIN_AI,
    DOMAIN_IDS,
    DOMAIN_ML,
    DOMAIN_SHARED,
    registry,
)

__all__ = [
    'CurriculumError', 'CurriculumRegistry', 'registry',
    'DOMAIN_SHARED', 'DOMAIN_AI', 'DOMAIN_ML', 'DOMAIN_IDS',
    'CURRICULUM_NAMESPACES',
    'get_domain', 'lesson', 'module', 'find_lesson', 'versions', 'summary',
]


def get_domain(domain_id):
    return registry.get_domain(domain_id)


def module(domain_id, module_id):
    return registry.module(domain_id, module_id)


def lesson(domain_id, lesson_id):
    return registry.lesson(domain_id, lesson_id)


def find_lesson(lesson_id):
    return registry.find_lesson(lesson_id)


def versions():
    return {domain_id: registry.version(domain_id) for domain_id in DOMAIN_IDS}


def summary():
    return registry.summary()
