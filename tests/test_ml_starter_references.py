"""Stage A check: starter-kit contracts pass against reference solutions.

The shipped kits deliberately raise NotImplementedError so learner downloads
stay stubbed. These tests load the reference implementations from
``tests/ml_reference`` and run each kit's own test file against them, plus
the server-owned report contract used by project submission validation.
"""

import os
import sys
import unittest
import pytest
from importlib import import_module, reload
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KITS = ROOT / 'starter_kits' / 'machine_learning'
REFERENCES = Path(__file__).resolve().parent / 'ml_reference'

sys.path.insert(0, str(REFERENCES))

pytest.importorskip('pandas', reason=(
    'install requirements-dev.txt to run the ML starter reference checks'
))

from app.routes.ml_specialization import _report_matches  # noqa: E402


def _run_kit_tests(module_dir):
    kit = KITS / module_dir
    test_path = next((kit / 'tests').glob('test_*.py'))
    namespace = {'__name__': f'reference_{module_dir}'}
    previous_cwd = os.getcwd()
    os.chdir(kit)
    try:
        code = compile(test_path.read_text(), str(test_path), 'exec')
        exec(code, namespace)
        failed = []
        for name, fn in namespace.items():
            if name.startswith('test_') and callable(fn):
                try:
                    fn()
                except Exception as error:  # noqa: BLE001
                    failed.append(f'{name}: {error}')
    finally:
        os.chdir(previous_cwd)
    return failed


class StarterContractReferenceTests(unittest.TestCase):
    def test_module_1_audit_reference_meets_kit_and_server_contracts(self):
        audit = reload(import_module('audit'))
        self.assertEqual(_run_kit_tests('module_1'), [])
        self.assertTrue(_report_matches(
            'mle.data-problem-formulation', audit.build_report()
        ))

    def test_module_2_model_reference_meets_kit_and_server_contracts(self):
        model = reload(import_module('model'))
        self.assertEqual(_run_kit_tests('module_2'), [])
        self.assertTrue(_report_matches('mle.classical-ml', model.evaluate()))

    def test_module_3_run_reference_meets_kit_and_server_contracts(self):
        run = reload(import_module('run'))
        self.assertEqual(_run_kit_tests('module_3'), [])
        self.assertTrue(_report_matches(
            'mle.reproducible-training', run.run_training()
        ))

    def test_module_4_service_reference_meets_kit_and_server_contracts(self):
        import joblib

        project_report = reload(import_module('project_report'))
        train_model = reload(import_module('train_model'))
        self.assertEqual(_run_kit_tests('module_4'), [])
        self.assertTrue(_report_matches(
            'mle.production-ml',
            project_report.build_report(
                joblib.load(train_model.train_and_save())
            ),
        ))
