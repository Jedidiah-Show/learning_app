"""M6 — Learning Intelligence: mastery model, recommendations, concept graph."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import (
    LearnerPathwayEnrollment, LearningPathway, ReviewItem, SkillNode,
    SkillVerification, User, UserSkillProgress,
)
from app.services.mastery import (
    concept_mastery, domain_summary,
)
from app.services.recommendations import recommend
from app.services.concept_graph import (
    build_graph, dependents_of, prerequisites_of, is_valid_edge,
)


class LearningIntelligenceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            self.user = User(username='intellect', email='intellect@example.test',
                             password_hash='x')
            db.session.add(self.user)
            for skill_id in ('ml-mathematics-statistics', 'ml-supervised-learning',
                             'ml-data-analysis'):
                db.session.add(SkillNode(
                    id=skill_id, title=skill_id.replace('-', ' ').title(),
                    normalized_title=skill_id, category='Machine Learning',
                ))
            db.session.commit()
            self.user_id = self.user.id

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

    def _seed_progress(self, skill_id, status='NOT_STARTED', evidence_type=None,
                       evidence_id=None):
        with self.app.app_context():
            db.session.add(UserSkillProgress(
                user_id=self.user_id, skill_id=skill_id,
                status=status, evidence_type=evidence_type,
                evidence_id=evidence_id,
            ))
            db.session.commit()

    def _seed_verification(self, skill_id, to_status, from_status='UNVERIFIED'):
        with self.app.app_context():
            db.session.add(SkillVerification(
                user_id=self.user_id, skill_id=skill_id,
                from_status=from_status, to_status=to_status,
            ))
            db.session.commit()

    def _enrol(self, pathway_id):
        with self.app.app_context():
            pathway = LearningPathway(
                id=pathway_id, slug=pathway_id, name=pathway_id,
                description=f'{pathway_id} pathway', domain_type='SPECIALIZATION',
                version='1.0.0', status='ACTIVE',
            )
            db.session.add(pathway)
            db.session.commit()
            db.session.add(LearnerPathwayEnrollment(
                learner_id=self.user_id, pathway_id=pathway_id, status='ENROLLED',
            ))
            db.session.commit()

    def test_lesson_only_evidence_is_practising_not_proficient(self):
        self._seed_progress('ml-mathematics-statistics', 'DEVELOPING', 'LESSON', 'mle.math.01')
        with self.app.app_context():
            items = {i['skill_id']: i for i in concept_mastery(self.user_id)}
            self.assertEqual(items['ml-mathematics-statistics']['mastery'], 'practising')

    def test_judged_project_evidence_reaches_proficient(self):
        self._seed_progress('ml-supervised-learning', 'DEMONSTRATED', 'PROJECT', 'mle.classical-ml')
        with self.app.app_context():
            items = {i['skill_id']: i for i in concept_mastery(self.user_id)}
            self.assertEqual(items['ml-supervised-learning']['mastery'], 'proficient')

    def test_mastered_requires_mastered_status(self):
        self._seed_progress('ml-supervised-learning', 'MASTERED', 'PROBLEM', 'ml-p1')
        with self.app.app_context():
            items = {i['skill_id']: i for i in concept_mastery(self.user_id)}
            self.assertEqual(items['ml-supervised-learning']['mastery'], 'mastered')

    def test_revocation_flags_needs_review(self):
        self._seed_progress('ml-data-analysis', 'DEMONSTRATED', 'PROBLEM', 'ml-p1')
        self._seed_verification('ml-data-analysis', 'VERIFIED', 'SUBMITTED')
        self._seed_verification('ml-data-analysis', 'REVOKED', 'VERIFIED')
        with self.app.app_context():
            items = {i['skill_id']: i for i in concept_mastery(self.user_id)}
            self.assertEqual(items['ml-data-analysis']['mastery'], 'needs_review')

    def test_domain_summary_groups_by_domain(self):
        self._seed_progress('ml-mathematics-statistics', 'DEVELOPING', 'LESSON', 'mle.math.01')
        with self.app.app_context():
            summary = domain_summary(self.user_id)
            self.assertIn('machine-learning', summary)
            self.assertEqual(summary['machine-learning']['practising'], 1)

    def test_recommendations_cite_reason_and_respect_reviews(self):
        with self.app.app_context():
            db.session.add(ReviewItem(
                user_id=self.user_id, quiz_id='q', question_id='qq',
                subject_id='s', question='q?', options='["a","b"]',
                correct_index=0, due_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
            ))
            db.session.commit()
        self._seed_progress('ml-data-analysis', 'DEVELOPING', 'PROBLEM', 'x')
        self._enrol('machine-learning')
        with self.app.app_context():
            recs = recommend(self.user_id, limit=5)
        kinds = {r['kind'] for r in recs}
        self.assertIn('review', kinds)
        for rec in recs:
            self.assertTrue(rec['reason'])
            self.assertIn(rec['confidence'], ('low', 'medium', 'high'))
        review_rec = next(r for r in recs if r['kind'] == 'review')
        self.assertEqual(review_rec['confidence'], 'high')

    def test_concept_graph_edges_and_traversal(self):
        graph = build_graph('ai-engineering')
        self.assertTrue(any(n['type'] == 'module' for n in graph['nodes']))
        self.assertTrue(any(n['type'] == 'lesson' for n in graph['nodes']))
        self.assertTrue(any(e['type'] == 'contains' for e in graph['edges']))
        deps = dependents_of('sf.00')
        self.assertIn('ai.03', deps)
        prereqs = prerequisites_of('ai-engineering', 'ai.04')
        self.assertIn('sf.00', prereqs)
        self.assertTrue(is_valid_edge('ai-engineering', 'module', 'shared-foundations', 'module'))
        self.assertTrue(is_valid_edge('machine-learning', 'module', 'shared-foundations', 'module'))
        self.assertFalse(is_valid_edge('ai-engineering', 'module', 'machine-learning', 'module'))


if __name__ == '__main__':
    unittest.main()

class MasteryDashboardTests(unittest.TestCase):
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

    def test_mastery_dashboard_requires_login(self):
        response = self.client.get('/mastery')
        self.assertIn(response.status_code, (302, 401))

    def test_mastery_dashboard_renders_for_learner(self):
        response = self.client.post('/register', data={
            'username': 'dashboardlearner',
            'email': 'dashboardlearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Dashboard Learner',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})
        page = self.client.get('/mastery')
        self.assertEqual(page.status_code, 200)
        body = page.get_data(as_text=True)
        self.assertIn('Concept mastery', body)
        self.assertIn('Recommended next steps', body)

    def test_graph_endpoint_validates_domain(self):
        response = self.client.post('/register', data={
            'username': 'graphlearner',
            'email': 'graphlearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Graph Learner',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})
        ok = self.client.get('/api/mastery/graph?domain=ai-engineering')
        self.assertEqual(ok.status_code, 200)
        bad = self.client.get('/api/mastery/graph?domain=data-science')
        self.assertEqual(bad.status_code, 400)
