"""Shared project lifecycle engine tests (M2.3)."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import User
from app.services.project_lifecycle import (
    LifecycleError, current_stage, history, record_transition,
)


class LifecycleServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            self.owner = User(username='owner', email='owner@example.test',
                              password_hash='x')
            self.reviewer = User(username='reviewer', email='reviewer@example.test',
                                 password_hash='x')
            self.reviewer.is_admin = True
            db.session.add_all([self.owner, self.reviewer])
            db.session.commit()
            self.owner_id = self.owner.id
            self.reviewer_id = self.reviewer.id

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

    def test_fresh_project_is_draft(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            self.assertEqual(current_stage(owner.id, 'ai-engineering', 'ai.03'), 'draft')

    def test_learner_walks_working_stages(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'planned', actor=owner)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'in_progress', actor=owner)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'submitted', actor=owner)
            db.session.commit()
            self.assertEqual(current_stage(owner.id, 'ai-engineering', 'ai.03'), 'submitted')
            stages = [e['to_stage'] for e in history(owner.id, 'ai-engineering', 'ai.03')]
            self.assertEqual(stages, ['planned', 'in_progress', 'submitted'])

    def test_learner_cannot_skip_to_approved(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'submitted', actor=owner)
            with self.assertRaises(LifecycleError):
                record_transition(owner.id, 'ai-engineering', 'ai.03', 'approved', actor=owner)

    def test_reviewer_cannot_approve_own_project(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(reviewer.id, 'ai-engineering', 'ai.03', 'submitted', actor=reviewer)
            with self.assertRaises(LifecycleError):
                record_transition(reviewer.id, 'ai-engineering', 'ai.03', 'approved', actor=reviewer)

    def test_reviewer_can_approve_learner_project(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'submitted', actor=owner)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'approved',
                              actor=reviewer, note='Rubric satisfied')
            db.session.commit()
            self.assertEqual(current_stage(owner.id, 'ai-engineering', 'ai.03'), 'approved')

    def test_automated_review_can_approve(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(owner.id, 'machine-learning', 'mle.classical-ml',
                              'submitted', actor=owner)
            record_transition(owner.id, 'machine-learning', 'mle.classical-ml',
                              'approved', actor=None, note='Automated rubric review')
            db.session.commit()
            self.assertEqual(current_stage(owner.id, 'machine-learning', 'mle.classical-ml'), 'approved')

    def test_resubmission_after_revision_requested(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(owner.id, 'machine-learning', 'mle.classical-ml',
                              'submitted', actor=owner)
            record_transition(owner.id, 'machine-learning', 'mle.classical-ml',
                              'revision_requested', actor=None, note='below threshold')
            record_transition(owner.id, 'machine-learning', 'mle.classical-ml',
                              'submitted', actor=owner, note='Resubmitted')
            db.session.commit()
            self.assertEqual(current_stage(owner.id, 'machine-learning', 'mle.classical-ml'), 'submitted')

    def test_owner_can_archive(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'archived', actor=owner)
            db.session.commit()
            self.assertEqual(current_stage(owner.id, 'ai-engineering', 'ai.03'), 'archived')

    def test_unknown_domain_and_stage_rejected(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            with self.assertRaises(LifecycleError):
                current_stage(owner.id, 'data-science', 'x')
            with self.assertRaises(LifecycleError):
                record_transition(owner.id, 'ai-engineering', 'ai.03', 'in_review', actor=owner)

    def test_same_stage_is_idempotent_noop(self):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            reviewer = db.session.get(User, self.reviewer_id)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'submitted', actor=owner)
            record_transition(owner.id, 'ai-engineering', 'ai.03', 'submitted', actor=owner)
            db.session.commit()
            events = history(owner.id, 'ai-engineering', 'ai.03')
            self.assertEqual(sum(1 for e in events if e['to_stage'] == 'submitted'), 1)


class LifecycleApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.owner_id = self._register('lycowner')

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
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})
        self.client.post('/logout', follow_redirects=True)
        with self.app.app_context():
            return User.query.filter_by(username=username).one().id

    def _login(self, username):
        response = self.client.post('/login', data={
            'username': username, 'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_owner_reads_own_lifecycle(self):
        self._login('lycowner')
        response = self.client.get('/api/projects/lifecycle/ai-engineering/ai.03')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['stage'], 'draft')

    def test_stranger_cannot_read_history(self):
        other_id = self._register('lycother')
        self._login('lycowner')
        response = self.client.get(f'/api/projects/lifecycle/ai-engineering/ai.03?user_id={other_id}')
        self.assertEqual(response.status_code, 403)

    def test_invalid_domain_rejected(self):
        self._login('lycowner')
        response = self.client.get('/api/projects/lifecycle/data-science/x')
        self.assertEqual(response.status_code, 400)

    def test_ai_submission_records_submitted_stage(self):
        self._login('lycowner')
        response = self.client.post(
            '/specializations/ai-engineering/projects/ai.03/submit',
            json={
                'problem_statement': 'Our support team answers the same forty billing questions every day; we need an AI copilot grounded in the help centre.',
                'reflection': 'I built a RAG pipeline with chunking and retrieval, then evaluated it against a held-out set.',
            },
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/api/projects/lifecycle/ai-engineering/ai.03')
        body = response.get_json()
        self.assertEqual(body['stage'], 'submitted')
        self.assertTrue(body['history'])


if __name__ == '__main__':
    unittest.main()
