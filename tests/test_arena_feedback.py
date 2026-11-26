"""M3.4/M3.5 — Arena diagnostic feedback and dismissable recommendations."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import (
    SkillNode, Submission, User, UserSkillProgress,
)
from app.services.arena_feedback import DISCLAIMER, diagnostic_for


class DiagnosticUnitTests(unittest.TestCase):
    def _sub(self, verdict, tests_passed=0, total_tests=0, error_details=''):
        class S:
            pass
        s = S()
        s.verdict, s.tests_passed, s.total_tests, s.error_details = (
            verdict, tests_passed, total_tests, error_details)
        return s

    def test_compile_error_is_syntax_error(self):
        d = diagnostic_for(self._sub('COMPILE_ERROR', error_details='SyntaxError: unexpected EOF'))
        self.assertEqual(d['category'], 'syntax_error')
        self.assertEqual(d['confidence'], 'high')

    def test_timeout_is_complexity_issue(self):
        self.assertEqual(diagnostic_for(self._sub('TIME_LIMIT_EXCEEDED'))['category'], 'complexity_issue')
        self.assertEqual(diagnostic_for(self._sub('MEMORY_LIMIT_EXCEEDED'))['category'], 'complexity_issue')

    def test_runtime_error_specific_mappings(self):
        self.assertEqual(diagnostic_for(self._sub('RUNTIME_ERROR', error_details='IndexError: list index out of range'))['category'], 'boundary_condition')
        self.assertEqual(diagnostic_for(self._sub('RUNTIME_ERROR', error_details='KeyError: foo'))['category'], 'data_structure_misuse')
        self.assertEqual(diagnostic_for(self._sub('RUNTIME_ERROR', error_details='TypeError: unsupported operand'))['category'], 'incorrect_assumption')
        self.assertEqual(diagnostic_for(self._sub('RUNTIME_ERROR', error_details='NameError: name x is not defined'))['category'], 'incomplete_implementation')
        self.assertEqual(diagnostic_for(self._sub('RUNTIME_ERROR', error_details='something exotic'))['category'], 'runtime_error')

    def test_wrong_answer_spectrum(self):
        self.assertEqual(diagnostic_for(self._sub('WRONG_ANSWER', tests_passed=0, total_tests=7))['category'], 'incorrect_algorithm')
        self.assertEqual(diagnostic_for(self._sub('WRONG_ANSWER', tests_passed=3, total_tests=7))['category'], 'boundary_condition')

    def test_accepted_has_no_diagnostic(self):
        self.assertIsNone(diagnostic_for(self._sub('ACCEPTED', tests_passed=7, total_tests=7)))

    def test_every_diagnostic_is_honest_and_disclaimed(self):
        for verdict in ('COMPILE_ERROR', 'TIME_LIMIT_EXCEEDED', 'RUNTIME_ERROR',
                        'WRONG_ANSWER', 'PENDING', 'INTERNAL_ERROR'):
            d = diagnostic_for(self._sub(verdict, tests_passed=1, total_tests=3))
            self.assertEqual(d['disclaimer'], DISCLAIMER)
            self.assertIn(d['confidence'], ('low', 'medium', 'high'))
            self.assertNotIn('the hidden input is', d['detail'].lower())


class ArenaFeedbackApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

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

    def _register(self, username='arenauser'):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def _submission(self, user_id, verdict='ACCEPTED', skill=None, problem_id='ml-feature-minmax-scale'):
        with self.app.app_context():
            row = Submission(
                id=f'{user_id}-{verdict.lower()}', user_id=user_id,
                problem_id=problem_id, code_snapshot='pass',
                verdict=verdict, tests_passed=9, total_tests=10,
                error_details='',
            )
            db.session.add(row)
            db.session.commit()

    def test_submission_detail_includes_diagnostic(self):
        self._register()
        with self.app.app_context():
            user = User.query.filter_by(username='arenauser').one()
            self._submission(user.id, 'WRONG_ANSWER')
        response = self.client.get('/arena/api/submissions/1-wrong_answer')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['diagnostic']['category'], 'boundary_condition')

    def test_history_list_includes_diagnostic_and_is_owner_scoped(self):
        self._register()
        with self.app.app_context():
            user = User.query.filter_by(username='arenauser').one()
            self._submission(user.id, 'ACCEPTED')
        response = self.client.get('/arena/api/submissions')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['submissions'][0]['diagnostic'], None)


class ArenaRecommendationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            db.session.add(SkillNode(
                id='ml-data-analysis', title='Data analysis',
                normalized_title='ml-data-analysis', category='Machine Learning',
            ))
            db.session.commit()
        self.client = self.app.test_client()

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

    def _register(self, username='rectify'):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def _enrol_ml(self, username):
        with self.app.app_context():
            from app.models import LearningPathway, LearnerPathwayEnrollment
            pathway = LearningPathway(
                id='machine-learning', slug='machine-learning',
                name='Machine Learning', description='ML pathway',
                domain_type='SPECIALIZATION', version='1.0.0', status='ACTIVE',
            )
            db.session.add(pathway)
            db.session.commit()
            user = User.query.filter_by(username=username).one()
            db.session.add(LearnerPathwayEnrollment(
                learner_id=user.id, pathway_id='machine-learning', status='ENROLLED',
            ))
            db.session.commit()

    def test_recommendations_have_reasons_and_dismissal_hides_item(self):
        self._register()
        self._enrol_ml('rectify')
        with self.app.app_context():
            user = User.query.filter_by(username='rectify').one()
            db.session.add(UserSkillProgress(
                user_id=user.id, skill_id='ml-data-analysis',
                status='DEVELOPING', evidence_type='PROBLEM', evidence_id='x',
            ))
            db.session.commit()
        response = self.client.get('/arena/api/recommendations')
        self.assertEqual(response.status_code, 200)
        recs = response.get_json()['recommendations']
        self.assertTrue(recs)
        for rec in recs:
            self.assertTrue(rec['reason'])
            self.assertIn('/arena/problems/', rec['url'])
        first = recs[0]['problem_id']
        dismiss = self.client.post('/arena/api/recommendations/dismiss',
                                   json={'problem_id': first})
        self.assertEqual(dismiss.status_code, 200)
        response = self.client.get('/arena/api/recommendations')
        remaining = {r['problem_id'] for r in response.get_json()['recommendations']}
        self.assertNotIn(first, remaining)

    def test_dismiss_requires_valid_payload(self):
        self._register()
        response = self.client.post('/arena/api/recommendations/dismiss', json={})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
