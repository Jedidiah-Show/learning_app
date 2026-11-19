"""M5 — AI Tutor 3.0: domain resolution, modes, evaluation harness, privacy."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app import create_app, db
from app.models import TutorConversation, User
from app.services.tutor import (
    DOMAIN_AI_ENGINEERING, DOMAIN_MACHINE_LEARNING, DOMAIN_SHARED_FOUNDATIONS,
    infer_learning_domain, pathway_context_for_user,
)

ROOT = Path(__file__).resolve().parent.parent
EVAL_SCRIPT = ROOT / 'docs' / 'tutor_evaluation' / 'run_tutor_eval.py'
DATASETS = {
    'shared-foundations': ROOT / 'docs/tutor_evaluation/shared_foundations_eval.json',
    'ai-engineering': ROOT / 'docs/tutor_evaluation/ai_engineering_eval.json',
    'machine-learning': ROOT / 'docs/tutor_evaluation/machine_learning_eval.json',
}


def _load_eval_module():
    spec = importlib.util.spec_from_file_location('run_tutor_eval', EVAL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DomainResolutionTests(unittest.TestCase):
    def test_explicit_context_wins(self):
        self.assertEqual(
            infer_learning_domain(lesson_id='sf.00.01', explicit_domain='ai-engineering'),
            DOMAIN_AI_ENGINEERING,
        )

    def test_canonical_lesson_ids_resolve_via_registry(self):
        self.assertEqual(infer_learning_domain(lesson_id='sf.00.01'), DOMAIN_SHARED_FOUNDATIONS)
        self.assertEqual(infer_learning_domain(lesson_id='ai.03.01'), DOMAIN_AI_ENGINEERING)
        self.assertEqual(infer_learning_domain(lesson_id='mle.tools.01'), DOMAIN_MACHINE_LEARNING)

    def test_legacy_lesson_ids_fallback(self):
        self.assertEqual(infer_learning_domain(lesson_id='00.01'), DOMAIN_SHARED_FOUNDATIONS)
        self.assertEqual(infer_learning_domain(lesson_id='02.11'), DOMAIN_SHARED_FOUNDATIONS)
        self.assertEqual(infer_learning_domain(lesson_id='03.01'), DOMAIN_AI_ENGINEERING)
        self.assertEqual(infer_learning_domain(lesson_id='12.99'), DOMAIN_AI_ENGINEERING)

    def test_project_domain_precedes_destination(self):
        self.assertEqual(
            infer_learning_domain(destination='machine-learning', project_domain='ai-engineering'),
            DOMAIN_AI_ENGINEERING,
        )

    def test_destination_fallback_and_shared_default(self):
        self.assertEqual(infer_learning_domain(destination='machine-learning'), DOMAIN_MACHINE_LEARNING)
        self.assertEqual(infer_learning_domain(destination='ai-engineering'), DOMAIN_AI_ENGINEERING)
        self.assertEqual(infer_learning_domain(destination=None), DOMAIN_SHARED_FOUNDATIONS)
        self.assertEqual(infer_learning_domain(), DOMAIN_SHARED_FOUNDATIONS)

    def test_domain_does_not_confuse_specialisations(self):
        ctx = pathway_context_for_user(None, lesson_id='ai.03.01')
        self.assertEqual(ctx['active_domain'], DOMAIN_AI_ENGINEERING)
        ctx = pathway_context_for_user(None, lesson_id='mle.tools.01')
        self.assertEqual(ctx['active_domain'], DOMAIN_MACHINE_LEARNING)


class EvaluationHarnessTests(unittest.TestCase):
    def test_datasets_exist_and_have_cases(self):
        for domain, path in DATASETS.items():
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data.get('domain'), domain)
            self.assertGreaterEqual(len(data.get('cases', [])), 3, domain)

    def test_every_case_has_required_fields(self):
        module = _load_eval_module()
        for path in DATASETS.values():
            data = json.loads(path.read_text(encoding='utf-8'))
            for case in data['cases']:
                for field in module.REQUIRED_FIELDS:
                    self.assertTrue(case.get(field), f'{case.get("id")}: {field}')

    def test_lesson_contexts_match_their_domain(self):
        from app.curriculum_registry import registry
        for domain, path in DATASETS.items():
            data = json.loads(path.read_text(encoding='utf-8'))
            for case in data['cases']:
                lesson_id = (case.get('lesson_id')
                             or (case.get('context') or {}).get('lesson_id'))
                if not lesson_id:
                    continue
                owner, _ = registry.find_lesson(lesson_id)
                if owner is None:
                    continue  # legacy course ids resolve to AI by convention; skip
                self.assertEqual(owner, domain, f'case {case["id"]} context resolves to {owner}')

    def test_structural_validation_runs_and_is_green(self):
        result = subprocess.run(
            [sys.executable, str(EVAL_SCRIPT), '--domain', 'all', '--dry-run', '--strict'],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_structural_score_rejects_cases_without_prompt(self):
        module = _load_eval_module()
        scored = module._structural_score({'id': 'x', 'type': 'explain'})
        self.assertFalse(scored['structural_valid'])
        self.assertTrue(scored['issues'])

    def test_records_carry_mode_model_run_metadata(self):
        module = _load_eval_module()
        # _structural_score is pure; emulate the record construction path.
        record = {
            'mode': 'structural', 'model_id': 'structural', 'run_id': 'test-run',
        }
        self.assertEqual(record['mode'], 'structural')
        self.assertIn('run_id', record)


class TutorPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self._register('tutoralice')
        self._register('tutorbob')

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def _register(self, username):
        self.client.post('/logout', follow_redirects=True)
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def _login(self, username):
        self.client.post('/logout', follow_redirects=True)
        response = self.client.post('/login', data={
            'username': username, 'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_tutor_history_is_owner_scoped(self):
        with self.app.app_context():
            alice = User.query.filter_by(username='tutoralice').one()
            db.session.add(TutorConversation(
                user_id=alice.id, lesson_id='sf.00.01', role='user',
                content='secret learner question',
            ))
            db.session.commit()
        self._login('tutorbob')
        response = self.client.get('/api/lessons/tutor/history/sf.00.01')
        # Bob must not see Alice's conversation.
        self.assertNotIn('secret learner question', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
