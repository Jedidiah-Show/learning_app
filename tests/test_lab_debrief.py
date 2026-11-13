"""Engineering troubleshooting labs: judged fix plus rubric-scored debrief."""

import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, db
from app.models import (
    LabDebrief, SkillNode, Submission, User, UserSkillProgress,
)
from app.services.skill_passport import update_skill_progress_from_lab


LAB_PROBLEM = 'lab-troubleshoot-vector-index'
LAB_SKILLS = {'rag', 'vector-databases', 'embeddings', 'debugging'}


def _passing_evaluation():
    return {
        'summary': 'The diagnosis identifies the real root cause.',
        'strengths': ['Names the dimension mismatch precisely'],
        'gaps': ['Could quantify the norm drift'],
        'next_steps': ['Re-run with mixed-dimension fixtures'],
        'criterion_feedback': [
            {'criterion': 'Diagnosis', 'score': 90, 'evidence': 'dim 768 vs 1536 and no L2 norm', 'gap': ''},
            {'criterion': 'Verification', 'score': 80, 'evidence': 'verified against mixed-dimension fixture', 'gap': ''},
            {'criterion': 'Clarity', 'score': 75, 'evidence': 'precise and specific write-up', 'gap': ''},
        ],
    }


def _failing_evaluation():
    return {
        'summary': 'The write-up does not identify the root cause.',
        'strengths': ['Attempts a response'],
        'gaps': ['Root cause never mentioned'],
        'next_steps': ['Re-read the scenario'],
        'criterion_feedback': [
            {'criterion': 'Diagnosis', 'score': 20, 'evidence': 'blames the network', 'gap': 'wrong root cause'},
            {'criterion': 'Verification', 'score': 30, 'evidence': 'said it seems fine', 'gap': 'no method'},
            {'criterion': 'Clarity', 'score': 40, 'evidence': 'vague sentences', 'gap': 'unclear'},
        ],
    }


class LabDebriefTestCase(unittest.TestCase):
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

    def register(self, username):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def seed_accepted(self, problem_id=LAB_PROBLEM):
        with self.app.app_context():
            user = User.query.filter_by(username='learner').one()
            db.session.add(Submission(
                id='accepted-lab-1',
                user_id=user.id,
                problem_id=problem_id,
                code_snapshot='def rebuild_and_search_index(*a): pass',
                verdict='ACCEPTED',
            ))
            db.session.commit()

    def lab_payload(self):
        return {
            'diagnosis': 'Vectors from two embedding providers had mismatched '
                        'dimensions and were never L2-normalised before the dot-product score was computed, '
                        'so similarities exceeded 1.0 and retrieval drifted.',
            'verification': 'I re-ran with a mixed-dimension fixture, confirmed out-of-dim rows are filtered, '
                            'and checked normalized similarities stay within [-1, 1] against the private suite.',
        }

    def test_debrief_endpoint_rejects_unknown_and_non_lab_problems(self):
        self.register('learner')
        response = self.client.get('/arena/api/problems/no-such-lab/debrief')
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/arena/api/problems/algo-binary-search/debrief')
        self.assertEqual(response.status_code, 404)

    def test_debrief_requires_a_judged_accepted_solution(self):
        self.register('learner')
        response = self.client.post(
            f'/arena/api/problems/{LAB_PROBLEM}/debrief',
            json=self.lab_payload(),
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn('ACCEPTED', response.get_json()['error'])

    def test_debrief_rejects_short_or_invalid_text(self):
        self.register('learner')
        self.seed_accepted()
        response = self.client.post(
            f'/arena/api/problems/{LAB_PROBLEM}/debrief',
            json={'diagnosis': 'too short', 'verification': self.lab_payload()['verification']},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            f'/arena/api/problems/{LAB_PROBLEM}/debrief',
            json={'diagnosis': self.lab_payload()['diagnosis'], 'verification': 12345},
        )
        self.assertEqual(response.status_code, 400)

    def test_passing_debrief_stores_result_and_records_lab_evidence(self):
        self.register('learner')
        self.seed_accepted()
        with patch('app.gemini.generate_json', return_value=_passing_evaluation()):
            response = self.client.post(
                f'/arena/api/problems/{LAB_PROBLEM}/debrief',
                json=self.lab_payload(),
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data['status'], 'passed')
        self.assertEqual(data['debrief']['score'], 82)
        self.assertTrue(data['debrief']['passed'])
        with self.app.app_context():
            debrief = LabDebrief.query.filter_by(problem_id=LAB_PROBLEM).one()
            self.assertTrue(debrief.passed)
            self.assertEqual(debrief.evaluation_source, 'ai')
            for skill in LAB_SKILLS:
                self.assertTrue(
                    SkillNode.query.filter_by(id=skill).first() is not None,
                    f'skill node {skill} must exist',
                )
            progress = UserSkillProgress.query.filter(
                UserSkillProgress.skill_id.in_(LAB_SKILLS),
                UserSkillProgress.evidence_type == 'LAB',
            ).all()
            self.assertEqual(len(progress), len(LAB_SKILLS))
            self.assertTrue(all(row.status in {'DEMONSTRATED', 'MASTERED'} for row in progress))
            self.assertTrue(all(row.evidence_id == LAB_PROBLEM for row in progress))

    def test_failing_debrief_is_recorded_without_lab_evidence(self):
        self.register('learner')
        self.seed_accepted()
        with patch('app.gemini.generate_json', return_value=_failing_evaluation()):
            response = self.client.post(
                f'/arena/api/problems/{LAB_PROBLEM}/debrief',
                json=self.lab_payload(),
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data['status'], 'recorded')
        self.assertFalse(data['debrief']['passed'])
        self.assertEqual(data['debrief']['score'], 30)
        with self.app.app_context():
            self.assertFalse(
                UserSkillProgress.query.filter_by(evidence_type='LAB').first() is not None,
            )

    def test_ai_outage_saves_debrief_as_pending_review(self):
        from app.gemini import GeminiError

        self.register('learner')
        self.seed_accepted()
        with patch('app.gemini.generate_json', side_effect=GeminiError('boom')):
            response = self.client.post(
                f'/arena/api/problems/{LAB_PROBLEM}/debrief',
                json=self.lab_payload(),
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data['status'], 'pending_review')
        self.assertEqual(data['evaluation_source'], 'local')
        self.assertFalse(data['debrief']['passed'])
        with self.app.app_context():
            debrief = LabDebrief.query.filter_by(problem_id=LAB_PROBLEM).one()
            self.assertEqual(debrief.evaluation_source, 'local')
            self.assertIsNone(debrief.score)

    def test_invalid_ai_payload_returns_503_and_stores_nothing(self):
        self.register('learner')
        self.seed_accepted()
        with patch('app.gemini.generate_json', return_value={'unexpected': True}):
            response = self.client.post(
                f'/arena/api/problems/{LAB_PROBLEM}/debrief',
                json=self.lab_payload(),
            )
        self.assertEqual(response.status_code, 503)
        with self.app.app_context():
            self.assertIsNone(LabDebrief.query.filter_by(problem_id=LAB_PROBLEM).first())

    def test_get_returns_null_debrief_before_first_submission(self):
        self.register('learner')
        response = self.client.get(f'/arena/api/problems/{LAB_PROBLEM}/debrief')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()['debrief'])

    def test_get_returns_stored_debrief_after_submission(self):
        self.register('learner')
        self.seed_accepted()
        with patch('app.gemini.generate_json', return_value=_passing_evaluation()):
            self.client.post(
                f'/arena/api/problems/{LAB_PROBLEM}/debrief',
                json=self.lab_payload(),
            )
        response = self.client.get(f'/arena/api/problems/{LAB_PROBLEM}/debrief')
        self.assertEqual(response.status_code, 200)
        debrief = response.get_json()['debrief']
        self.assertTrue(debrief['passed'])
        self.assertEqual(debrief['diagnosis'], self.lab_payload()['diagnosis'])

    def test_lab_problems_are_flagged_and_page_shows_debrief_panel(self):
        self.register('learner')
        response = self.client.get(f'/arena/api/problems/{LAB_PROBLEM}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['problem']['is_lab'])
        page = self.client.get(f'/arena/problems/{LAB_PROBLEM}')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'data-lab-debrief', page.data)
        other = self.client.get('/arena/problems/algo-binary-search')
        self.assertEqual(other.status_code, 200)
        self.assertNotIn(b'data-lab-debrief', other.data)

    def test_lab_evidence_is_not_downgraded_by_later_problem_acceptance(self):
        self.register('learner')
        self.seed_accepted()
        with patch('app.gemini.generate_json', return_value=_passing_evaluation()):
            self.client.post(
                f'/arena/api/problems/{LAB_PROBLEM}/debrief',
                json=self.lab_payload(),
            )
        with self.app.app_context():
            user = User.query.filter_by(username='learner').one()
            for skill_id, title in (('rag', 'rag'),):
                progress = UserSkillProgress.query.filter_by(
                    user_id=user.id, skill_id=skill_id,
                ).one()
                self.assertEqual(progress.evidence_type, 'LAB')
            # Simulate a later judged acceptance of a non-lab problem sharing
            # the same skill; LAB evidence must survive.
            problem = {
                'id': 'rag-rank-chunks', 'skills': ['rag'], 'track': 'ai-engineering',
            }
            db.session.add(Submission(
                id='accepted-nonlab-1',
                user_id=user.id,
                problem_id='rag-rank-chunks',
                code_snapshot='def rank_chunks(*a): pass',
                verdict='ACCEPTED',
            ))
            db.session.commit()
            from app.services.skill_passport import _award_problem_skills
            _award_problem_skills(user.id, problem, 'PROBLEM', commit=True)
            progress = UserSkillProgress.query.filter_by(
                user_id=user.id, skill_id='rag',
            ).one()
            self.assertEqual(progress.evidence_type, 'LAB')


if __name__ == '__main__':
    unittest.main()
