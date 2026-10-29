"""Release audit checks for the bundled curriculum."""

import unittest

from scripts.audit_curriculum import audit


class CurriculumAuditTests(unittest.TestCase):
    def test_bundled_curriculum_passes_hard_release_checks(self):
        errors, modules, lessons, exercises, queue = audit(
            strict_reviews=False, run_exercises=False,
        )
        self.assertEqual(errors, [])
        self.assertEqual(modules, 13)
        self.assertEqual(lessons, 212)
        self.assertGreaterEqual(exercises, 61)
        # Review queue is reported but is not a hard failure unless strict mode.
        self.assertIsInstance(queue, list)
