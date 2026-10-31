"""Administrator portal access control, account management, and audit tests."""

import os
import tempfile
import time
import unittest

from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app, db
from app.models import AdminAuditLog, LessonCompletion, SupportRequest, User


class AdminPortalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            db.create_all()
            learner = User(
                username='learner',
                email='learner@example.test',
                full_name='Learner One',
                password_hash=generate_password_hash('secure-pass-123'),
            )
            admin = User(
                username='admin',
                email='admin@example.test',
                full_name='Admin One',
                password_hash=generate_password_hash('secure-pass-123'),
                is_admin=True,
            )
            other_admin = User(
                username='admin2',
                email='admin2@example.test',
                password_hash=generate_password_hash('secure-pass-123'),
                is_admin=True,
            )
            db.session.add_all([learner, admin, other_admin])
            db.session.commit()
            self.learner_id = learner.id
            self.admin_id = admin.id
            self.other_admin_id = other_admin.id
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

    # ------------------------------------------------------------------ helpers
    def _login_learner(self, username='learner', password='secure-pass-123',
                       client=None):
        client = client or self.client
        return client.post('/login', data={
            'username': username, 'password': password,
        }, follow_redirects=False)

    def _login_admin(self, identifier='admin', password='secure-pass-123',
                     client=None):
        client = client or self.client
        return client.post('/admin/login', data={
            'identifier': identifier, 'password': password,
        }, follow_redirects=False)

    def _account(self, user_id):
        with self.app.app_context():
            return db.session.get(User, user_id)

    def _audit(self, action, target_user_id=None):
        with self.app.app_context():
            query = AdminAuditLog.query.filter_by(action=action)
            if target_user_id is not None:
                query = query.filter_by(target_user_id=target_user_id)
            return query.order_by(AdminAuditLog.id.desc()).first()

    def _create_account(self, username, email=None, is_admin=False):
        with self.app.app_context():
            account = User(
                username=username,
                email=email or f'{username}@example.test',
                password_hash=generate_password_hash('secure-pass-123'),
                is_admin=is_admin,
            )
            db.session.add(account)
            db.session.commit()
            return account.id

    # --------------------------------------------------------------- public entry
    def test_admin_portal_is_reachable_from_the_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn('/admin/login', response.get_data(as_text=True))

        response = self.client.get('/admin/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Admin Portal', response.get_data(as_text=True))

    def test_admin_pages_require_a_dedicated_admin_session(self):
        for path in ('/admin', '/admin/users', '/admin/analytics', '/admin/audit'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertIn('/admin/login', response.headers['Location'], path)

    def test_learner_cannot_open_admin_pages(self):
        self._login_learner()
        for path in ('/admin', '/admin/users', '/admin/analytics', '/admin/audit'):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_admin_dashboard_reports_ml_pathway_status(self):
        from app.ml_pathway import PATHWAY_ID
        from app.models import (
            MLSpecializationCredential, MLSpecializationLessonCompletion,
        )
        enrolled = self._create_account('ml-pilot')
        with self.app.app_context():
            db.session.add(MLSpecializationLessonCompletion(
                user_id=enrolled, pathway_id=PATHWAY_ID,
                lesson_id='mle.data.01',
            ))
            db.session.add(MLSpecializationCredential(
                user_id=enrolled, pathway_id=PATHWAY_ID,
                public_id='admin-test-credential', recipient_name='ML Pilot',
            ))
            db.session.commit()
        self._login_admin()
        page = self.client.get('/admin')
        self.assertEqual(page.status_code, 200)
        body = page.get_data(as_text=True)
        self.assertIn('ML Engineering specialization', body)
        self.assertIn('hold the specialization credential', body)

    def test_learner_cannot_sign_in_to_the_admin_portal(self):
        self._login_learner()
        response = self._login_admin('learner')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Invalid administrator credentials',
            response.get_data(as_text=True),
        )
        self.assertEqual(self.client.get('/admin').status_code, 403)

    def test_admin_must_authenticate_inside_the_admin_portal(self):
        self._login_learner('admin')
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.headers['Location'])

        response = self._login_admin()
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin', response.headers['Location'])
        self.assertNotIn('/admin/login', response.headers['Location'])
        self.assertEqual(self.client.get('/admin').status_code, 200)

    def test_admin_portal_pages_render(self):
        self._login_admin()
        paths = (
            '/admin',
            '/admin/users',
            '/admin/users/new',
            f'/admin/users/{self.learner_id}',
            '/admin/analytics',
            '/admin/audit',
        )
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_learner_support_request_reaches_admin_inbox_and_status(self):
        self._login_learner()
        self.assertEqual(self.client.get('/support').status_code, 200)
        submitted = self.client.post('/support', data={
            'category': 'feature',
            'subject': 'Add model comparison guide',
            'message': 'A short guide comparing common model tradeoffs would help learners choose tools.',
        })
        self.assertEqual(submitted.status_code, 302)
        with self.app.app_context():
            report = SupportRequest.query.one()
            self.assertEqual(report.user_id, self.learner_id)
            self.assertEqual(report.status, 'new')
            report_id = report.id

        self._login_admin()
        inbox = self.client.get('/admin/support')
        self.assertEqual(inbox.status_code, 200)
        self.assertIn('Add model comparison guide', inbox.get_data(as_text=True))
        updated = self.client.post(
            f'/admin/support/{report_id}', data={'status': 'in_review'},
        )
        self.assertEqual(updated.status_code, 302)

        learner_client = self.app.test_client()
        self._login_learner(client=learner_client)
        learner_page = learner_client.get('/support')
        self.assertEqual(learner_page.status_code, 200)
        self.assertIn('In Review', learner_page.get_data(as_text=True))

    def test_admin_session_expires(self):
        self._login_admin()
        self.assertEqual(self.client.get('/admin').status_code, 200)
        with self.client.session_transaction() as flask_session:
            flask_session['admin_authenticated_at'] = time.time() - 3600
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.headers['Location'])
        # The learner session is untouched by an expired admin session.
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_admin_login_stays_inside_the_portal(self):
        client = self.app.test_client()
        response = client.post('/admin/login', data={
            'identifier': 'admin',
            'password': 'secure-pass-123',
            'next': '/admin/users?',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/admin/users'))

        other = self.app.test_client()
        response = other.post('/admin/login', data={
            'identifier': 'admin',
            'password': 'secure-pass-123',
            'next': 'https://evil.example/phish',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.headers['Location'].rstrip('/').endswith('/admin')
        )

    def test_learner_logout_clears_the_admin_grant(self):
        self._login_admin()
        self.assertEqual(self.client.get('/admin').status_code, 200)
        self.client.post('/logout')
        self._login_learner('admin')
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.headers['Location'])

    def test_exiting_the_portal_revokes_only_the_admin_session(self):
        self._login_admin()
        self.assertEqual(self.client.get('/admin/exit').status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/admin').status_code, 302)

    def test_admin_pages_are_never_cached(self):
        self._login_admin()
        response = self.client.get('/admin')
        self.assertIn('no-store', response.headers['Cache-Control'])

    # ------------------------------------------------------------------- create
    def test_admin_can_create_a_learner(self):
        self._login_admin()
        response = self.client.post('/admin/users/new', data={
            'username': 'newbie',
            'email': 'newbie@example.test',
            'full_name': 'New Bie',
            'phone': '+15551234567',
            'password': 'brand-new-pass',
            'confirm_password': 'brand-new-pass',
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            account = User.query.filter_by(username='newbie').first()
            self.assertIsNotNone(account)
            self.assertFalse(account.is_admin)
            self.assertTrue(account.is_active)
            self.assertEqual(account.phone, '+15551234567')
            self.assertTrue(check_password_hash(
                account.password_hash, 'brand-new-pass'
            ))
            new_id = account.id
        entry = self._audit('user.create', new_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.admin_user_id, self.admin_id)

    def test_create_user_rejects_duplicate_and_short_password(self):
        self._login_admin()
        response = self.client.post('/admin/users/new', data={
            'username': 'learner',
            'email': 'learner@example.test',
            'password': 'short',
            'confirm_password': 'short',
        })
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('already in use', html)
        self.assertIn('at least 8 characters', html)
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(username='learner').count(), 1)

    # ------------------------------------------------------------------- update
    def test_admin_can_edit_profile_and_invalidate_sessions(self):
        self._login_admin()
        before = self._account(self.learner_id).auth_version
        response = self.client.post(
            f'/admin/users/{self.learner_id}/profile',
            data={
                'username': 'learner',
                'email': 'learner-updated@example.test',
                'full_name': 'Learner Updated',
                'phone': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        account = self._account(self.learner_id)
        self.assertEqual(account.email, 'learner-updated@example.test')
        self.assertEqual(account.full_name, 'Learner Updated')
        self.assertEqual(account.auth_version, before + 1)
        self.assertIsNotNone(self._audit('user.update', self.learner_id))

    def test_admin_can_reset_a_password(self):
        self._login_admin()
        before = self._account(self.learner_id).auth_version
        response = self.client.post(
            f'/admin/users/{self.learner_id}/password',
            data={
                'password': 'replacement-pass',
                'confirm_password': 'replacement-pass',
            },
        )
        self.assertEqual(response.status_code, 302)
        account = self._account(self.learner_id)
        self.assertEqual(account.auth_version, before + 1)
        self.assertTrue(check_password_hash(
            account.password_hash, 'replacement-pass'
        ))
        self.assertIsNotNone(
            self._audit('user.password_reset', self.learner_id)
        )

        fresh_client = self.app.test_client()
        response = self._login_learner(
            username='learner',
            password='replacement-pass',
            client=fresh_client,
        )
        self.assertEqual(response.status_code, 302)

    # ------------------------------------------------------------ role / status
    def test_admin_can_promote_and_demote_a_learner(self):
        self._login_admin()
        response = self.client.post(
            f'/admin/users/{self.learner_id}/role',
            data={'is_admin': '1'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self._account(self.learner_id).is_admin)

        response = self.client.post(
            f'/admin/users/{self.learner_id}/role',
            json={'is_admin': False},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['is_admin'])
        self.assertFalse(self._account(self.learner_id).is_admin)
        self.assertIsNotNone(
            self._audit('user.role_change', self.learner_id)
        )

    def test_admin_cannot_remove_their_own_access(self):
        self._login_admin()
        response = self.client.post(
            f'/admin/users/{self.admin_id}/role',
            json={'is_admin': False},
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(self._account(self.admin_id).is_admin)

    def test_admin_can_deactivate_and_reactivate_an_account(self):
        self._login_admin()
        response = self.client.post(
            f'/admin/users/{self.learner_id}/status',
            data={'is_active': '0'},
        )
        self.assertEqual(response.status_code, 302)
        account = self._account(self.learner_id)
        self.assertFalse(account.is_active)

        blocked_client = self.app.test_client()
        response = self._login_learner(client=blocked_client)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Invalid username or password',
            response.get_data(as_text=True),
        )

        response = self.client.post(
            f'/admin/users/{self.learner_id}/status',
            data={'is_active': '1'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self._account(self.learner_id).is_active)

    def test_deactivating_an_account_revokes_an_open_session(self):
        learner_client = self.app.test_client()
        self.assertEqual(
            self._login_learner(client=learner_client).status_code, 302
        )
        self.assertEqual(learner_client.get('/').status_code, 200)

        self._login_admin()
        self.client.post(
            f'/admin/users/{self.learner_id}/status',
            data={'is_active': '0'},
        )
        response = learner_client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_admin_cannot_deactivate_themselves(self):
        self._login_admin()
        response = self.client.post(
            f'/admin/users/{self.admin_id}/status',
            json={'is_active': False},
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(self._account(self.admin_id).is_active)

    # ------------------------------------------------------------------- delete
    def test_admin_can_delete_an_account_with_confirmation(self):
        target_id = self._create_account('deletable')
        with self.app.app_context():
            db.session.add(LessonCompletion(
                user_id=target_id,
                lesson_id='python-foundations-1',
                subject_id='python',
                day_number=1,
                completed=True,
            ))
            db.session.commit()

        self._login_admin()
        response = self.client.post(
            f'/admin/users/{target_id}/delete',
            data={'confirmation': 'wrong-name'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(self._account(target_id))

        response = self.client.post(
            f'/admin/users/{target_id}/delete',
            data={'confirmation': 'deletable'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self._account(target_id))
        self.assertIsNotNone(self._audit('user.delete', target_id))

    def test_admin_cannot_delete_themselves(self):
        self._login_admin()
        response = self.client.post(
            f'/admin/users/{self.admin_id}/delete',
            data={'confirmation': 'admin'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(self._account(self.admin_id))

    # --------------------------------------------------------- list / audit log
    def test_user_list_supports_search_and_pagination(self):
        for index in range(25):
            self._create_account(f'paged{index:02d}')
        self._login_admin()

        response = self.client.get('/admin/users?q=paged')
        self.assertEqual(response.status_code, 200)
        first_page = response.get_data(as_text=True)
        self.assertIn('paged24', first_page)
        self.assertIn('paged05', first_page)
        self.assertNotIn('paged04', first_page)

        response = self.client.get('/admin/users?q=no-such-account')
        self.assertEqual(response.status_code, 200)
        self.assertIn('No accounts match', response.get_data(as_text=True))

        response = self.client.get('/admin/users?q=paged&page=2')
        self.assertEqual(response.status_code, 200)
        second_page = response.get_data(as_text=True)
        self.assertIn('paged04', second_page)
        self.assertIn('paged00', second_page)

    def test_audit_log_records_and_renders_actions(self):
        self._login_admin()
        self.client.post('/admin/users/new', data={
            'username': 'audited',
            'email': 'audited@example.test',
            'password': 'brand-new-pass',
            'confirm_password': 'brand-new-pass',
        })
        response = self.client.get('/admin/audit')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('user', html)
        self.assertIn('create', html)

    # --------------------------------------------------------------- deployment
    def test_readyz_reports_missing_required_columns(self):
        with self.app.app_context():
            db.session.execute(db.text('ALTER TABLE user DROP COLUMN is_admin'))
            db.session.commit()
        response = self.client.get('/readyz')
        payload = response.get_json()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(payload['database']['ok'])
        self.assertEqual(
            payload['database']['missing_columns'], ['user.is_admin']
        )


if __name__ == '__main__':
    unittest.main()
