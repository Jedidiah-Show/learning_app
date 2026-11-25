"""Coverage and behaviour tests for the learner-owned data registry."""

import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

import sqlalchemy as sa

from app import create_app, db
from app.models import (
    AdminAuditLog, CommunityPost, CommunityReply, GeminiUsageBucket,
    LessonBookmark, MLSpecializationLessonCompletion, Submission,
    TutorConversation, User, utcnow,
)
from app.services.account_data import (
    DELETE_ON_RESET, RETAIN_ON_RESET, TOMBSTONE_ON_RESET, USER_OWNED_MODELS,
    owner_column, purge_user_data, reset_profile_counters,
)


class AccountDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
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

    @staticmethod
    def _user(username):
        return User(
            username=username,
            email=f'{username}@example.test',
            password_hash='not-used',
        )

    @staticmethod
    def _values_for(model, user_id, tag):
        """Build a valid-ish row for any user-owned model."""
        values = {}
        owner = owner_column(model)
        for column in model.__table__.columns:
            if column.name == owner.name:
                values[column.name] = user_id
            elif (
                column.primary_key
                and isinstance(column.type, sa.Integer)
                and column.autoincrement is not False
            ):
                continue
            elif isinstance(column.type, sa.Enum):
                values[column.name] = column.type.enums[0]
            elif isinstance(column.type, sa.LargeBinary):
                values[column.name] = b'test'
            elif isinstance(column.type, sa.DateTime):
                values[column.name] = utcnow()
            elif isinstance(column.type, sa.Date):
                values[column.name] = date.today()
            elif isinstance(column.type, sa.Boolean):
                values[column.name] = False
            elif isinstance(column.type, sa.Integer):
                values[column.name] = 1
            elif isinstance(column.type, sa.Float):
                values[column.name] = 1.0
            elif isinstance(column.type, sa.String):
                values[column.name] = f'{tag}-{column.name}'
        return values

    def test_registry_covers_every_user_owned_model_in_schema(self):
        """A new table with a learner FK must join the registry or fail here."""
        registered = {model.__tablename__ for model in USER_OWNED_MODELS}
        self.assertEqual(len(registered), len(USER_OWNED_MODELS))
        with self.app.app_context():
            schema_owned = set()
            for mapper in db.Model.registry.mappers:
                for column in mapper.columns:
                    if column.name not in ('user_id', 'learner_id'):
                        continue
                    if any(
                        foreign_key.target_fullname == 'user.id'
                        for foreign_key in column.foreign_keys
                    ):
                        schema_owned.add(mapper.local_table.name)
                        break
        self.assertEqual(schema_owned - registered, set())
        self.assertEqual(schema_owned, registered - {'admin_audit_log'})
        self.assertNotIn('admin_audit_log', {m.__tablename__ for m in DELETE_ON_RESET})

    def test_purge_deletes_every_registered_row_for_one_user_only(self):
        with self.app.app_context():
            first = self._user('first')
            second = self._user('second')
            db.session.add_all([first, second])
            db.session.commit()
            for model in DELETE_ON_RESET:
                db.session.add_all([
                    model(**self._values_for(model, first.id, f'a-{model.__tablename__}')),
                    model(**self._values_for(model, second.id, f'b-{model.__tablename__}')),
                ])
            db.session.commit()

            summary = purge_user_data(first.id)
            db.session.commit()
            self.assertEqual(
                set(summary['removed']),
                {model.__tablename__ for model in DELETE_ON_RESET},
            )
            for model in DELETE_ON_RESET:
                with self.subTest(model=model.__tablename__):
                    self.assertEqual(
                        db.session.query(model).filter(
                            owner_column(model) == first.id
                        ).count(),
                        0,
                    )
                    self.assertEqual(
                        db.session.query(model).filter(
                            owner_column(model) == second.id
                        ).count(),
                        1,
                    )

    def test_purge_tombstones_community_rows_and_is_idempotent(self):
        with self.app.app_context():
            first = self._user('author')
            second = self._user('other')
            db.session.add_all([first, second])
            db.session.commit()
            for user_id in (first.id, second.id):
                db.session.add(CommunityPost(
                    user_id=user_id, topic='general',
                    title=f'post-{user_id}', body='body',
                ))
            db.session.commit()
            for post in CommunityPost.query.all():
                db.session.add(CommunityReply(
                    user_id=post.user_id, post_id=post.id,
                    body=f'reply-{post.user_id}',
                ))
            db.session.commit()

            first_posts = CommunityPost.query.filter_by(user_id=first.id).all()
            first_replies = CommunityReply.query.filter_by(user_id=first.id).all()
            summary = purge_user_data(first.id)
            db.session.commit()
            for row in first_posts + first_replies:
                self.assertIsNotNone(row.deleted_at)
            for model in TOMBSTONE_ON_RESET:
                self.assertEqual(summary['removed'][model.__tablename__], 1)
            self.assertTrue(all(
                row.deleted_at is None
                for row in CommunityPost.query.filter_by(user_id=second.id).all()
                + CommunityReply.query.filter_by(user_id=second.id).all()
            ))

            second_summary = purge_user_data(first.id)
            self.assertNotIn('community_post', second_summary['removed'])
            self.assertNotIn('community_reply', second_summary['removed'])

    def test_reset_profile_counters_clears_streak_state(self):
        with self.app.app_context():
            user = self._user('streaky')
            user.streak = 9
            user.longest_streak = 14
            user.last_study_date = date.today()
            user.subjects_configured = True
            reset_profile_counters(user)
            self.assertEqual(user.streak, 0)
            self.assertEqual(user.longest_streak, 0)
            self.assertIsNone(user.last_study_date)
            self.assertFalse(user.subjects_configured)

    def test_reset_account_removes_all_learner_content(self):
        self.client.post('/register', data={
            'username': 'learner',
            'email': 'learner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Learner',
        }, follow_redirects=True)
        with self.app.app_context():
            user = User.query.one()
            user.streak = 7
            user.longest_streak = 11
            user.last_study_date = date.today()
            user.subjects_configured = True
            for model in (
                MLSpecializationLessonCompletion, Submission, TutorConversation,
                LessonBookmark,
            ):
                db.session.add(model(**self._values_for(
                    model, user.id, f'reset-{model.__tablename__}'
                )))
            db.session.add(GeminiUsageBucket(
                user_id=user.id, window='day',
                bucket_start=datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
                request_count=4,
            ))
            db.session.add(AdminAuditLog(
                admin_user_id=user.id, action='test', detail='keep me',
            ))
            db.session.add(CommunityPost(
                user_id=user.id, topic='general', title='post', body='body',
            ))
            db.session.commit()

        with patch(
            'app.routes.auth._run_calendar_cleanup', return_value=(True, None)
        ), patch(
            'app.google_calendar.revoke_authorization', return_value=True
        ):
            response = self.client.post('/account/reset', json={
                'current_password': 'secure-pass-123',
            })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()['status'], 'success')
        self.assertEqual(self.client.get('/profile').status_code, 200)

        with self.app.app_context():
            user = User.query.one()
            self.assertEqual(user.streak, 0)
            self.assertEqual(user.longest_streak, 0)
            self.assertIsNone(user.last_study_date)
            self.assertFalse(user.subjects_configured)
            self.assertEqual(user.auth_version, 1)
            self.assertIsNone(user.google_access_token)
            self.assertIsNone(user.google_refresh_token)
            self.assertEqual(GeminiUsageBucket.query.count(), 1)
            self.assertEqual(AdminAuditLog.query.count(), 1)
            for model in (
                MLSpecializationLessonCompletion, Submission, TutorConversation,
                LessonBookmark,
            ):
                with self.subTest(model=model.__tablename__):
                    self.assertEqual(model.query.count(), 0)
            post = CommunityPost.query.one()
            self.assertIsNotNone(post.deleted_at)
            self.assertEqual(CommunityReply.query.count(), 0)

    def test_delete_account_removes_all_registered_rows(self):
        self.client.post('/register', data={
            'username': 'deleteme',
            'email': 'deleteme@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': 'Delete Me',
        }, follow_redirects=True)
        with self.app.app_context():
            user = User.query.one()
            db.session.add(MLSpecializationLessonCompletion(
                **self._values_for(
                    MLSpecializationLessonCompletion, user.id, 'delete'
                )
            ))
            db.session.add(LessonBookmark(
                **self._values_for(LessonBookmark, user.id, 'delete')
            ))
            db.session.add(CommunityPost(
                user_id=user.id, topic='general', title='post', body='body',
            ))
            db.session.commit()

        with patch(
            'app.routes.auth._run_calendar_cleanup', return_value=(True, None)
        ), patch(
            'app.google_calendar.revoke_authorization', return_value=True
        ):
            response = self.client.post('/account/delete', json={
                'current_password': 'secure-pass-123',
            })
        self.assertEqual(response.status_code, 200, response.get_json())
        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)
            self.assertEqual(MLSpecializationLessonCompletion.query.count(), 0)
            self.assertEqual(LessonBookmark.query.count(), 0)
            self.assertEqual(CommunityPost.query.count(), 0)

    def test_retained_tables_are_not_purged(self):
        with self.app.app_context():
            user = self._user('retained')
            db.session.add(user)
            db.session.commit()
            self.assertEqual(
                {model.__tablename__ for model in RETAIN_ON_RESET},
                {'gemini_usage_bucket', 'admin_audit_log', 'ai_usage_record',
                 'skill_verification'},
            )
            summary = purge_user_data(user.id)
            self.assertEqual(summary['removed'], {})
            self.assertEqual(
                set(summary['retained']),
                {model.__tablename__ for model in RETAIN_ON_RESET},
            )


if __name__ == '__main__':
    unittest.main()
