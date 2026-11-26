"""M4 — Skill Passport role model and domain classification tests."""

import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import (
    SkillNode, SkillVerification, User, UserSkillProgress,
)
from app.routes.passport import _skill_domain
from app.services.authorization import effective_role


class RoleModelTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            self._seed_skill('ml-mathematics-statistics', 'Mathematics and statistics',
                             'Machine Learning')
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

    def _seed_skill(self, skill_id, title, category):
        db.session.add(SkillNode(
            id=skill_id, title=title, normalized_title=skill_id, category=category,
        ))
        db.session.commit()

    def _create(self, username, role='learner', is_admin=False):
        with self.app.app_context():
            user = User(
                username=username, email=f'{username}@example.test',
                full_name=username.title(),
                password_hash=generate_password_hash('secure-pass-123'),
                role=role, is_admin=is_admin,
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    def _login(self, username):
        response = self.client.post('/login', data={
            'username': username, 'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def _logout(self):
        self.client.post('/logout', follow_redirects=True)

    def _seed_progress(self, user_id, verification_status='SUBMITTED'):
        with self.app.app_context():
            db.session.add(UserSkillProgress(
                user_id=user_id, skill_id='ml-mathematics-statistics',
                status='DEMONSTRATED', evidence_type='PROJECT',
                evidence_id='proj-1', verification_status=verification_status,
            ))
            db.session.commit()

    def test_default_role_is_learner(self):
        uid = self._create('newbie')
        with self.app.app_context():
            self.assertEqual(effective_role(db.session.get(User, uid)), 'learner')

    def test_is_admin_maps_to_administrator(self):
        uid = self._create('oldadmin', is_admin=True)
        with self.app.app_context():
            self.assertEqual(effective_role(db.session.get(User, uid)), 'administrator')

    def test_reviewer_can_assess_learner_evidence(self):
        owner = self._create('evidenceowner')
        reviewer = self._create('evidencereviewer', role='reviewer')
        self._seed_progress(owner)
        self._login('evidencereviewer')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': owner},
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            progress = UserSkillProgress.query.filter_by(
                user_id=owner, skill_id='ml-mathematics-statistics').one()
            self.assertEqual(progress.verified_by_user_id, reviewer)

    def test_reviewer_cannot_assess_own_evidence(self):
        reviewer = self._create('selfrreview', role='reviewer')
        self._seed_progress(reviewer)
        self._login('selfrreview')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': reviewer},
        )
        self.assertEqual(response.status_code, 403)

    def test_instructor_counts_as_reviewer(self):
        owner = self._create('instr-owner')
        self._create('instr-reviewer', role='instructor')
        self._seed_progress(owner)
        self._login('instr-reviewer')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': owner},
        )
        self.assertEqual(response.status_code, 200)

    def test_administrator_role_without_legacy_flag_can_assess_and_manage(self):
        owner = self._create('admin2-owner')
        administrator = self._create('admin2-admin', role='administrator', is_admin=False)
        self._seed_progress(owner)
        self._login('admin2-admin')
        response = self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': owner},
        )
        self.assertEqual(response.status_code, 200)
        from app.services.authorization import (
            can_manage_reviewer_access, can_assess_competency, effective_role,
        )
        with self.app.app_context():
            admin_user = db.session.get(User, administrator)
            self.assertEqual(effective_role(admin_user), 'administrator')
            self.assertTrue(can_manage_reviewer_access(admin_user))
            self.assertTrue(can_assess_competency(admin_user, owner))

    def test_revocation_preserves_original_verification_event(self):
        owner = self._create('auditowner')
        self._create('auditreviewer', role='reviewer')
        self._seed_progress(owner, verification_status='UNVERIFIED')
        self._login('auditowner')
        response = self.client.post('/api/passport/skills/ml-mathematics-statistics/verify')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self._logout()
        self._login('auditreviewer')
        self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/assess',
            json={'verification_status': 'VERIFIED', 'user_id': owner, 'note': 'ok'},
        )
        self.client.post(
            '/api/passport/skills/ml-mathematics-statistics/invalidate',
            json={'reason': 'evidence was fabricated', 'user_id': owner},
        )
        with self.app.app_context():
            events = SkillVerification.query.filter_by(
                user_id=owner, skill_id='ml-mathematics-statistics',
            ).order_by(SkillVerification.id.asc()).all()
            transitions = [(e.from_status, e.to_status) for e in events]
        self.assertEqual(
            transitions,
            [('UNVERIFIED', 'SUBMITTED'), ('SUBMITTED', 'VERIFIED'), ('VERIFIED', 'REVOKED')],
        )


class DomainClassificationTests(unittest.TestCase):
    def _classify(self, skill_id, category='curriculum', title=''):
        return _skill_domain({'id': skill_id, 'category': category, 'title': title})

    def test_ml_competencies(self):
        self.assertEqual(self._classify('ml-mathematics-statistics', 'machine learning'), 'machine-learning')
        self.assertEqual(self._classify('mle.tools.01'), 'machine-learning')

    def test_legacy_foundation_modules_are_not_ai(self):
        self.assertEqual(self._classify('curriculum-00'), 'shared-foundations')
        self.assertEqual(self._classify('curriculum-01'), 'shared-foundations')
        self.assertEqual(self._classify('curriculum-02'), 'shared-foundations')

    def test_legacy_ai_modules_are_ai(self):
        self.assertEqual(self._classify('curriculum-03'), 'ai-engineering')
        self.assertEqual(self._classify('curriculum-12'), 'ai-engineering')
        self.assertEqual(self._classify('lesson-3-01'), 'ai-engineering')
        self.assertEqual(self._classify('lesson-0-01'), 'shared-foundations')
        self.assertEqual(self._classify('lesson-2-14'), 'shared-foundations')

    def test_shared_foundations_nodes(self):
        self.assertEqual(self._classify('lesson-sf-00-01', 'foundations'), 'shared-foundations')
        self.assertEqual(self._classify('sf.00.01', 'foundations'), 'shared-foundations')

    def test_ai_and_project_studio(self):
        self.assertEqual(self._classify('ai-03.01'), 'ai-engineering')
        self.assertEqual(self._classify('project-studio', 'projects'), 'ai-engineering')
        self.assertEqual(self._classify('lesson-ai-03-01'), 'ai-engineering')

    def test_arena_tracks(self):
        self.assertEqual(self._classify('some-ai-problem', 'ai-engineering'), 'ai-engineering')
        self.assertEqual(self._classify('some-ml-problem', 'machine-learning'), 'machine-learning')
        self.assertEqual(self._classify('algo-binary-search', 'algorithms'), 'shared-foundations')


if __name__ == '__main__':
    unittest.main()
