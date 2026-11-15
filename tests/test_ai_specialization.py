"""Application-level checks for the independent AI Engineering workbench.

AI Engineering project records, prompt versions, retrieval configurations,
agent executions, and evaluation records are learner-scoped and pathway
scoped: AI evidence never credits Machine Learning and vice versa.
"""

import os
import tempfile
import unittest

from app import create_app, db
from app.ai_pathway import PATHWAY_ID, ai_engineering_pathway
from app.models import (
    AISpecializationProject, AIPromptVersion, AIRetrievalConfiguration,
    AIAgentExecutionRecord, AIEvaluationRecord, User,
)


class AISpecializationFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.register()
        self.pathway = ai_engineering_pathway()
        self.module_id = self.pathway['modules'][0]['id']

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

    def register(self):
        response = self.client.post('/register', data={
            'username': 'ailearner',
            'email': 'ailearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def test_pathway_and_modules_load(self):
        self.assertEqual(PATHWAY_ID, 'ai-engineering')
        ids = [m['id'] for m in self.pathway['modules']]
        self.assertEqual(ids, ['ai.03', 'ai.04', 'ai.05', 'ai.06', 'ai.07', 'ai.08', 'ai.09', 'ai.10', 'ai.11'])

    def test_dashboard_loads(self):
        response = self.client.get('/specializations/ai-engineering')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('AI Engineering', html)
        self.assertIn(self.module_id, html)

    def test_project_page_loads(self):
        response = self.client.get(f'/specializations/ai-engineering/projects/{self.module_id}')
        self.assertEqual(response.status_code, 200)

    def test_unknown_module_404s(self):
        response = self.client.get('/specializations/ai-engineering/projects/ai.99')
        self.assertEqual(response.status_code, 404)

    def test_submit_project_validation_and_save(self):
        response = self.client.post(
            f'/specializations/ai-engineering/projects/{self.module_id}/submit',
            json={'reflection': 'too short'},
        )
        self.assertEqual(response.status_code, 400)

        payload = {
            'reflection': 'I built a RAG pipeline with chunking and retrieval, then evaluated it against a held-out set.',
            'architecture_decisions': 'Used cosine similarity with a small embedding model to balance latency and quality.',
        }
        response = self.client.post(
            f'/specializations/ai-engineering/projects/{self.module_id}/submit',
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['draft_saved'])

        with self.app.app_context():
            record = AISpecializationProject.query.filter_by(
                user_id=1, pathway_id=PATHWAY_ID, module_id=self.module_id,
            ).first()
        self.assertIsNotNone(record)
        self.assertIn('RAG pipeline', record.submission)
        self.assertIn('cosine similarity', record.submission)

    def test_artefacts_are_learner_scoped(self):
        # Create a prompt version as the registered learner.
        create = self.client.post(
            '/api/ai-engineering/prompt-versions',
            json={'module_id': self.module_id, 'prompt_content': 'You are a helpful coding assistant.'},
        )
        self.assertEqual(create.status_code, 200, create.get_data(as_text=True))
        version = create.get_json()['id']

        listed = self.client.get('/api/ai-engineering/prompt-versions')
        self.assertEqual(listed.status_code, 200)
        versions = listed.get_json()
        self.assertTrue(any(v['id'] == version for v in versions))

        # A second learner must not see the first learner's artefacts.
        # A fresh client so the first learner's session cookie does not leak.
        other_client = self.app.test_client()
        other_client.post('/register', data={
            'username': 'otherlearner',
            'email': 'other@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        other_client.post('/onboarding', data={'action': 'skip'})
        other = other_client.get('/api/ai-engineering/prompt-versions')
        self.assertEqual(other.status_code, 200)
        self.assertFalse(any(v['id'] == version for v in other.get_json()))

    def test_retrieval_config_and_agent_execution_and_evaluation(self):
        self.client.post(
            '/api/ai-engineering/retrieval-configs',
            json={
                'module_id': self.module_id,
                'chunking_configuration': '{"strategy": "recursive", "size": 500}',
                'embedding_configuration': '{"model": "small-embed"}',
                'retrieval_parameters': '{"top_k": 5}',
            },
        )
        listed = self.client.get('/api/ai-engineering/retrieval-configs')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()), 1)

        self.client.post(
            '/api/ai-engineering/agent-executions',
            json={
                'module_id': self.module_id,
                'execution_id': 'exec-1',
                'status': 'completed',
                'tool_calls': '["retrieve", "rank"]',
                'duration': 1200,
            },
        )
        listed = self.client.get('/api/ai-engineering/agent-executions')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()), 1)

        self.client.post(
            '/api/ai-engineering/evaluations',
            json={
                'module_id': self.module_id,
                'evaluation_dataset': 'eval-set-a',
                'evaluation_results': '{"pass_rate": 0.9}',
                'metric_summary': '{"avg_bleu": 0.42}',
            },
        )
        listed = self.client.get('/api/ai-engineering/evaluations')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()), 1)

    def test_tables_are_queryable(self):
        with self.app.app_context():
            self.assertEqual(AISpecializationProject.query.count(), 0)
            self.assertEqual(AIPromptVersion.query.count(), 0)
            self.assertEqual(AIRetrievalConfiguration.query.count(), 0)
            self.assertEqual(AIAgentExecutionRecord.query.count(), 0)
            self.assertEqual(AIEvaluationRecord.query.count(), 0)
            self.assertEqual(User.query.count(), 1)
