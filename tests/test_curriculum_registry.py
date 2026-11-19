"""Curriculum contract tests (M1.1 / M1.5).

Verifies the canonical registry resolves all three domains, enforces
uniqueness and domain boundaries, and that the legacy mapping file is
internally consistent.
"""

import json
import os
import unittest

from app.curriculum_registry import (
    CURRICULUM_NAMESPACES, DOMAIN_AI, DOMAIN_IDS, DOMAIN_ML, DOMAIN_SHARED,
    CurriculumError, registry,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_MAPPING_PATH = os.path.join(REPO_ROOT, 'app', 'data', 'curriculum_legacy_mapping.json')


class RegistrySummaryTests(unittest.TestCase):
    def test_all_three_domains_resolve(self):
        self.assertEqual(set(registry.domain_ids()),
                         {DOMAIN_SHARED, DOMAIN_AI, DOMAIN_ML})
        for domain_id in DOMAIN_IDS:
            domain = registry.get_domain(domain_id)
            self.assertEqual(domain.id, domain_id)
            self.assertRegex(domain.version, r'^\d+\.\d+\.\d+$')

    def test_domain_module_and_lesson_counts(self):
        summary = registry.summary()
        self.assertEqual(summary[DOMAIN_SHARED]['module_count'], 6)
        self.assertEqual(summary[DOMAIN_SHARED]['lesson_count'], 21)
        self.assertEqual(summary[DOMAIN_AI]['module_count'], 9)
        self.assertEqual(summary[DOMAIN_AI]['lesson_count'], 28)
        self.assertEqual(summary[DOMAIN_ML]['module_count'], 12)
        self.assertEqual(summary[DOMAIN_ML]['lesson_count'], 59)

    def test_unique_ids_across_domains(self):
        seen = {}
        for domain_id in DOMAIN_IDS:
            domain = registry.get_domain(domain_id)
            for module in domain.modules:
                self.assertNotIn(module['id'], seen)
                seen[module['id']] = domain_id
                for lesson in module['lessons']:
                    self.assertNotIn(lesson['id'], seen)
                    seen[lesson['id']] = domain_id

    def test_lessons_carry_domain_namespace(self):
        for domain_id in DOMAIN_IDS:
            prefix = CURRICULUM_NAMESPACES[domain_id]
            for lesson in registry.get_domain(domain_id).lessons():
                self.assertTrue(lesson['id'].startswith(prefix),
                                f'{lesson["id"]} lacks namespace {prefix}')
                self.assertTrue(lesson.get('title'))

    def test_find_lesson_roundtrip_for_every_published_lesson(self):
        for domain_id in DOMAIN_IDS:
            for lesson in registry.get_domain(domain_id).lessons():
                found_domain, found_lesson = registry.find_lesson(lesson['id'])
                self.assertEqual(found_domain, domain_id)
                self.assertEqual(found_lesson['id'], lesson['id'])

    def test_find_lesson_unknown_returns_none_pair(self):
        self.assertEqual(registry.find_lesson('no.such.lesson'), (None, None))


class PrerequisiteTests(unittest.TestCase):
    def test_prerequisites_resolve_within_allowed_domains(self):
        for domain_id in DOMAIN_IDS:
            for module in registry.get_domain(domain_id).modules:
                # Must not raise; edges were validated at load time.
                registry.resolve_prerequisites(domain_id, module['id'])

    def test_ai_prerequisites_reference_only_foundations_and_ai(self):
        for module in registry.get_domain(DOMAIN_AI).modules:
            for prereq in module.get('prerequisites') or []:
                self.assertTrue(
                    prereq.startswith('sf.') or prereq.startswith('ai.'),
                    f'AI Engineering prerequisite {prereq} crosses domains',
                )

    def test_ml_prerequisites_reference_only_foundations_and_ml(self):
        for module in registry.get_domain(DOMAIN_ML).modules:
            for prereq in module.get('prerequisites') or []:
                self.assertTrue(
                    prereq.startswith('sf.') or prereq.startswith('mle.'),
                    f'Machine Learning prerequisite {prereq} crosses domains',
                )

    def test_foundations_do_not_depend_on_specialisations(self):
        for module in registry.get_domain(DOMAIN_SHARED).modules:
            for prereq in module.get('prerequisites') or []:
                self.assertTrue(prereq.startswith('sf.'),
                                f'Foundations prerequisite {prereq} escapes the domain')

    def test_shared_foundations_modules_form_a_chain(self):
        ordered = registry.resolve_prerequisites(DOMAIN_SHARED, 'sf.05')
        self.assertEqual(ordered, ['sf.00', 'sf.01', 'sf.02', 'sf.03', 'sf.04'])

    def test_cross_specialisation_edge_is_rejected(self):
        from app import curriculum_registry
        manifest = registry.get_domain(DOMAIN_AI).manifest
        mutated_module = dict(manifest['modules'][0])
        mutated_module['prerequisites'] = ['mle.classical-ml']
        with self.assertRaises(CurriculumError):
            curriculum_registry._validate_manifest(
                DOMAIN_AI,
                {**manifest, 'modules': [mutated_module] + manifest['modules'][1:]},
            )

    def test_unknown_domain_rejected(self):
        with self.assertRaises(CurriculumError):
            registry.get_domain('data-science')

    def test_learning_objectives_and_competencies_present(self):
        for domain_id in DOMAIN_IDS:
            self.assertTrue(registry.learning_objectives(domain_id))
            self.assertTrue(registry.competencies(domain_id))


class LegacyMappingTests(unittest.TestCase):
    def setUp(self):
        with open(LEGACY_MAPPING_PATH, encoding='utf-8') as handle:
            self.mapping = json.load(handle)

    def test_every_legacy_lesson_is_listed(self):
        self.assertEqual(self.mapping['lesson_count'], len(self.mapping['lesson_mappings']))

    def test_module_mappings_resolve_to_canonical_domains(self):
        for legacy_module, rule in self.mapping['module_mappings'].items():
            if rule['domain'] is None:
                self.assertEqual(rule['confidence'], 'UNRESOLVED')
                continue
            self.assertIn(rule['domain'], DOMAIN_IDS)
            module = registry.module(rule['domain'], rule['module'])
            self.assertIsNotNone(module, f'{legacy_module} -> {rule["module"]} unresolved')

    def test_lesson_mappings_point_at_mapped_modules(self):
        for entry in self.mapping['lesson_mappings']:
            rule = self.mapping['module_mappings'][entry['legacy_module']]
            self.assertEqual(entry['domain'], rule['domain'])
            self.assertEqual(entry['canonical_module'], rule['module'])

    def test_unresolved_entries_are_explicit(self):
        unresolved = [e for e in self.mapping['lesson_mappings'] if e['domain'] is None]
        # Legacy module 12 (Final Capstone) is the only unresolved set.
        self.assertTrue(all(e['legacy_module'] == '12' for e in unresolved))
        self.assertTrue(any(e['legacy_module'] == '12' for e in unresolved))


if __name__ == '__main__':
    unittest.main()
