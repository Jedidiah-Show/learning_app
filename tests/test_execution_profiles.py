"""M3 execution profile registry tests."""

import unittest

from app.execution.profiles import (
    ProfileDisabledError,
    UnknownProfileError,
    get_profile,
    list_profiles,
    profile_for_problem,
    profile_for_workload,
)


class ExecutionProfileTests(unittest.TestCase):
    def test_all_documented_profiles_are_registered(self):
        self.assertEqual(
            [profile.name for profile in list_profiles()],
            [
                'browser_python',
                'container_data_science',
                'container_ml',
                'container_python',
                'gpu_training',
            ],
        )

    def test_every_profile_declares_required_controls(self):
        for profile in list_profiles():
            self.assertTrue(profile.runtime)
            self.assertTrue(profile.libraries)
            self.assertGreaterEqual(profile.timeout_sec, 0.1)
            self.assertTrue(profile.network_policy)
            self.assertGreater(profile.max_concurrency, 0)
            self.assertTrue(profile.workloads)

    def test_server_selects_container_profile_for_arena_workload(self):
        self.assertEqual(
            profile_for_workload('arena_submit').name, 'container_python'
        )
        self.assertEqual(
            profile_for_workload('formative_run').runtime, 'pyodide'
        )

    def test_advanced_profiles_are_defined_but_disabled(self):
        with self.assertRaises(ProfileDisabledError):
            profile_for_workload('gpu_training')
        with self.assertRaises(ProfileDisabledError):
            profile_for_workload('ml_training')
        self.assertFalse(get_profile('gpu_training').enabled)

    def test_unknown_workload_and_profile_are_rejected(self):
        with self.assertRaises(UnknownProfileError):
            profile_for_workload('unrestricted')
        with self.assertRaises(UnknownProfileError):
            get_profile('unrestricted')

    def test_problem_metadata_is_server_side_only(self):
        self.assertEqual(
            profile_for_problem({'track': 'machine-learning'}).name,
            'container_data_science',
        )
        self.assertEqual(
            profile_for_problem({
                'track': 'ai-engineering',
                'execution_profile': 'container_data_science',
            }).name,
            'container_data_science',
        )
        self.assertEqual(
            profile_for_problem({'track': 'algorithms'}).name,
            'container_python',
        )


if __name__ == '__main__':
    unittest.main()
