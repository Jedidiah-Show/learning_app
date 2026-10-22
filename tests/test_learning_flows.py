import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, db
from app.curriculum import get_subject_curriculum
from app.gemini import generate_json
from app.models import (
    CalendarEvent, GeminiUsageBucket, LearningProject, Progress,
    ProficiencyTest, Quiz, StudySession, SubjectCurriculum, User,
    UserSubjectConfig,
)


class LearningFlowTests(unittest.TestCase):
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

    def register(self, username, proficiency='Novice'):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        return self.client.post('/subject-config', data={
            f'proficiency_{subject["id"]}': proficiency
            for subject in self.app.config['APP_CONFIG']['subjects']
        }, follow_redirects=True)

    def complete_day(self, day):
        lessons = self.client.get(f'/api/lessons/daily/{day}')
        self.assertEqual(lessons.status_code, 200)
        for entry in lessons.get_json()['subjects']:
            result = self.client.post('/api/lessons/complete', json={
                'lesson_id': entry['lesson']['lesson_id'],
                'time_spent_minutes': 30,
            })
            self.assertEqual(result.status_code, 200)

    def test_signed_out_users_are_required_to_sign_in(self):
        response = self.client.get('/api/progress/dashboard')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'error': 'Authentication required'})

    def test_login_without_password_returns_regular_auth_failure(self):
        self.register('missingpassword')
        self.client.post('/logout')
        response = self.client.post('/login', data={'username': 'missingpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)

    def test_production_requires_a_stable_secret_key(self):
        with patch.dict(os.environ, {'APP_ENV': 'production'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
                create_app()

    def test_login_normalizes_email_case(self):
        self.register('emailcase')
        self.client.post('/logout')
        response = self.client.post('/login', data={
            'username': 'EMAILCASE@EXAMPLE.TEST',
            'password': 'secure-pass-123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/')

    def test_calendar_outage_does_not_prevent_account_deletion(self):
        self.register('deletewithcalendaroutage')
        with self.app.app_context():
            user = User.query.filter_by(
                username='deletewithcalendaroutage'
            ).one()
            user.google_access_token = 'expired-token'
            db.session.add(CalendarEvent(
                user_id=user.id,
                event_id='event-to-delete',
                title='Study session',
                start_time=__import__('datetime').datetime(2030, 1, 1),
                end_time=__import__('datetime').datetime(2030, 1, 1, 1),
                synced_to_google=True,
            ))
            db.session.commit()
        with patch(
            'app.routes.calendar._calendar_service',
            side_effect=RuntimeError('Calendar unavailable'),
        ):
            response = self.client.post('/account/delete', data={
                'current_password': 'secure-pass-123',
            })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(
                username='deletewithcalendaroutage'
            ).first())

    def test_schedule_rejects_duplicate_block_names(self):
        self.register('duplicateschedule')
        response = self.client.post('/api/admin/schedule', json={
            'daily_blocks': [
                {'name': 'study', 'start_time': '09:00', 'end_time': '10:00'},
                {'name': 'study', 'start_time': '11:00', 'end_time': '12:00'},
            ],
        })
        self.assertEqual(response.status_code, 400)

    def test_gemini_requests_are_limited_per_authenticated_user(self):
        from app.gemini import GeminiRateLimitExceeded, _record_user_request
        self.register('geminilimit')
        with self.app.app_context():
            user_id = User.query.filter_by(username='geminilimit').one().id
        with self.app.test_request_context('/'):
            from flask import session
            session['_user_id'] = str(user_id)
            session['_fresh'] = True
            for _ in range(10):
                _record_user_request()
            with self.assertRaises(GeminiRateLimitExceeded):
                _record_user_request()
        with self.app.app_context():
            self.assertEqual(
                GeminiUsageBucket.query.filter_by(
                    user_id=user_id, window='minute'
                ).one().request_count,
                10,
            )

    def test_gemini_quota_errors_return_retryable_http_429(self):
        from app.gemini import GeminiRateLimitExceeded

        self.register('gemini429')
        lesson = self.client.get('/api/lessons/daily/1').get_json()['subjects'][0]
        with patch(
            'app.routes.lessons.generate_json',
            side_effect=GeminiRateLimitExceeded(17),
        ):
            response = self.client.post('/api/lessons/ask', json={
                'lesson_id': lesson['lesson']['lesson_id'],
                'question': 'Can you explain this lesson?',
            })
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '17')

    def test_generated_cache_insert_recovers_from_unique_collision(self):
        from app.db_utils import add_or_get
        self.register('cachecollision')
        with self.app.app_context():
            quiz = Quiz(
                quiz_id='shared-cache-entry',
                quiz_type='daily',
                day_number=1,
                questions='[]',
            )
            db.session.add(quiz)
            db.session.commit()
            recovered = add_or_get(
                Quiz,
                Quiz(
                    quiz_id='shared-cache-entry',
                    quiz_type='daily',
                    day_number=1,
                    questions='[]',
                ),
                quiz_id='shared-cache-entry',
            )
            self.assertEqual(recovered.id, quiz.id)

    def test_dashboard_streak_uses_the_requested_timezone(self):
        from datetime import datetime, timezone
        from app.routes import progress as progress_routes

        self.register('localstreak')
        with self.app.app_context():
            user = User.query.filter_by(username='localstreak').one()
            db.session.add_all([
                Progress(
                    user_id=user.id, subject_id='python', day_number=1,
                    completed=True,
                    completion_date=datetime(2026, 2, 2, 23, 30, tzinfo=timezone.utc),
                ),
                Progress(
                    user_id=user.id, subject_id='python', day_number=2,
                    completed=True,
                    completion_date=datetime(2026, 2, 3, 0, 30, tzinfo=timezone.utc),
                ),
            ])
            db.session.commit()

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                now = cls(2026, 2, 3, 1, 0, tzinfo=timezone.utc)
                return now.astimezone(tz) if tz else now.replace(tzinfo=None)

        with patch.object(progress_routes, 'datetime', FrozenDateTime):
            response = self.client.get(
                '/api/progress/dashboard',
                headers={'X-Timezone': 'America/Los_Angeles'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['study_streak_days'], 1)

    def test_revisiting_completed_lesson_records_additional_study_time(self):
        self.register('reviewtimetracking')
        lessons = self.client.get('/api/lessons/daily/1').get_json()['subjects']
        lesson_id = lessons[0]['lesson']['lesson_id']
        for minutes in (20, 10):
            response = self.client.post('/api/lessons/complete', json={
                'lesson_id': lesson_id,
                'time_spent_minutes': minutes,
            })
            self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            user = User.query.filter_by(username='reviewtimetracking').one()
            self.assertEqual(
                StudySession.query.filter_by(
                    user_id=user.id, session_type='lesson'
                ).with_entities(db.func.sum(StudySession.duration_minutes)).scalar(),
                30,
            )

    def test_quiz_submission_rejects_missing_answers(self):
        self.register('incompletequiz')
        quiz = self.client.get('/api/quizzes/daily/1').get_json()
        response = self.client.post('/api/quizzes/submit', json={
            'quiz_id': quiz['quiz_id'],
            'quiz_type': quiz['quiz_type'],
            'answers': {},
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()['error'],
            'Provide one valid answer for every quiz question',
        )

    def test_account_update_rejects_non_object_json_without_server_error(self):
        self.register('badaccountjson')
        response = self.client.post(
            '/account/update', data='[]', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'error': 'Request body must be an object'})

    def test_gemini_client_uses_configured_model_and_api_key_header(self):
        from unittest.mock import Mock
        with self.app.app_context():
            self.app.config['GEMINI_API_KEY'] = 'test-key-not-a-real-secret'
            response = Mock(ok=True)
            response.json.return_value = {
                'candidates': [{
                    'content': {'parts': [{'text': '{"answer":"ok"}'}]}
                }]
            }
            with patch('app.gemini.requests.post', return_value=response) as post:
                result = generate_json('Return JSON')
        self.assertEqual(result, {'answer': 'ok'})
        self.assertIn('/gemini-3.8-flash:generateContent', post.call_args.args[0])
        self.assertEqual(
            post.call_args.kwargs['headers']['x-goog-api-key'],
            'test-key-not-a-real-secret',
        )
        self.assertEqual(
            post.call_args.kwargs['json']['generationConfig']['thinkingConfig'],
            {'thinkingLevel': 'LOW'},
        )

    def test_gemini_client_reports_provider_rejections_without_exposing_key(self):
        from unittest.mock import Mock
        from app.gemini import GeminiError
        with self.app.app_context():
            self.app.config['GEMINI_API_KEY'] = 'test-key-not-a-real-secret'
            response = Mock(ok=False, status_code=400)
            response.json.return_value = {
                'error': {'message': 'model is unavailable for this API key'}
            }
            with patch('app.gemini.requests.post', return_value=response):
                with self.assertRaisesRegex(GeminiError, 'HTTP 400'):
                    generate_json('Return JSON')

    def test_gemini_older_models_keep_their_default_thinking_config(self):
        from unittest.mock import Mock

        with self.app.app_context():
            self.app.config.update(
                GEMINI_API_KEY='test-key',
                GEMINI_FLASH_MODEL='gemini-2.5-flash',
            )
            response = Mock(ok=True)
            response.json.return_value = {
                'candidates': [{
                    'content': {'parts': [{'text': '{"answer":"ok"}'}]}
                }]
            }
            with patch('app.gemini.requests.post', return_value=response) as post:
                self.assertEqual(generate_json('Return JSON'), {'answer': 'ok'})
        self.assertNotIn(
            'thinkingConfig',
            post.call_args.kwargs['json']['generationConfig'],
        )

    def test_gemini_client_reports_generation_timeouts_clearly(self):
        from requests import ReadTimeout
        from app.gemini import GeminiError

        with self.app.app_context():
            self.app.config['GEMINI_API_KEY'] = 'test-key'
            with patch(
                'app.gemini.requests.post',
                side_effect=ReadTimeout('provider took too long'),
            ):
                with self.assertRaisesRegex(GeminiError, 'timed out while generating'):
                    generate_json('Return JSON')

    def test_gemini_retries_rate_limited_pro_with_flash(self):
        from unittest.mock import Mock
        with self.app.app_context():
            self.app.config.update(
                GEMINI_API_KEY='test-key',
                GEMINI_PRO_MODEL='gemini-pro-test',
                GEMINI_FLASH_MODEL='gemini-flash-test',
            )
            limited = Mock(ok=False, status_code=429)
            limited.json.return_value = {'error': {'message': 'quota exceeded'}}
            success = Mock(ok=True)
            success.json.return_value = {
                'candidates': [{
                    'content': {'parts': [{'text': '{"answer":"ok"}'}]}
                }]
            }
            with patch(
                'app.gemini.requests.post', side_effect=[limited, success]
            ) as post:
                result = generate_json('Return JSON', model='pro')
        self.assertEqual(result, {'answer': 'ok'})
        self.assertEqual(post.call_count, 2)
        self.assertIn('gemini-pro-test:generateContent', post.call_args_list[0].args[0])
        self.assertIn('gemini-flash-test:generateContent', post.call_args_list[1].args[0])

    def test_offline_proficiency_assessment_has_twenty_distinct_balanced_questions(self):
        from app.routes.main import generate_proficiency_questions
        subject = self.app.config['APP_CONFIG']['subjects'][0]
        with self.app.app_context():
            questions = generate_proficiency_questions(
                subject, self.app.config['APP_CONFIG'], 'Intermediate'
            )
        self.assertEqual(len(questions), 20)
        self.assertEqual(len({item['question'] for item in questions}), 20)
        self.assertEqual(
            [sum(item['difficulty'] == level for item in questions) for level in range(1, 6)],
            [4, 4, 4, 4, 4],
        )
        self.assertEqual(
            {item['correct'] for item in questions},
            {0, 1, 2, 3},
        )

    def test_google_calendar_oauth_uses_configured_callback_and_saves_tokens(self):
        from datetime import datetime, timezone
        from types import SimpleNamespace
        from unittest.mock import Mock
        self.register('oauthlearner')
        self.app.config.update(
            GOOGLE_CLIENT_ID='client-id',
            GOOGLE_CLIENT_SECRET='client-secret',
            GOOGLE_REDIRECT_URI='http://localhost/api/calendar/oauth2callback',
        )
        fake_flow = Mock()
        fake_flow.authorization_url.return_value = (
            'https://accounts.google.test/authorize', 'oauth-state'
        )
        fake_flow.credentials = SimpleNamespace(
            token='access-token',
            refresh_token='refresh-token',
            expiry=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        with patch(
            'google_auth_oauthlib.flow.Flow.from_client_config',
            return_value=fake_flow,
        ) as from_client_config:
            auth_response = self.client.get('/api/calendar/auth/google')
            self.assertEqual(auth_response.status_code, 302)
            self.assertEqual(auth_response.headers['Location'], 'https://accounts.google.test/authorize')
            self.assertEqual(
                from_client_config.call_args.kwargs['scopes'],
                ['https://www.googleapis.com/auth/calendar.events'],
            )
            self.assertEqual(fake_flow.redirect_uri, 'http://localhost/api/calendar/oauth2callback')
            callback = self.client.get(
                '/api/calendar/oauth2callback?state=oauth-state&code=authorization-code'
            )
        self.assertEqual(callback.status_code, 302)
        fake_flow.fetch_token.assert_called_once_with(code='authorization-code')
        with self.app.app_context():
            user = User.query.filter_by(username='oauthlearner').one()
            self.assertEqual(user.google_access_token, 'access-token')
            self.assertEqual(user.google_refresh_token, 'refresh-token')
            self.assertIsNotNone(user.token_expiry)

    def test_google_calendar_sync_uses_saved_credentials_and_marks_events(self):
        from unittest.mock import Mock
        from app.models import CalendarEvent
        self.register('calendarsynctest')
        self.client.post('/api/calendar/schedule', json={'day_number': 1})
        self.app.config.update(
            GOOGLE_CLIENT_ID='client-id',
            GOOGLE_CLIENT_SECRET='client-secret',
        )
        with self.app.app_context():
            user = User.query.filter_by(username='calendarsynctest').one()
            user.google_access_token = 'access-token'
            db.session.commit()

        created = []
        event_resource = Mock()

        def record_insert(**kwargs):
            created.append(kwargs)
            return Mock(execute=Mock(return_value={'id': f'google-event-{len(created)}'}))

        event_resource.insert.side_effect = record_insert
        service = Mock()
        service.events.return_value = event_resource
        with patch('google.oauth2.credentials.Credentials') as credentials:
            credentials.return_value.expired = False
            with patch('googleapiclient.discovery.build', return_value=service):
                result = self.client.post('/api/calendar/sync', json={'day_number': 1})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()['events_created'], 2)
        self.assertEqual(len(created), 2)
        self.assertTrue(all(entry['calendarId'] == 'primary' for entry in created))
        with self.app.app_context():
            events = CalendarEvent.query.order_by(CalendarEvent.id).all()
            self.assertTrue(all(event.synced_to_google for event in events))
            self.assertTrue(all(event.event_id.startswith('google-event-') for event in events))

    def test_schedule_changes_update_and_remove_synced_calendar_events(self):
        from datetime import datetime, timezone
        from unittest.mock import Mock
        self.register('calendarreconcile')
        self.app.config.update(
            GOOGLE_CLIENT_ID='client-id',
            GOOGLE_CLIENT_SECRET='client-secret',
        )
        with self.app.app_context():
            user = User.query.filter_by(username='calendarreconcile').one()
            user.google_access_token = 'access-token'
            db.session.add_all([
                CalendarEvent(
                    user_id=user.id, event_id='google-morning',
                    title='[Learning App] Morning Session - Day 1',
                    start_time=datetime(2030, 1, 1, 11, tzinfo=timezone.utc).replace(tzinfo=None),
                    end_time=datetime(2030, 1, 1, 13, tzinfo=timezone.utc).replace(tzinfo=None),
                    day_number=1, block_name='morning', time_zone='UTC',
                    synced_to_google=True,
                ),
                CalendarEvent(
                    user_id=user.id, event_id='google-evening',
                    title='[Learning App] Evening Session - Day 1',
                    start_time=datetime(2030, 1, 1, 18, tzinfo=timezone.utc).replace(tzinfo=None),
                    end_time=datetime(2030, 1, 1, 20, tzinfo=timezone.utc).replace(tzinfo=None),
                    day_number=1, block_name='evening', time_zone='UTC',
                    synced_to_google=True,
                ),
            ])
            db.session.commit()

        events_resource = Mock()
        service = Mock()
        service.events.return_value = events_resource
        events_resource.update.return_value.execute.return_value = {}
        events_resource.delete.return_value.execute.return_value = {}
        with patch('google.oauth2.credentials.Credentials') as credentials:
            credentials.return_value.expired = False
            with patch('googleapiclient.discovery.build', return_value=service):
                response = self.client.post('/api/admin/schedule', json={
                    'daily_blocks': [{
                        'name': 'morning',
                        'start_time': '09:00',
                        'end_time': '10:30',
                    }],
                })
        self.assertEqual(response.status_code, 200)
        events_resource.update.assert_called_once()
        events_resource.delete.assert_called_once_with(
            calendarId='primary', eventId='google-evening'
        )
        with self.app.app_context():
            events = CalendarEvent.query.all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].start_time.isoformat(), '2030-01-01T09:00:00')
            self.assertEqual(events[0].end_time.isoformat(), '2030-01-01T10:30:00')

    def test_failed_calendar_reconciliation_is_persisted_for_retry(self):
        from datetime import datetime, timezone
        from unittest.mock import Mock

        self.register('calendarretry')
        self.app.config.update(
            GOOGLE_CLIENT_ID='client-id',
            GOOGLE_CLIENT_SECRET='client-secret',
        )
        with self.app.app_context():
            user = User.query.filter_by(username='calendarretry').one()
            user.google_access_token = 'access-token'
            db.session.add(CalendarEvent(
                user_id=user.id,
                event_id='google-retry',
                title='[Learning App] Morning Session - Day 1',
                start_time=datetime(2030, 1, 1, 11),
                end_time=datetime(2030, 1, 1, 13),
                day_number=1,
                block_name='morning',
                time_zone='UTC',
                synced_to_google=True,
            ))
            db.session.commit()

        blocks = [{
            'name': 'morning',
            'start_time': '09:00',
            'end_time': '10:30',
        }]
        with patch(
            'app.routes.calendar._calendar_service',
            side_effect=RuntimeError('temporary outage'),
        ):
            failed = self.client.post(
                '/api/admin/schedule', json={'daily_blocks': blocks}
            )
        self.assertEqual(failed.status_code, 502)
        with self.app.app_context():
            event = CalendarEvent.query.one()
            self.assertTrue(event.sync_pending)
            self.assertEqual(event.start_time.isoformat(), '2030-01-01T09:00:00')

        service = Mock()
        service.events.return_value.update.return_value.execute.return_value = {}
        with patch(
            'app.routes.calendar._calendar_service', return_value=service
        ):
            retried = self.client.post(
                '/api/admin/schedule', json={'daily_blocks': blocks}
            )
        self.assertEqual(retried.status_code, 200)
        service.events.return_value.update.assert_called_once()
        with self.app.app_context():
            self.assertFalse(CalendarEvent.query.one().sync_pending)

    def test_unlocking_and_weekly_quiz_follow_completed_lessons(self):
        self.register('learner')
        locked = self.client.get('/api/lessons/daily/2')
        self.assertEqual(locked.status_code, 403)

        self.complete_day(1)
        self.assertEqual(self.client.get('/api/lessons/daily/2').status_code, 200)
        for day in range(2, 8):
            self.complete_day(day)

        weekly = self.client.get('/api/quizzes/weekly/1')
        self.assertEqual(weekly.status_code, 200)
        payload = weekly.get_json()
        self.assertGreater(len(payload['questions']), 0)
        self.assertTrue(all('correct' not in question for question in payload['questions']))
        submitted = self.client.post('/api/quizzes/submit', json={
            'quiz_id': payload['quiz_id'],
            'quiz_type': payload['quiz_type'],
            'answers': {
                question['id']: 0
                for question in payload['questions']
            },
        })
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(
            self.client.get('/api/progress/dashboard').get_json()['next_unlocked_day'],
            7,
        )
        project_definition = {
            'title': 'Integrated weekly project',
            'brief': 'Build an artifact using this week’s topics.',
            'learning_goals': ['Combine concepts.'],
            'deliverables': ['Artifact', 'Explanation'],
            'subjects': ['Python'],
            'rubric': [
                {'criterion': 'Application', 'weight': 50},
                {'criterion': 'Evidence', 'weight': 50},
            ],
        }
        with patch('app.routes.projects.generate_json', return_value=project_definition):
            project = self.client.get('/api/projects/weekly/1')
        self.assertEqual(project.status_code, 200)
        project_payload = project.get_json()
        self.assertIn('deliverables', project_payload['project'])
        self.assertTrue(project_payload['is_ai_generated'])
        self.assertFalse(project_payload['completed'])
        with patch('app.routes.projects.generate_json', side_effect=[
            project_definition,
            {
                'score': 88,
                'summary': 'The artifact applies the week’s ideas.',
                'strengths': ['Clear application.'],
                'gaps': [],
                'next_steps': ['Add a second test case.'],
                'rubric_scores': [],
            },
        ]):
            project_submission = self.client.post(
                '/api/projects/weekly/1/submit',
                json={'submission': 'A substantial project artifact. ' * 4},
            )
        self.assertEqual(project_submission.status_code, 200)
        self.assertEqual(project_submission.get_json()['evaluation']['score'], 88)
        with self.app.app_context():
            saved_project = LearningProject.query.one()
            self.assertTrue(saved_project.completed)
        self.assertEqual(
            self.client.get('/api/progress/dashboard').get_json()['next_unlocked_day'],
            8,
        )
        self.assertEqual(self.client.get('/api/lessons/daily/8').status_code, 200)
        with self.app.app_context():
            user_id = User.query.filter_by(username='learner').first().id
            Progress.query.filter_by(user_id=user_id).delete()
            db.session.commit()
        self.assertEqual(
            self.client.post('/api/quizzes/submit', json={
                'quiz_id': payload['quiz_id'],
                'quiz_type': payload['quiz_type'],
                'answers': {
                    question['id']: 0
                    for question in payload['questions']
                },
            }).status_code,
            409,
        )

    def test_initial_proficiency_assessment_blocks_the_curriculum(self):
        self.register('assessedlearner')
        questions = [{
            'question': f'Python diagnostic question {index + 1}',
            'options': ['Correct', 'Incorrect', 'Incorrect', 'Incorrect'],
            'correct_index': 0,
            'explanation': 'The first option is correct.',
            'difficulty': index // 4 + 1,
            'topic': 'Python',
        } for index in range(20)]
        for index, question in enumerate(questions):
            question['options'] = [
                f'Option {option} for question {index + 1}' for option in range(4)
            ]
        evaluation = {
            'summary': 'Strong result.',
            'strengths': ['Correctly applied core concepts.'],
            'gaps': [],
            'next_steps': ['Continue into advanced practice.'],
        }
        with patch('app.routes.main.generate_json', side_effect=[
            {'questions': questions},
            evaluation,
        ]):
            config_response = self.client.post('/subject-config', data={
                **{
                    f'proficiency_{subject["id"]}': 'Novice'
                    for subject in self.app.config['APP_CONFIG']['subjects']
                },
                'proficiency_python': 'Beginner',
            }, follow_redirects=True)
            self.assertEqual(config_response.status_code, 200)
            self.assertEqual(
                self.client.get('/api/progress/dashboard').status_code,
                403,
            )
            tests_page = self.client.get('/proficiency-tests')
            self.assertEqual(tests_page.status_code, 200)
            with self.app.app_context():
                test = ProficiencyTest.query.one()
                test_id = test.id
                self.assertEqual(test.get_questions()[0]['question'], questions[0]['question'])
            answers = {f'q{index}': '0' for index in range(20)}
            result = self.client.post(
                f'/proficiency-test/{test_id}', data=answers, follow_redirects=True
            )
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Strong result.', result.data)
        with self.app.app_context():
            profile = UserSubjectConfig.query.filter_by(subject_id='python').one()
            self.assertEqual(profile.acquired_proficiency, 'Expert')
            self.assertTrue(profile.tested)
        self.assertEqual(self.client.get('/api/progress/dashboard').status_code, 200)

    def test_gemini_curriculum_lessons_tutor_and_quizzes(self):
        self.register('geminilearner')
        ai_plan = {'days': [
            {'day': day, 'topic': f'AI topic {day}', 'objective': f'Advanced goal {day}', 'difficulty': 4}
            for day in range(1, 91)
        ]}
        with self.app.app_context():
            with patch('app.curriculum.generate_json', return_value=ai_plan):
                curriculum, days = get_subject_curriculum(
                    User.query.filter_by(username='geminilearner').first(),
                    self.app.config['APP_CONFIG']['subjects'][0],
                    self.app.config['APP_CONFIG'],
                )
            self.assertTrue(curriculum.is_ai_generated)
            self.assertEqual(days[0]['topic'], 'AI topic 1')
            db.session.commit()

        generated_lesson = {
            'title': 'Generated topic lesson',
            'objectives': ['Apply the concept.'],
            'content': {
                'overview': 'A generated lesson overview.',
                'theory_sections': [
                    {'heading': heading, 'content': f'A clear explanation of {heading.lower()}.'}
                    for heading in (
                        'Overview', 'Core Concepts',
                        'Guided Walkthrough', 'Practical Application',
                    )
                ],
                'code_examples': [],
                'pitfalls': [],
                'self_checks': [{
                    'question': 'Which option is correct?',
                    'options': ['First', 'Second', 'Third', 'Fourth'],
                    'correct_index': 0,
                    'explanation': 'This follows from the lesson.',
                }],
                'summary': {'heading': 'Summary', 'points': ['Apply it.']},
                'exercises': [],
                'key_terms': ['concept'],
            },
        }
        with patch('app.routes.lessons.generate_json', return_value=generated_lesson):
            daily = self.client.get('/api/lessons/daily/1')
        self.assertEqual(daily.status_code, 200)
        lesson = daily.get_json()['subjects'][0]['lesson']
        self.assertTrue(lesson['is_ai_generated'])
        self.assertEqual(lesson['title'], 'Generated topic lesson')

        with patch('app.routes.lessons.generate_json', return_value={'answer': 'Here is a simpler explanation.'}):
            answer = self.client.post('/api/lessons/ask', json={
                'lesson_id': lesson['lesson_id'],
                'question': 'Can you explain this more simply?',
            })
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.get_json()['answer'], 'Here is a simpler explanation.')

        subjects = self.app.config['APP_CONFIG']['subjects']
        generated_questions = {'questions': [
            {
                'subject_id': subject['id'],
                'question': f'Question {number} for {subject["id"]}',
                'options': ['A', 'B', 'C', 'D'],
                'correct_index': 0,
                'explanation': 'The lesson supports this answer.',
            }
            for subject in subjects for number in range(2)
        ]}
        with patch('app.routes.quizzes.generate_json', return_value=generated_questions):
            quiz_response = self.client.get('/api/quizzes/daily/1')
        self.assertEqual(quiz_response.status_code, 200)
        quiz_data = quiz_response.get_json()
        self.assertTrue(quiz_data['is_ai_generated'])
        self.assertEqual(len(quiz_data['questions']), 10)
        with self.app.app_context():
            quiz = Quiz.query.filter_by(quiz_id=quiz_data['quiz_id']).one()
            correct_answers = {
                question['id']: question['correct'] for question in quiz.get_questions()
            }
        with patch('app.routes.quizzes.generate_json', return_value={
            'summary': 'Excellent work.',
            'strengths': ['Strong recall.'],
            'gaps': [],
            'next_steps': ['Keep practicing.'],
        }):
            evaluated = self.client.post('/api/quizzes/submit', json={
                'quiz_id': quiz_data['quiz_id'],
                'quiz_type': 'daily',
                'answers': correct_answers,
            })
        self.assertEqual(evaluated.status_code, 200)
        self.assertEqual(evaluated.get_json()['evaluation']['summary'], 'Excellent work.')

    def test_progress_and_completions_are_isolated_per_account(self):
        self.register('alice')
        self.complete_day(1)
        completed = self.client.get('/api/lessons/daily/1').get_json()
        self.assertTrue(all(entry['completed'] for entry in completed['subjects']))
        self.client.post('/logout')
        self.register('bob')

        lessons = self.client.get('/api/lessons/daily/1').get_json()
        self.assertTrue(all(not entry['completed'] for entry in lessons['subjects']))
        progress = self.client.get('/api/progress/dashboard').get_json()
        self.assertEqual(progress['days_completed'], 0)

    def test_daily_quiz_cache_is_isolated_per_account(self):
        self.register('quizalice')
        alice_quiz = self.client.get('/api/quizzes/daily/1').get_json()
        self.client.post('/logout')
        self.register('quizbob')
        bob_quiz = self.client.get('/api/quizzes/daily/1').get_json()
        self.assertNotEqual(alice_quiz['quiz_id'], bob_quiz['quiz_id'])

    def test_quiz_submission_attempt_key_returns_saved_result_without_re_evaluation(self):
        self.register('quizretry')
        quiz = self.client.get('/api/quizzes/daily/1').get_json()
        payload = {
            'quiz_id': quiz['quiz_id'],
            'quiz_type': quiz['quiz_type'],
            'attempt_id': 'attempt-1',
            'answers': {
                question['id']: 0
                for question in quiz['questions']
            },
        }
        evaluation = {
            'summary': 'Review the explanations.',
            'strengths': [],
            'gaps': [],
            'next_steps': [],
        }
        with patch(
            'app.routes.quizzes.generate_json', return_value=evaluation
        ) as generate:
            first = self.client.post('/api/quizzes/submit', json=payload)
            retry = self.client.post('/api/quizzes/submit', json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(first.get_json(), retry.get_json())
        self.assertEqual(generate.call_count, 1)
        with self.app.app_context():
            from app.models import QuizResult
            self.assertEqual(QuizResult.query.filter_by(
                attempt_id='attempt-1'
            ).count(), 1)

    def test_disabling_quiz_prevents_submission_of_an_existing_quiz(self):
        self.register('quizdisabled')
        quiz = self.client.get('/api/quizzes/daily/1').get_json()
        preferences = self.client.post('/api/settings/preferences', json={
            'quizzes': {'end_of_day_quiz': {'enabled': False}},
        })
        self.assertEqual(preferences.status_code, 200)
        response = self.client.post('/api/quizzes/submit', json={
            'quiz_id': quiz['quiz_id'],
            'quiz_type': 'daily',
            'answers': {},
        })
        self.assertEqual(response.status_code, 403)

    def test_password_reset_token_is_hashed_expiring_and_single_use(self):
        from werkzeug.security import check_password_hash
        from app.models import PasswordResetToken

        self.register('resetuser')
        raw_token = 'test-reset-token-not-a-credential'
        with patch('app.routes.auth.secrets.token_urlsafe', return_value=raw_token):
            response = self.client.post('/forgot-password', data={
                'email': 'resetuser@example.test',
            })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            stored = PasswordResetToken.query.one()
            self.assertNotEqual(stored.token_hash, raw_token)
            token_id = stored.id
        reset = self.client.post(
            f'/reset-password/{raw_token}',
            data={'password': 'new-secure-pass', 'confirm_password': 'new-secure-pass'},
        )
        self.assertEqual(reset.status_code, 302)
        with self.app.app_context():
            stored = db.session.get(PasswordResetToken, token_id)
            user = User.query.filter_by(username='resetuser').one()
            self.assertIsNotNone(stored.used_at)
            self.assertTrue(check_password_hash(user.password_hash, 'new-secure-pass'))
        reused = self.client.get(f'/reset-password/{raw_token}')
        self.assertEqual(reused.status_code, 302)

    def test_curriculum_length_and_personal_settings_are_isolated(self):
        alice = self.client
        bob = self.app.test_client()
        self.register('alice')
        bob_response = bob.post('/register', data={
            'username': 'bob',
            'email': 'bob@example.test',
            'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(bob_response.status_code, 200)
        bob.post('/subject-config', data={
            f'proficiency_{subject["id"]}': 'Novice'
            for subject in self.app.config['APP_CONFIG']['subjects']
        }, follow_redirects=True)
        alice_date = alice.post('/api/settings/assessment', json={'assessment_date': '2030-06-01'})
        self.assertEqual(alice_date.status_code, 200)
        self.assertEqual(
            alice.post('/api/settings/assessment', json={'assessment_date': 'not-a-date'}).status_code,
            400,
        )
        self.assertEqual(
            alice.get('/api/progress/dashboard').get_json()['assessment_date'],
            '2030-06-01',
        )
        self.assertEqual(
            bob.get('/api/progress/dashboard').get_json()['assessment_date'],
            '2027-01-27',
        )
        self.assertEqual(
            alice.get('/api/progress/dashboard').get_json()['curriculum_days'],
            90,
        )

        alice.post('/api/admin/subjects', json={
            'id': 'alice_track', 'name': 'Alice Track', 'topics': ['Topic A'],
        })
        alice.post('/subject-config', data={
            f'proficiency_{subject["id"]}': 'Novice'
            for subject in self.app.config['APP_CONFIG']['subjects']
        } | {'proficiency_alice_track': 'Novice'}, follow_redirects=True)
        alice.post('/api/admin/schedule', json={
            'daily_blocks': [{'name': 'personal', 'start_time': '09:00', 'end_time': '10:00'}],
        })
        alice_subject_ids = {item['id'] for item in alice.get('/api/admin/subjects').get_json()['subjects']}
        bob_subject_ids = {item['id'] for item in bob.get('/api/admin/subjects').get_json()['subjects']}
        self.assertIn('alice_track', alice_subject_ids)
        self.assertNotIn('alice_track', bob_subject_ids)
        alice.delete('/api/admin/subjects/python')
        self.assertNotIn(
            'python',
            {item['id'] for item in alice.get('/api/admin/subjects').get_json()['subjects']},
        )
        self.assertIn(
            'python',
            {item['id'] for item in bob.get('/api/admin/subjects').get_json()['subjects']},
        )
        self.assertEqual(
            alice.get('/api/admin/schedule').get_json()['daily_blocks'][0]['name'],
            'personal',
        )
        self.assertEqual(
            bob.get('/api/admin/schedule').get_json()['daily_blocks'][0]['name'],
            'morning',
        )

    def test_weekly_quiz_uses_each_users_custom_subjects(self):
        self.register('customlearner')
        response = self.client.post('/api/admin/subjects', json={
            'id': 'custom_track', 'name': 'Custom Track', 'topics': ['Custom topic'],
        })
        self.assertEqual(response.status_code, 200)
        self.client.post('/subject-config', data={
            f'proficiency_{subject["id"]}': 'Novice'
            for subject in self.app.config['APP_CONFIG']['subjects']
        } | {'proficiency_custom_track': 'Novice'}, follow_redirects=True)
        day_one = self.client.get('/api/lessons/daily/1').get_json()
        python_lesson = next(item for item in day_one['subjects'] if item['subject']['id'] == 'python')
        self.assertIn('Python names refer to objects', python_lesson['lesson']['content']['theory_sections'][1]['content'])
        self.assertEqual(self.client.get('/settings').status_code, 200)
        self.assertEqual(self.client.get('/schedule').status_code, 200)
        self.assertEqual(self.client.get(f"/lesson/{python_lesson['lesson']['lesson_id']}").status_code, 200)
        for day in range(1, 8):
            self.complete_day(day)
        weekly = self.client.get('/api/quizzes/weekly/1')
        self.assertEqual(weekly.status_code, 200)
        question_subjects = {question['subject_id'] for question in weekly.get_json()['questions']}
        self.assertIn('custom_track', question_subjects)

    def test_calendar_scheduling_is_bounded_and_idempotent(self):
        self.register('calendarlearner')
        invalid = self.client.post('/api/calendar/schedule', json={'day_number': 91})
        self.assertEqual(invalid.status_code, 400)
        first = self.client.post('/api/calendar/schedule', json={'day_number': 1})
        second = self.client.post('/api/calendar/schedule', json={'day_number': 1})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.get_json()['events_created']), 2)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()['events_created'], [])
        with self.app.app_context():
            self.assertEqual(CalendarEvent.query.count(), 2)

    def test_reset_removes_personalized_curricula_projects_and_calendar_tokens(self):
        self.register('resetlearner')
        with self.app.app_context():
            user = User.query.filter_by(username='resetlearner').one()
            user.google_access_token = 'access-token'
            user.google_refresh_token = 'refresh-token'
            db.session.add(SubjectCurriculum(
                user_id=user.id, subject_id='python', starting_proficiency='Novice',
                plan='[]', source_signature='old-signature',
            ))
            db.session.add(LearningProject(
                user_id=user.id, week_number=1, project='{}', completed=True,
            ))
            db.session.commit()

        response = self.client.post('/account/reset', json={
            'current_password': 'secure-pass-123',
        })
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            user = User.query.filter_by(username='resetlearner').one()
            self.assertEqual(SubjectCurriculum.query.filter_by(user_id=user.id).count(), 0)
            self.assertEqual(LearningProject.query.filter_by(user_id=user.id).count(), 0)
            self.assertIsNone(user.google_access_token)
            self.assertIsNone(user.google_refresh_token)

    def test_reset_deletes_synced_google_events_before_clearing_calendar_data(self):
        from datetime import datetime
        from unittest.mock import Mock
        self.register('resetcalendar')
        self.app.config.update(
            GOOGLE_CLIENT_ID='client-id',
            GOOGLE_CLIENT_SECRET='client-secret',
        )
        with self.app.app_context():
            user = User.query.filter_by(username='resetcalendar').one()
            user.google_access_token = 'access-token'
            db.session.add(CalendarEvent(
                user_id=user.id, event_id='google-reset-event',
                title='Learning session',
                start_time=datetime(2030, 1, 1, 11),
                end_time=datetime(2030, 1, 1, 12),
                day_number=1, block_name='morning', time_zone='UTC',
                synced_to_google=True,
            ))
            db.session.commit()

        events_resource = Mock()
        service = Mock()
        service.events.return_value = events_resource
        events_resource.delete.return_value.execute.return_value = {}
        with patch('google.oauth2.credentials.Credentials') as credentials:
            credentials.return_value.expired = False
            with patch('googleapiclient.discovery.build', return_value=service):
                response = self.client.post('/account/reset', json={
                    'current_password': 'secure-pass-123',
                })
        self.assertEqual(response.status_code, 200)
        events_resource.delete.assert_called_once_with(
            calendarId='primary', eventId='google-reset-event'
        )
        with self.app.app_context():
            user = User.query.filter_by(username='resetcalendar').one()
            self.assertIsNone(user.google_access_token)
            self.assertEqual(CalendarEvent.query.filter_by(user_id=user.id).count(), 0)

    def test_weekly_project_is_regenerated_when_its_source_changes(self):
        from app.routes.projects import _get_or_create_project
        self.register('projectrefresh')
        project_data = {
            'title': 'Updated project',
            'brief': 'Apply the updated subject material.',
            'learning_goals': ['Use the current topics.'],
            'deliverables': ['One working artifact.'],
            'rubric': [{'criterion': 'Application', 'weight': 100}],
        }
        with self.app.app_context():
            user = User.query.filter_by(username='projectrefresh').one()
            config = self.app.config['APP_CONFIG']
            subjects = config['subjects'][:1]
            original = _get_or_create_project(
                user, config, 1, subjects, 1, 7
            )
            original_signature = original.source_signature
            original_id = original.id
            db.session.commit()
            subjects[0]['description'] = 'Changed subject source'
            with patch(
                'app.routes.projects.generate_json', return_value=project_data
            ) as generate:
                updated = _get_or_create_project(
                    user, config, 1, subjects, 1, 7
                )
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(updated.id, original_id)
            self.assertNotEqual(updated.source_signature, original_signature)
            self.assertEqual(updated.get_project()['title'], 'Updated project')

    def test_malformed_progress_json_returns_bad_request(self):
        self.register('malformedlearner')
        response = self.client.post(
            '/api/progress/update', data='[]', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_curriculum_length_is_fixed_and_refreshes_on_subject_change(self):
        self.register('fixedcourse')
        subject = self.app.config['APP_CONFIG']['subjects'][0]
        with self.app.app_context():
            user = User.query.filter_by(username='fixedcourse').one()
            stored, days = get_subject_curriculum(
                user, subject, self.app.config['APP_CONFIG']
            )
            self.assertEqual(len(days), 90)
            self.assertEqual(days[-1]['day'], 90)
            subject['description'] = 'Changed source material'
            generated = {'days': [
                {'day': day, 'topic': f'Updated {day}', 'objective': f'Objective {day}', 'difficulty': 2}
                for day in range(1, 91)
            ]}
            with patch('app.curriculum.generate_json', return_value=generated) as generate:
                refreshed, updated_days = get_subject_curriculum(
                    user, subject, self.app.config['APP_CONFIG']
                )
            self.assertEqual(generate.call_count, 1)
            self.assertTrue(refreshed.is_ai_generated)
            self.assertEqual(updated_days[0]['topic'], 'Updated 1')
            invalid_config = dict(self.app.config['APP_CONFIG'])
            invalid_config['app'] = dict(invalid_config['app'], curriculum_days=2)
            with self.assertRaisesRegex(ValueError, 'fixed at 90'):
                from app import validate_app_config
                validate_app_config(invalid_config)

    def test_calendar_events_use_course_start_date_and_learner_timezone(self):
        self.register('timezonelearner')
        self.app.config['APP_CONFIG']['schedule']['start_date'] = '2030-01-01'
        response = self.client.post('/api/calendar/schedule', json={
            'day_number': 1, 'time_zone': 'Asia/Kolkata',
        })
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            event = CalendarEvent.query.order_by(CalendarEvent.id).first()
            self.assertEqual(event.time_zone, 'Asia/Kolkata')
            self.assertEqual(event.start_time.isoformat(), '2030-01-01T05:30:00')

    def test_schedule_config_requires_unlock_rule_used_by_completion(self):
        from copy import deepcopy
        from app import validate_app_config
        config = deepcopy(self.app.config['APP_CONFIG'])
        config['schedule'].pop('unlock_rules')
        with self.assertRaisesRegex(ValueError, 'unlock_rules'):
            validate_app_config(config)


if __name__ == '__main__':
    unittest.main()
