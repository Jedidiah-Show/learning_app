import io
import json
import os
import tempfile
import unittest
import zipfile
from datetime import datetime
from unittest.mock import patch

from app import create_app, db
from app.curriculum import all_lessons, all_modules, curriculum
from app.gemini import GeminiError, GeminiRateLimited
from app.models import (
    CalendarEvent, CoursePlan, CourseProject, Credential, LessonCompletion, Quiz,
    QuizResult, ReviewItem, StudySession, User, VideoProgress,
)
from sqlalchemy.exc import IntegrityError


class RuachAICourseTests(unittest.TestCase):
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

    def register(self, username='learner'):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        return response

    def complete_lesson(self, lesson_id):
        response = self.client.post('/api/lessons/complete', json={
            'lesson_id': lesson_id, 'time_spent_minutes': 20,
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def unlock_lesson(self, target_id):
        """Seed completed lessons and prior module projects for a target lesson."""
        target = next(
            (lesson for lesson in all_lessons() if lesson['id'] == target_id),
            None,
        )
        if target is None:
            self.fail(f'Unknown lesson {target_id}')
        prior_module_ids = []
        for module in all_modules():
            if module['id'] == target['module_id']:
                break
            prior_module_ids.append(module['id'])
        with self.app.app_context():
            user = User.query.one()
            for lesson in all_lessons():
                if lesson['id'] == target_id:
                    break
                db.session.add(LessonCompletion(
                    user_id=user.id,
                    lesson_id=lesson['id'],
                    subject_id=lesson['module_id'],
                    day_number=lesson['_ordinal'],
                    completed=True,
                ))
            for module_id in prior_module_ids:
                db.session.add(CourseProject(
                    user_id=user.id,
                    module_id=module_id,
                    project='{}',
                    completed=True,
                ))
            db.session.commit()

    def test_bundled_course_has_its_declared_modules_and_lessons(self):
        self.assertEqual(len(all_modules()), 13)
        self.assertEqual(len(all_lessons()), 212)
        self.assertEqual(
            sum(len(module['lessons']) for module in all_modules()), 212
        )
        self.assertEqual(
            curriculum()['course']['title'],
            'RUACH AI Engineering',
        )

    def test_registration_starts_the_fixed_course_without_proficiency_setup(self):
        self.register()
        first = self.client.get('/api/lessons/daily/1')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()['lesson']['id'], all_lessons()[0]['id'])
        self.assertEqual(self.client.get('/proficiency-test').status_code, 404)
        self.assertEqual(self.client.get('/subject-config').status_code, 404)

    def test_placement_skips_only_foundation_lessons_and_never_projects(self):
        self.register()
        placement = curriculum()['course']['placement']
        public = self.client.get('/api/lessons/placement')
        self.assertEqual(public.status_code, 200)
        public_payload = public.get_json()
        self.assertEqual(len(public_payload['questions']), 10)
        self.assertNotIn('answer', public_payload['questions'][0])
        self.assertEqual(
            sum(question.get('type') == 'short' for question in public_payload['questions']),
            4,
        )

        passed = self.client.post('/api/lessons/placement', json={
            'answers': {
                question['id']: question['answer']
                for question in placement['questions']
            },
        })
        self.assertEqual(passed.status_code, 200, passed.get_json())
        payload = passed.get_json()
        self.assertTrue(payload['passed'])
        self.assertEqual(payload['score'], 10)
        self.assertEqual(
            set(payload['placed_lessons']),
            set(placement['skippable_lessons']),
        )
        self.assertEqual(payload['next_action']['type'], 'project')
        self.assertEqual(payload['next_action']['module_id'], '00')
        with self.app.app_context():
            completions = LessonCompletion.query.filter(
                LessonCompletion.completion_source == 'placement'
            ).all()
            self.assertEqual(
                {item.lesson_id for item in completions},
                set(placement['skippable_lessons']),
            )
            self.assertEqual(CourseProject.query.filter_by(completed=True).count(), 0)

    def test_welcome_lesson_has_a_runnable_first_python_exercise(self):
        self.register()
        response = self.client.get(
            '/api/lessons/practice/0.01/first-python-greeting'
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertIn('def greet(name):', response.get_json()['source'])
        self.assertIn('function responds to different names', response.get_json()['exercise']['checks_code'])

    def test_failed_placement_does_not_mark_lessons_complete(self):
        self.register()
        placement = curriculum()['course']['placement']
        answers = {
            question['id']: (
                'not the answer'
                if question.get('type') == 'short'
                else (question['answer'] + 1) % len(question['options'])
            )
            for question in placement['questions']
        }
        response = self.client.post('/api/lessons/placement', json={'answers': answers})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertFalse(response.get_json()['passed'])
        with self.app.app_context():
            self.assertEqual(LessonCompletion.query.count(), 0)

    def test_setup_checks_round_trip_through_the_guided_start(self):
        self.register()
        first = self.client.get('/lesson/0.01')
        self.assertEqual(first.status_code, 200)
        html = first.get_data(as_text=True)
        self.assertIn('lesson-setup-check', html)
        self.assertIn('data-check-id="python"', html)
        self.assertIn('python -c "print(\'Hello, AI engineering!\')"', html)
        saved = self.client.post('/api/lessons/setup-checks', json={
            'checks': {'python': True, 'first_program': True},
        })
        self.assertEqual(saved.status_code, 200, saved.get_json())
        self.assertEqual(saved.get_json()['done'], 2)
        reloaded = self.client.get('/api/lessons/setup-checks')
        self.assertEqual(reloaded.status_code, 200, reloaded.get_json())
        checks = reloaded.get_json()['checks']
        self.assertTrue(checks['python'])
        self.assertTrue(checks['first_program'])
        self.assertFalse(checks['terminal'])

    def test_lessons_page_renders_the_placement_topics(self):
        self.register()
        page = self.client.get('/lessons')
        self.assertEqual(page.status_code, 200)
        html = page.get_data(as_text=True)
        self.assertIn('placement-check', html)
        self.assertIn('placement-topics-result', html)
        self.assertIn('placement-skip-confirm', html)
        for topic in curriculum()['course']['placement']['topics']:
            self.assertIn(f'data-topic-id="{topic["id"]}"', html)

    def test_onboarding_persists_prior_knowledge_and_available_hours(self):
        self.register()
        page = self.client.get('/onboarding')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'What do you already know?', page.data)
        posted = self.client.post('/onboarding', data={
            'skill_level': 'some_programming',
            'weekly_hours': '15-20',
            'track': 'standard',
        })
        self.assertEqual(posted.status_code, 302)
        with self.app.app_context():
            plan = CoursePlan.query.one()
            self.assertEqual(plan.skill_level, 'some_programming')
            self.assertEqual(plan.weekly_hours, 17)
            self.assertEqual(plan.track, 'standard')

    def test_onboarding_rejects_unknown_answers(self):
        self.register()
        posted = self.client.post('/onboarding', data={
            'skill_level': 'expert',
            'weekly_hours': '',
        })
        self.assertEqual(posted.status_code, 200)
        self.assertIn(b'Choose what you already know', posted.data)

    def test_recommend_track_uses_available_hours_not_assumed_experience(self):
        from app.course_data import recommend_track
        self.assertIsNone(recommend_track(None))
        self.assertEqual(recommend_track(6), 'steady')
        self.assertEqual(recommend_track(11), 'standard')
        self.assertEqual(recommend_track(24), 'accelerated')

    def test_registration_with_safe_destination_routes_through_onboarding(self):
        response = self.client.post('/register', data={
            'username': 'onboarded', 'email': 'onboarded@example.test',
            'password': 'secure-pass-123', 'confirm_password': 'secure-pass-123',
            'next': '/projects',
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        gated = self.client.get('/projects', follow_redirects=False)
        self.assertEqual(gated.status_code, 302)
        self.assertIn('/onboarding', gated.headers['Location'])
        completed = self.client.post('/onboarding', data={
            'skill_level': 'new', 'weekly_hours': '10-12', 'track': 'standard',
        }, follow_redirects=False)
        self.assertEqual(completed.status_code, 302)
        self.assertEqual(self.client.get('/projects').status_code, 200)

    def test_registration_commit_conflict_never_authenticates_the_requester(self):
        with patch('app.routes.auth.db.session.commit',
                   side_effect=IntegrityError('duplicate', {}, Exception('duplicate'))):
            response = self.client.post('/register', data={
                'username': 'conflicted', 'email': 'conflicted@example.test',
                'password': 'secure-pass-123', 'confirm_password': 'secure-pass-123',
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration could not be completed', response.data)
        self.assertEqual(self.client.get('/').status_code, 302)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)

    def test_dashboard_shows_retry_state_when_progress_cannot_load(self):
        self.register()
        with patch('app.routes.main.course_progress', side_effect=RuntimeError('database unavailable')):
            response = self.client.get('/')
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'Your progress is temporarily unavailable', response.data)
        self.assertNotIn(b'lessons complete', response.data)

    def test_schedule_renders_events_in_their_selected_timezone(self):
        self.register()
        with self.app.app_context():
            user = User.query.one()
            db.session.add(CalendarEvent(
                user_id=user.id, title='Local study', start_time=datetime(2030, 1, 2, 12),
                end_time=datetime(2030, 1, 2, 13), time_zone='Africa/Lagos',
                delete_pending=False,
            ))
            db.session.commit()
        response = self.client.get('/schedule')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'13:00', response.data)
        self.assertIn(b'(Africa/Lagos)', response.data)

    def test_progress_hides_tracked_time_when_tracking_is_disabled(self):
        self.register()
        with self.app.app_context():
            user = User.query.one()
            from app.user_preferences import set_user_preferences
            set_user_preferences(user, {'progress': {'track_time_spent': False}})
            db.session.add(StudySession(
                user_id=user.id, session_type='morning', duration_minutes=125,
            ))
            db.session.commit()
        response = self.client.get('/progress')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'0 min', response.data)

    def test_lessons_unlock_sequentially_and_duplicate_completion_is_idempotent(self):
        self.register()
        lessons = all_lessons()
        locked = self.client.get('/api/lessons/daily/2')
        self.assertEqual(locked.status_code, 403)
        result = self.complete_lesson(lessons[0]['id'])
        self.assertEqual(result['next_lesson_id'], lessons[1]['id'])
        duplicate = self.complete_lesson(lessons[0]['id'])
        self.assertTrue(duplicate['already_completed'])
        with self.app.app_context():
            completion = LessonCompletion.query.one()
            self.assertEqual(completion.time_spent_minutes, 20)

    def test_lesson_navigation_respects_completion_and_course_order(self):
        self.register()
        lessons = all_lessons()
        first_page = self.client.get(f"/lesson/{lessons[0]['id']}")
        self.assertEqual(first_page.status_code, 200)
        self.assertIn(b'aria-controls="app-navigation"', first_page.data)
        self.assertIn(b'data-theme-toggle', first_page.data)
        self.assertIn(b'class="nav-icon"', first_page.data)
        self.assertIn(b'Next lesson locked', first_page.data)
        self.assertIn('disabled>← Previous lesson'.encode(), first_page.data)
        self.assertIn(b'disabled data-next-lesson-id=', first_page.data)

        self.complete_lesson(lessons[0]['id'])
        first_page = self.client.get(f"/lesson/{lessons[0]['id']}")
        self.assertIn(
            f'href="/lesson/{lessons[1]["id"]}">Next lesson'.encode(),
            first_page.data,
        )
        self.assertEqual(
            self.client.get(f"/lesson/{lessons[1]['id']}").status_code,
            200,
        )
        self.assertIn(
            f'href="/lesson/{lessons[0]["id"]}">← Previous lesson'.encode(),
            self.client.get(f"/lesson/{lessons[1]['id']}").data,
        )

    def test_completing_a_module_points_to_its_project_before_the_next_module(self):
        self.register()
        first_module = all_modules()[0]
        next_module = all_modules()[1]
        lessons = all_lessons()
        last_lesson = first_module['lessons'][-1]
        last_index = next(
            index for index, lesson in enumerate(lessons)
            if lesson['id'] == last_lesson['id']
        )
        next_module_lesson = lessons[last_index + 1]
        self.assertEqual(next_module_lesson['module_id'], next_module['id'])

        for lesson in first_module['lessons'][:-1]:
            self.complete_lesson(lesson['id'])
        result = self.complete_lesson(last_lesson['id'])

        self.assertIsNone(result['next_lesson_id'])
        self.assertEqual(result['next_action']['type'], 'project')
        self.assertEqual(
            result['next_action']['module_id'], first_module['id']
        )
        self.assertEqual(
            self.client.get(f"/lesson/{next_module_lesson['id']}").status_code,
            403,
        )

        page = self.client.get(f"/lesson/{last_lesson['id']}")
        self.assertEqual(page.status_code, 200)
        html = page.get_data(as_text=True)
        self.assertIn(
            f'href="/projects#module-{first_module["id"]}"', html
        )
        self.assertIn(
            f'Open Module {first_module["number"]} project', html
        )
        self.assertNotIn(
            f'href="/lesson/{next_module_lesson["id"]}"', html
        )

    def test_lesson_page_shows_plain_language_notes_and_self_check_answers(self):
        self.register()
        self.unlock_lesson('1.01')
        lesson = next(item for item in all_lessons() if item['id'] == '1.01')
        self.assertEqual(
            len(lesson['question_answers']), len(lesson['questions'])
        )
        self.assertTrue(all(lesson['question_answers']))
        self.assertTrue(lesson['extras']['intro'])

        page = self.client.get('/lesson/1.01')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'lesson-plain-text', page.data)
        self.assertIn(b'lesson-answer-text', page.data)
        self.assertNotIn(b'Answer in your own words', page.data)

    def test_lesson_material_includes_curriculum_resources(self):
        self.register()
        lesson = all_lessons()[0]
        response = self.client.get('/api/lessons/daily/1')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()['lesson']
        self.assertEqual(payload['title'], lesson['title'])
        self.assertEqual(payload['resources'], lesson['resources'])
        self.assertTrue(payload.get('outcomes') or payload.get('core_concepts'))

    def test_module_quiz_is_locked_until_module_lessons_are_complete(self):
        self.register()
        module = all_modules()[0]
        response = self.client.get(f"/api/quizzes/module/{module['id']}")
        self.assertEqual(response.status_code, 409)

        for lesson in module['lessons']:
            self.complete_lesson(lesson['id'])
        # The quiz path reaches Gemini only after lesson completion.
        with patch('app.gemini.generate_json', side_effect=GeminiError('offline')):
            response = self.client.get(f"/api/quizzes/module/{module['id']}")
        self.assertEqual(response.status_code, 503)

    def test_lesson_quiz_generates_questions_for_the_lesson_module(self):
        self.register()
        lesson = all_lessons()[0]
        questions = [{
            'question': f'Lesson question {index}?',
            'options': ['A', 'B', 'C', 'D'],
            'correct_index': 0,
            'explanation': 'A is correct.',
        } for index in range(5)]
        with patch(
            'app.gemini.generate_json',
            return_value={'questions': questions},
        ):
            response = self.client.get(f"/api/quizzes/lesson/{lesson['id']}")
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['quiz_type'], 'lesson')
        self.assertEqual(len(payload['questions']), 5)
        with self.app.app_context():
            quiz = Quiz.query.filter_by(
                quiz_id=f"dynamoai_lesson_{lesson['id']}"
            ).one()
            self.assertEqual(
                quiz.week_number, lesson['_module']['number'] + 1
            )
            self.assertEqual(quiz.day_number, lesson['_ordinal'])
            self.assertEqual(quiz.subject_id, lesson['module_id'])

    def test_lesson_quiz_generation_maps_provider_rate_limit_to_429(self):
        self.register()
        lesson = all_lessons()[0]
        with patch(
            'app.gemini.generate_json',
            side_effect=GeminiRateLimited(
                'Gemini per-minute limit reached.', retry_after=9
            ),
        ):
            response = self.client.get(f"/api/quizzes/lesson/{lesson['id']}")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '9')
        payload = response.get_json()
        self.assertEqual(payload['retry_after'], 9)
        self.assertIn('limit', payload['error'].lower())

    def test_concurrent_quiz_generation_returns_the_stored_quiz(self):
        self.register()
        lesson = all_lessons()[0]
        quiz_id = f"dynamoai_lesson_{lesson['id']}"
        questions = [{
            'question': f'Racing question {index}?',
            'options': ['A', 'B', 'C', 'D'],
            'correct_index': 0,
            'explanation': 'A is correct.',
        } for index in range(5)]
        normalized = [{
            'id': f'{quiz_id}_{index}',
            'question': item['question'],
            'options': item['options'],
            'correct': 0,
            'explanation': item['explanation'],
        } for index, item in enumerate(questions)]

        def generate_and_seed(*args, **kwargs):
            # Simulate another request committing the same quiz while this
            # request was waiting on the provider.
            db.session.remove()
            with db.engine.begin() as connection:
                connection.execute(Quiz.__table__.insert().values(
                    quiz_id=quiz_id,
                    quiz_type='lesson',
                    subject_id=lesson['module_id'],
                    day_number=lesson['_ordinal'],
                    week_number=lesson['_module']['number'] + 1,
                    questions=json.dumps(normalized),
                    passing_threshold=70,
                    is_ai_generated=True,
                ))
            return {'questions': questions}

        with patch('app.gemini.generate_json', side_effect=generate_and_seed):
            response = self.client.get(f"/api/quizzes/lesson/{lesson['id']}")
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()['quiz_id'], quiz_id)
        with self.app.app_context():
            self.assertEqual(Quiz.query.filter_by(quiz_id=quiz_id).count(), 1)

    def test_lesson_clarification_maps_provider_rate_limit_to_429(self):
        self.register()
        lesson = all_lessons()[0]
        with patch(
            'app.gemini.generate_json',
            side_effect=GeminiRateLimited(
                'Gemini per-minute limit reached.', retry_after=11
            ),
        ):
            response = self.client.post('/api/lessons/ask', json={
                'lesson_id': lesson['id'],
                'question': 'Can you clarify the main idea?',
            })
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '11')
        self.assertEqual(response.get_json()['retry_after'], 11)

    def test_lesson_tutor_greeting_introduces_ruach_ai_without_ai_request(self):
        self.register()
        lesson = all_lessons()[0]
        with patch('app.gemini.generate_json') as generate:
            response = self.client.post('/api/lessons/ask', json={
                'lesson_id': lesson['id'],
                'question': 'Hello!',
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ruach-AI', response.get_json()['answer'])
        self.assertEqual(response.get_json()['in_scope'], True)
        generate.assert_not_called()

    def test_lesson_tutor_uses_fixed_redirect_for_out_of_scope_response(self):
        self.register()
        lesson = all_lessons()[0]
        with patch(
            'app.gemini.generate_json',
            return_value={
                'in_scope': False,
                'answer': 'An unrelated answer that must not be shown.',
            },
        ):
            response = self.client.post('/api/lessons/ask', json={
                'lesson_id': lesson['id'],
                'question': 'Tell me about an unrelated topic.',
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn('RUACH AI Engineering course', response.get_json()['answer'])
        self.assertNotIn('unrelated answer', response.get_json()['answer'])
        self.assertFalse(response.get_json()['in_scope'])

    def test_module_quiz_generates_questions_for_the_module(self):
        self.register()
        module = all_modules()[0]
        for lesson in module['lessons']:
            self.complete_lesson(lesson['id'])
        questions = [{
            'question': f'Module question {index}?',
            'options': ['A', 'B', 'C', 'D'],
            'correct_index': 0,
            'explanation': 'A is correct.',
        } for index in range(5)]
        with patch(
            'app.gemini.generate_json',
            return_value={'questions': questions},
        ):
            response = self.client.get(f"/api/quizzes/module/{module['id']}")
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['quiz_type'], 'module')
        self.assertEqual(len(payload['questions']), 5)
        with self.app.app_context():
            quiz = Quiz.query.filter_by(
                quiz_id=f"dynamoai_module_{module['id']}"
            ).one()
            self.assertEqual(quiz.week_number, module['number'] + 1)
            self.assertEqual(quiz.subject_id, module['id'])

    def test_quiz_submission_requires_every_answer_and_records_a_result(self):
        self.register()
        lesson = all_lessons()[0]
        questions = [{
            'id': f'q{index}', 'question': f'Question {index}?',
            'options': ['A', 'B', 'C', 'D'], 'correct': 0,
            'explanation': 'A is correct.',
        } for index in range(5)]
        quiz = Quiz(
            quiz_id='test-lesson-quiz', quiz_type='lesson',
            subject_id=lesson['module_id'], day_number=1, week_number=1,
            questions=json.dumps(questions), passing_threshold=70,
        )
        quiz_id = quiz.quiz_id
        with self.app.app_context():
            db.session.add(quiz)
            db.session.commit()

        incomplete = self.client.post('/api/quizzes/submit', json={
            'quiz_id': quiz_id, 'answers': {'0': 0},
        })
        self.assertEqual(incomplete.status_code, 400)
        submitted = self.client.post('/api/quizzes/submit', json={
            'quiz_id': quiz_id,
            'answers': {str(index): 0 for index in range(5)},
        })
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.get_json()['score'], 100)
        with self.app.app_context():
            self.assertEqual(QuizResult.query.count(), 1)

    def test_module_project_unlocks_after_lessons_and_uses_bundled_fallback(self):
        self.register()
        module = all_modules()[0]
        locked = self.client.get(f"/api/projects/module/{module['id']}")
        self.assertEqual(locked.status_code, 409)
        for lesson in module['lessons']:
            self.complete_lesson(lesson['id'])
        project = self.client.get(f"/api/projects/module/{module['id']}")
        self.assertEqual(project.status_code, 200)
        payload = project.get_json()
        self.assertTrue(payload['project']['brief'])
        self.assertFalse(payload['is_ai_generated'])
        with self.app.app_context():
            self.assertEqual(CourseProject.query.count(), 1)

    def test_monthly_blueprint_capstone_choice_and_personal_project_are_saved(self):
        self.register()
        page = self.client.get('/projects')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Monthly milestones', page.data)
        self.assertIn(b'High-precision production RAG engine', page.data)
        choice = self.client.post('/api/course-plan/required-project', json={
            'required_project_id': 'production-rag',
        })
        self.assertEqual(choice.status_code, 200, choice.get_json())
        saved = self.client.post('/api/course-plan/portfolio', json={
            'portfolio_title': 'Community knowledge assistant',
            'portfolio_summary': 'A personal RAG project for trusted local resources.',
            'portfolio_repository_url': 'https://github.com/learner/community-assistant',
            'portfolio_demo_url': '',
        })
        self.assertEqual(saved.status_code, 200, saved.get_json())
        portfolio = self.client.get('/portfolio')
        self.assertIn(b'Community knowledge assistant', portfolio.data)
        with self.app.app_context():
            plan = CoursePlan.query.one()
            self.assertEqual(plan.required_project_id, 'production-rag')
            self.assertEqual(plan.portfolio_title, 'Community knowledge assistant')
            self.assertEqual(plan.track, 'standard')

    def test_learners_can_switch_between_standard_and_accelerated_tracks(self):
        self.register()
        standard = self.client.get('/progress')
        self.assertEqual(standard.status_code, 200)
        self.assertIn(b'10-month standard', standard.data)
        self.assertIn(b'Month 10', standard.data)

        switched = self.client.post('/api/course-plan/track', json={
            'track': 'accelerated',
        })
        self.assertEqual(switched.status_code, 200, switched.get_json())
        self.assertEqual(switched.get_json()['label'], '5-month intensive (≈24 focused hours/week)')
        accelerated = self.client.get('/progress')
        self.assertEqual(accelerated.status_code, 200)
        self.assertIn(b'5-month intensive', accelerated.data)
        self.assertIn(b'Month 5', accelerated.data)
        self.assertNotIn(b'Month 10', accelerated.data)
        with self.app.app_context():
            self.assertEqual(CoursePlan.query.one().track, 'accelerated')

        rejected = self.client.post('/api/course-plan/track', json={
            'track': 'impossible',
        })
        self.assertEqual(rejected.status_code, 400)

    def test_selected_capstone_is_used_for_the_final_required_project(self):
        self.register()
        self.client.post('/api/course-plan/required-project', json={
            'required_project_id': 'evaluation-harness',
        })
        module = all_modules()[-1]
        with self.app.app_context():
            user = User.query.one()
            for index, lesson in enumerate(module['lessons'], start=1):
                db.session.add(LessonCompletion(
                    user_id=user.id, lesson_id=lesson['id'], subject_id=module['id'],
                    day_number=index, completed=True,
                ))
            db.session.commit()
        response = self.client.get(f"/api/projects/module/{module['id']}")
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload['project']['required_project_id'], 'evaluation-harness')
        self.assertEqual(payload['project']['title'], 'Continuous evaluation and regression harness')
        self.assertFalse(payload['is_ai_generated'])

    def test_portfolio_project_rejects_non_https_evidence_links(self):
        self.register()
        response = self.client.post('/api/course-plan/portfolio', json={
            'portfolio_title': 'My project', 'portfolio_summary': 'A useful project.',
            'portfolio_repository_url': 'http://example.test/repo',
        })
        self.assertEqual(response.status_code, 400)

    def test_project_submission_validates_ai_evaluation_and_records_result(self):
        self.register()
        module = all_modules()[0]
        for lesson in module['lessons']:
            self.complete_lesson(lesson['id'])
        opened = self.client.get(f"/api/projects/module/{module['id']}")
        self.assertEqual(opened.status_code, 200)

        submission = (
            'I built the requested artefact, tested each deliverable, and '
            'recorded the verification output for review.'
        )
        verification = {
            'verified': True,
            'checks_url': 'https://github.com/learner/project/actions/runs/1',
            'checks_host': 'github.com',
            'checks_status': 200,
            'verified_at': '2026-10-29T12:00:00+00:00',
        }
        with patch(
            'app.routes.projects.verify_checks', return_value=verification
        ), patch(
            'app.gemini.generate_json',
            return_value={'score': 101, 'summary': 'Invalid score.'},
        ):
            rejected = self.client.post(
                f"/api/projects/module/{module['id']}/submit",
                json={
                    'submission': submission,
                    'repository_url': 'https://github.com/learner/project',
                    'checks_url': verification['checks_url'],
                },
            )
        self.assertEqual(rejected.status_code, 503)
        with self.app.app_context():
            self.assertFalse(CourseProject.query.one().completed)

        evaluation = {
            'score': 88,
            'summary': 'The artefact meets the brief with minor gaps.',
            'strengths': ['Working implementation', 'Clear verification'],
            'gaps': ['Add one edge-case test'],
            'next_steps': ['Document the remaining edge case'],
            'criterion_feedback': [
                {
                    'criterion': item['criterion'],
                    'score': 88,
                    'evidence': 'The README and test output document this criterion.',
                    'gap': 'Add one edge-case test.',
                }
                for item in module['project_rubric']
            ],
        }
        with patch(
            'app.routes.projects.verify_checks', return_value=verification
        ), patch('app.gemini.generate_json', return_value=evaluation):
            accepted = self.client.post(
                f"/api/projects/module/{module['id']}/submit",
                json={'submission': submission,
                      'repository_url': 'https://github.com/learner/project',
                      'checks_url': verification['checks_url'],
                      'demo_url': 'https://demo.example.test'},
            )
        self.assertEqual(accepted.status_code, 200, accepted.get_json())
        payload = accepted.get_json()
        self.assertTrue(payload['completed'])
        self.assertEqual(payload['evaluation']['score'], 88)
        self.assertEqual(payload['evaluation']['evaluation_source'], 'ai')
        self.assertTrue(payload['checks']['verified'])
        with self.app.app_context():
            record = CourseProject.query.one()
            self.assertTrue(record.completed)
            self.assertTrue(record.checks_verified)
            self.assertEqual(record.repository_url, 'https://github.com/learner/project')
            self.assertEqual(record.checks_url, verification['checks_url'])
            self.assertEqual(record.demo_url, 'https://demo.example.test')
            # Evaluation provenance must not overwrite how the brief was made.
            self.assertFalse(record.is_ai_generated)
        portfolio = self.client.get('/portfolio')
        self.assertEqual(portfolio.status_code, 200)
        self.assertIn(b'https://github.com/learner/project', portfolio.data)

    def test_missed_quiz_answers_enter_spaced_review_and_are_rescheduled(self):
        self.register()
        with self.app.app_context():
            quiz = Quiz(
                quiz_id='review-test', quiz_type='lesson', subject_id='01',
                day_number=1, week_number=1,
                questions=json.dumps([
                    {'id': 'review-q1', 'question': 'Which is correct?',
                     'options': ['A', 'B', 'C', 'D'], 'correct': 2,
                     'explanation': 'C is correct.'},
                ]),
                passing_threshold=70,
            )
            db.session.add(quiz)
            db.session.commit()
        submitted = self.client.post('/api/quizzes/submit', json={
            'quiz_id': 'review-test', 'answers': {'0': 0},
        })
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.get_json()['missed_questions_added'], 1)
        queue = self.client.get('/api/quizzes/review').get_json()
        self.assertEqual(queue['due_count'], 1)
        item_id = queue['items'][0]['id']
        reviewed = self.client.post(
            f'/api/quizzes/review/{item_id}', json={'answer': 2},
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertTrue(reviewed.get_json()['correct'])
        with self.app.app_context():
            item = ReviewItem.query.one()
            self.assertEqual(item.repetitions, 1)
            self.assertEqual(item.interval_days, 1)
        self.assertEqual(self.client.get('/api/quizzes/review').get_json()['due_count'], 0)

    def test_project_requires_verified_checks_and_cannot_be_self_attested(self):
        self.register()
        module = all_modules()[0]
        for lesson in module['lessons']:
            self.complete_lesson(lesson['id'])
        self.client.get(f"/api/projects/module/{module['id']}")
        submission = (
            'I built an artefact, checked every requirement and documented my '
            'test results in the repository README.'
        )
        verification = {
            'verified': True,
            'checks_url': 'https://github.com/learner/project/actions/runs/2',
            'checks_host': 'github.com',
            'checks_status': 200,
            'verified_at': '2026-10-29T12:00:00+00:00',
        }
        payload = {
            'submission': submission,
            'repository_url': 'https://github.com/learner/project',
            'checks_url': verification['checks_url'],
        }
        missing_checks = self.client.post(
            f"/api/projects/module/{module['id']}/submit",
            json={
                'submission': submission,
                'repository_url': 'https://github.com/learner/project',
            },
        )
        self.assertEqual(missing_checks.status_code, 400)
        with patch(
            'app.routes.projects.verify_checks', return_value=verification
        ), patch('app.gemini.generate_json', side_effect=GeminiError('provider unavailable')):
            saved = self.client.post(
                f"/api/projects/module/{module['id']}/submit", json=payload,
            )
        self.assertEqual(saved.status_code, 200)
        self.assertFalse(saved.get_json()['completed'])
        self.assertTrue(saved.get_json()['checks']['verified'])
        # Self-attestation is not an assessment path.
        rejected = self.client.post(
            f"/api/projects/module/{module['id']}/self-attest",
            json={'evidence': []},
        )
        self.assertEqual(rejected.status_code, 404)
        # A failing or unreachable checks page never records a submission.
        from app.project_verification import VerificationError
        with patch(
            'app.routes.projects.verify_checks',
            side_effect=VerificationError('The checks page reports a failed build'),
        ):
            failed_checks = self.client.post(
                f"/api/projects/module/{module['id']}/submit", json=payload,
            )
        self.assertEqual(failed_checks.status_code, 422)
        with self.app.app_context():
            self.assertFalse(CourseProject.query.one().completed)
        with self.app.app_context():
            # A failing checks run keeps the learner's draft instead of
            # discarding the submission text.
            self.assertEqual(
                CourseProject.query.one().submission.strip(), submission.strip()
            )

    def test_module_zero_starter_kit_is_the_docs_kit(self):
        self.register()
        response = self.client.get('/projects/starter/00')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        archive = zipfile.ZipFile(io.BytesIO(response.data))
        names = archive.namelist()
        self.assertIn('ruach-module-00/README.md', names)
        self.assertIn('ruach-module-00/docs/glossary.md', names)
        self.assertIn('ruach-module-00/docs/architecture-sketch.md', names)
        self.assertIn('ruach-module-00/SETUP.md', names)
        self.assertIn('ruach-module-00/.github/workflows/docs.yml', names)

    def test_module_one_starter_kit_is_the_code_kit(self):
        self.register()
        response = self.client.get('/projects/starter/01')
        self.assertEqual(response.status_code, 200)
        archive = zipfile.ZipFile(io.BytesIO(response.data))
        names = archive.namelist()
        self.assertIn('ruach-module-01/src/main.py', names)
        self.assertIn('ruach-module-01/tests/test_main.py', names)
        self.assertIn('ruach-module-01/.github/workflows/tests.yml', names)
        self.assertIn('ruach-module-01/SETUP.md', names)

    def test_credential_requires_full_completion_and_is_publicly_verifiable(self):
        self.register()
        page = self.client.get('/credential')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Eligibility', page.data)
        premature = self.client.post('/api/credentials/issue')
        self.assertEqual(premature.status_code, 409)

        with self.app.app_context():
            user = User.query.one()
            for lesson in all_lessons():
                db.session.add(LessonCompletion(
                    user_id=user.id, lesson_id=lesson['id'],
                    subject_id=lesson['module_id'], day_number=lesson['_ordinal'],
                    completed=True,
                ))
            for module in all_modules():
                db.session.add(CourseProject(
                    user_id=user.id, module_id=module['id'],
                    project='{}', completed=True,
                ))
            db.session.commit()
        issued = self.client.post('/api/credentials/issue')
        self.assertEqual(issued.status_code, 201, issued.get_json())
        credential = issued.get_json()['credential']
        self.assertEqual(credential['status'], 'active')
        self.assertTrue(credential['public_id'])
        self.client.post('/logout')
        public = self.client.get(
            f"/credentials/{credential['public_id']}",
            query_string={'sig': credential['signature']},
        )
        self.assertEqual(public.status_code, 200)
        self.assertIn(b'Verified', public.data)
        self.assertIn(b'Learner', public.data)
        unsigned = self.client.get(f"/credentials/{credential['public_id']}")
        self.assertEqual(unsigned.status_code, 200)
        self.assertNotIn(b'issuer signature valid', unsigned.data)
        missing = self.client.get('/credentials/not-a-real-credential')
        self.assertEqual(missing.status_code, 404)

    def test_users_have_independent_course_progress(self):
        self.register('firstlearner')
        self.complete_lesson(all_lessons()[0]['id'])
        self.client.post('/logout')
        self.register('secondlearner')
        locked = self.client.get('/api/lessons/daily/2')
        self.assertEqual(locked.status_code, 403)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 2)

    def test_lesson_page_renders_a_lazy_video_only_when_one_is_curated(self):
        self.register()
        first = all_lessons()[0]
        self.assertIsNone(first.get('video'))
        no_video = self.client.get(f"/lesson/{first['id']}")
        self.assertEqual(no_video.status_code, 200)
        self.assertNotIn('data-lesson-video', no_video.get_data(as_text=True))

        lesson = next(
            item for item in all_lessons() if item.get('video')
        )
        self.unlock_lesson(lesson['id'])
        response = self.client.get(f"/lesson/{lesson['id']}")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-lesson-video', html)
        self.assertIn(f'data-video-id="{lesson["video"]["id"]}"', html)
        self.assertIn(lesson['video']['thumbnail_url'], html)
        self.assertIn('/api/lessons/video-progress', html)

    def test_account_reset_clears_watch_progress(self):
        self.register()
        lesson = next(
            item for item in all_lessons() if item.get('video')
        )
        self.unlock_lesson(lesson['id'])
        response = self.client.post('/api/lessons/video-progress', json={
            'lesson_id': lesson['id'],
            'position_seconds': 60,
            'duration_seconds': 600,
        })
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(VideoProgress.query.count(), 1)

        reset = self.client.post('/account/reset', json={
            'current_password': 'secure-pass-123',
        })
        self.assertEqual(reset.status_code, 200, reset.get_json())
        with self.app.app_context():
            self.assertEqual(VideoProgress.query.count(), 0)

    def test_video_progress_requires_an_unlocked_lesson_with_a_video(self):
        self.register()
        video_lesson = next(
            lesson for lesson in all_lessons() if lesson.get('video')
        )
        locked = self.client.post('/api/lessons/video-progress', json={
            'lesson_id': video_lesson['id'],
            'position_seconds': 10,
            'duration_seconds': 100,
        })
        self.assertEqual(locked.status_code, 403)

        first = all_lessons()[0]
        self.assertIsNone(first.get('video'))
        no_video = self.client.post('/api/lessons/video-progress', json={
            'lesson_id': first['id'],
            'position_seconds': 10,
            'duration_seconds': 100,
        })
        self.assertEqual(no_video.status_code, 404)
        self.assertIn('no video', no_video.get_json()['error'])

    def test_video_progress_tracks_furthest_watch_position_and_completion(self):
        self.register()
        lesson = next(
            item for item in all_lessons() if item.get('video')
        )
        self.unlock_lesson(lesson['id'])
        duration = 600

        def report(position):
            response = self.client.post('/api/lessons/video-progress', json={
                'lesson_id': lesson['id'],
                'position_seconds': position,
                'duration_seconds': duration,
            })
            self.assertEqual(response.status_code, 200, response.get_json())
            return response.get_json()

        first = report(30)
        self.assertFalse(first['completed'])
        self.assertEqual(first['watched_seconds'], 30)
        half = report(300)
        self.assertFalse(half['completed'])
        done = report(570)
        self.assertTrue(done['completed'])
        self.assertTrue(done['just_completed'])
        with self.app.app_context():
            progress = VideoProgress.query.one()
            self.assertEqual(progress.video_id, lesson['video']['id'])
            self.assertTrue(progress.completed)
            self.assertEqual(progress.watched_seconds, 570)
            self.assertEqual(progress.duration_seconds, duration)

        earlier = report(120)
        self.assertTrue(earlier['completed'])
        self.assertFalse(earlier['just_completed'])
        self.assertEqual(earlier['last_position'], 120)

    def test_video_progress_validates_numbers_and_lesson_ids(self):
        self.register()
        lesson = next(
            item for item in all_lessons() if item.get('video')
        )
        self.unlock_lesson(lesson['id'])
        invalid_payloads = [
            {'lesson_id': lesson['id'], 'position_seconds': -1},
            {'lesson_id': lesson['id'], 'position_seconds': '10'},
            {'lesson_id': lesson['id'], 'position_seconds': True},
            {'lesson_id': lesson['id']},
            {
                'lesson_id': lesson['id'],
                'position_seconds': 10,
                'duration_seconds': -1,
            },
            {
                'lesson_id': lesson['id'],
                'position_seconds': 10,
                'duration_seconds': 999999,
            },
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    '/api/lessons/video-progress', json=payload
                )
                self.assertEqual(response.status_code, 400)
        missing = self.client.post('/api/lessons/video-progress', json={
            'lesson_id': 'missing.lesson',
            'position_seconds': 10,
        })
        self.assertEqual(missing.status_code, 404)
