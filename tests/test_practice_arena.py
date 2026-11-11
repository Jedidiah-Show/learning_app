"""Practice Arena: catalogue, workspace, and honest progress labels."""

import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, db
from app.models import (
    PracticeWorkspace, SkillNode, Submission, User, UserSkillProgress,
)
from app.practice_arena import (
    DIFFICULTIES,
    TOPICS,
    TRACKS,
    all_arena_problems,
    catalogue,
)


class ArenaTestCase(unittest.TestCase):
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

    def register(self, username):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def login(self, username):
        response = self.client.post('/login', data={
            'username': username,
            'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)


class ArenaTaxonomyTests(unittest.TestCase):
    def test_three_tracks_are_present_and_ai_is_primary(self):
        self.assertEqual(
            [track['id'] for track in TRACKS],
            ['ai-engineering', 'algorithms', 'machine-learning'],
        )
        self.assertTrue(TRACKS[0]['primary'])
        self.assertFalse(TRACKS[1]['primary'])
        self.assertFalse(TRACKS[2]['primary'])

    def test_machine_learning_topics(self):
        topics = {
            topic['id']: topic for topic in TOPICS
            if topic['track'] == 'machine-learning'
        }
        self.assertEqual(
            {topic['id'] for topic in topics.values()},
            {'ml-statistics', 'ml-python', 'ml-data-analysis'},
        )
        self.assertEqual(topics['ml-statistics']['name'], 'Statistics')
        self.assertEqual(topics['ml-python']['name'], 'Python for ML')
        self.assertEqual(topics['ml-data-analysis']['name'], 'Data Analysis')

    def test_every_problem_has_a_valid_track_topic_and_difficulty(self):
        problems = all_arena_problems()
        topics = {topic['id']: topic for topic in TOPICS}
        self.assertGreaterEqual(len(problems), 70)
        for problem in problems.values():
            with self.subTest(problem=problem['id']):
                self.assertIn(problem['track'], {t['id'] for t in TRACKS})
                self.assertIn(problem['topic'], topics)
                self.assertEqual(
                    topics[problem['topic']]['track'], problem['track'],
                )
                self.assertIn(problem['difficulty'], DIFFICULTIES)
                self.assertTrue(problem['skills'])
                self.assertIn(problem['id'], problems)
                for prerequisite in problem['prerequisites']:
                    self.assertIn(prerequisite, problems)

    def test_algorithms_problems_are_published_and_solutions_pass_checks(self):
        problems = all_arena_problems()
        algorithms = [
            problem for problem in problems.values()
            if problem['track'] == 'algorithms'
        ]
        self.assertGreaterEqual(len(algorithms), 6)
        for problem in algorithms:
            with self.subTest(problem=problem['id']):
                namespace = {}
                exec(problem['solution_code'], namespace)
                exec(problem['browser_checks'], namespace)

    def test_machine_learning_problems_are_beginner_and_pass_checks(self):
        problems = all_arena_problems()
        ml = [
            problem for problem in problems.values()
            if problem['track'] == 'machine-learning'
        ]
        self.assertEqual(len(ml), 6)
        for problem in ml:
            with self.subTest(problem=problem['id']):
                self.assertEqual(problem['difficulty'], 'beginner')
                self.assertTrue(problem['skills'])
                namespace = {}
                exec(problem['solution_code'], namespace)
                exec(problem['browser_checks'], namespace)

    def test_machine_learning_descriptive_statistics_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-statistics-descriptive-statistics']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['statistics', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_csv_inspection_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-python-csv-inspection']
        self.assertEqual(problem['topic'], 'ml-data-analysis')
        self.assertEqual(problem['skills'], ['python', 'data-analysis'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_probability_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-statistics-probability']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['statistics', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_missing_values_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-data-preparation-missing-values']
        self.assertEqual(problem['topic'], 'ml-data-analysis')
        self.assertEqual(problem['skills'], ['data-preparation', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_mean_squared_error_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-regression-mean-squared-error']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['regression', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_confusion_matrix_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-classification-confusion-matrix']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['classification', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_catalogue_filters_compose(self):
        result = catalogue(
            track='algorithms', difficulty='beginner', query='frequency',
        )
        ids = [problem['id'] for problem in result['problems']]
        self.assertEqual(ids, ['algo-count-word-frequency'])
        self.assertEqual(result['selected']['track'], 'algorithms')

        result = catalogue(track='ai-engineering', topic='rag-retrieval')
        self.assertTrue(result['problems'])
        self.assertTrue(all(
            problem['topic'] == 'rag-retrieval'
            for problem in result['problems']
        ))

        # Unknown filters are ignored rather than causing a 500.
        result = catalogue(track='nope', difficulty='impossible', sort='bad')
        self.assertEqual(result['selected']['track'], '')
        self.assertEqual(result['selected']['difficulty'], '')
        self.assertEqual(result['selected']['sort'], 'recommended')
        self.assertTrue(result['problems'])

class ArenaPageTests(ArenaTestCase):
    def test_pages_require_authentication(self):
        for path in ('/arena/', '/arena/ai-engineering', '/arena/algorithms',
                     '/arena/problems'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertIn(response.status_code, (302, 401))

    def test_arena_landing_is_primary_and_links_to_distinct_tracks(self):
        self.register('arena')
        response = self.client.get('/arena/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Flagship track', html)
        self.assertIn('AI Engineering Practice', html)
        self.assertIn('Algorithms &amp; Problem Solving', html)
        self.assertIn('How progress is labelled', html)
        self.assertIn('/arena/ai-engineering', html)
        self.assertIn('/arena/algorithms', html)

    def test_lesson_practice_route_is_still_served(self):
        self.register('arena')
        response = self.client.get('/practice')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Practice library', response.get_data(as_text=True))

    def test_track_pages_show_their_own_problems(self):
        self.register('arena')
        ai_html = self.client.get('/arena/ai-engineering').get_data(as_text=True)
        self.assertIn('Run your first tiny Python program', ai_html)
        self.assertNotIn('Binary search', ai_html)

        algo_html = self.client.get(
            '/arena/algorithms'
        ).get_data(as_text=True)
        self.assertIn('Binary search', algo_html)
        self.assertIn('Factorial with recursion', algo_html)
        self.assertNotIn('Run your first tiny Python program', algo_html)

    def test_machine_learning_track_shows_statistics_problem(self):
        self.register('mlarena')
        response = self.client.get('/arena/machine-learning')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Machine Learning Practice', html)
        self.assertIn('Descriptive statistics from scratch', html)
        self.assertIn('Inspect a small CSV dataset', html)
        self.assertIn('Probability of an event', html)
        self.assertIn('Handle missing values', html)
        self.assertIn('Mean squared error', html)
        self.assertIn('Confusion matrix', html)
        self.assertNotIn('Binary search', html)

    def test_catalogue_filters_and_empty_state(self):
        self.register('arena')
        response = self.client.get(
            '/arena/problems?track=algorithms&difficulty=beginner&q=frequency'
        )
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Count word frequency', html)
        self.assertIn('1 problem found', html)
        self.assertNotIn('Binary search', html)

        empty = self.client.get('/arena/problems?q=no-such-problem-xyz')
        empty_html = empty.get_data(as_text=True)
        self.assertIn('No problems match these filters', empty_html)
        self.assertIn('Clear all filters', empty_html)

    def test_problem_detail_has_standalone_workspace_and_honest_labels(self):
        self.register('arena')
        response = self.client.get('/arena/problems/algo-binary-search')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-arena-workspace', html)
        self.assertIn('id="arena-editor"', html)
        self.assertIn('sandbox="allow-scripts"', html)
        self.assertIn('js/arena.bundle.js', html)
        self.assertIn('isolated server judge', html)
        self.assertIn('Not started', html)
        self.assertNotIn('status="solved"', html)
        # Reference material must not be embedded in the problem page.
        self.assertNotIn('return numbers[middle]', html)
        self.assertNotIn('browser_checks', html)

    def test_unknown_problem_returns_404(self):
        self.register('arena')
        self.assertEqual(
            self.client.get('/arena/problems/does-not-exist').status_code, 404,
        )


class ArenaApiTests(ArenaTestCase):
    def test_public_problem_payload_omits_solutions_and_editorial(self):
        self.register('arena')
        response = self.client.get('/arena/api/problems/algo-binary-search')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['problem']['id'], 'algo-binary-search')
        self.assertEqual(data['source'], data['problem']['starter_code'])
        self.assertNotIn('solution_code', data['problem'])
        self.assertNotIn('editorial', data['problem'])
        self.assertNotIn('browser_checks', data['problem'])
        self.assertNotIn('hints', data['problem'])
        self.assertEqual(data['status'], 'not-started')

    def test_submit_queues_code_and_rejects_invalid_source(self):
        self.register('grader')
        invalid = self.client.post(
            '/arena/api/problems/algo-binary-search/submit',
            json={'code': 'def broken(:'},
        )
        self.assertEqual(invalid.status_code, 400)

        queued = self.client.post(
            '/arena/api/problems/algo-binary-search/submit',
            json={'code': 'def binary_search(numbers, target):\n    return -1\n'},
        )
        self.assertEqual(queued.status_code, 202)
        self.assertEqual(queued.get_json()['status'], 'queued')
        with self.app.app_context():
            record = db.session.get(
                Submission, queued.get_json()['submission_id'],
            )
            self.assertEqual(record.verdict, 'PENDING')

    def test_worker_records_verdict_and_verified_skill_evidence(self):
        from app.services.judge import JudgeResult
        from app.services.judge_worker import process_next_submission

        self.register('judgelearner')
        with self.app.app_context():
            user = User.query.filter_by(username='judgelearner').one()
            db.session.add(Submission(
                id='judge-test-submission',
                user_id=user.id,
                problem_id='algo-binary-search',
                code_snapshot='def binary_search(numbers, target): return -1',
                verdict='PENDING',
            ))
            db.session.commit()

        result = JudgeResult()
        result.verdict = 'ACCEPTED'
        result.tests_passed = 1
        result.total_tests = 1
        with patch(
            'app.services.judge_worker.execute_in_sandbox',
            return_value=result,
        ):
            self.assertTrue(process_next_submission(self.app))

        with self.app.app_context():
            submission = db.session.get(Submission, 'judge-test-submission')
            self.assertEqual(submission.verdict, 'ACCEPTED')
            self.assertEqual(
                UserSkillProgress.query.filter_by(
                    user_id=submission.user_id,
                    skill_id='searching',
                ).one().status,
                'DEMONSTRATED',
            )

    def test_hints_are_progressive_and_editorial_requires_saved_attempt(self):
        self.register('hintlearner')
        hint = self.client.get(
            '/arena/api/problems/algo-binary-search/hint?stage=1'
        )
        self.assertEqual(hint.status_code, 200)
        self.assertTrue(hint.get_json()['hint'])

        denied = self.client.get(
            '/arena/api/problems/algo-binary-search/hint?stage=5'
        )
        self.assertEqual(denied.status_code, 403)

        self.client.put(
            '/arena/api/problems/algo-binary-search/workspace',
            json={'source': 'def binary_search(numbers, target):\n    pass\n'},
        )
        allowed = self.client.get(
            '/arena/api/problems/algo-binary-search/hint?stage=5'
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertIn('def binary_search', allowed.get_json()['hint'])

    def test_passport_page_api_and_download_are_user_scoped(self):
        self.register('passportlearner')
        page = self.client.get('/passport')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Skill Passport', page.get_data(as_text=True))
        api = self.client.get('/api/passport')
        self.assertEqual(api.status_code, 200)
        self.assertTrue(api.get_json()['skills'])
        with self.app.app_context():
            self.assertEqual(SkillNode.query.count(), 0)
        download = self.client.get('/passport/download')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.mimetype, 'text/csv')
        self.assertIn(b'skill_id,title,category,status', download.data)


    def test_workspace_saves_per_learner_and_problem(self):
        self.register('alpha')
        source = 'def binary_search(numbers, target):\n    return 0\n'
        saved = self.client.put(
            '/arena/api/problems/algo-binary-search/workspace',
            json={'source': source},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.get_json()['status'], 'saved')

        loaded = self.client.get('/arena/api/problems/algo-binary-search')
        self.assertEqual(loaded.get_json()['source'], source)
        self.assertEqual(loaded.get_json()['status'], 'practised')
        detail = self.client.get('/arena/problems/algo-binary-search')
        self.assertIn('Practised', detail.get_data(as_text=True))

        # A different learner must not see alpha's work.
        self.client.post('/logout')
        self.register('beta')
        other = self.client.get('/arena/api/problems/algo-binary-search')
        self.assertEqual(
            other.get_json()['source'],
            other.get_json()['problem']['starter_code'],
        )
        self.assertEqual(other.get_json()['status'], 'not-started')

        with self.app.app_context():
            self.assertEqual(
                PracticeWorkspace.query.filter_by(
                    user_id=User.query.filter_by(username='alpha').one().id,
                ).count(),
                1,
            )

    def test_workspace_rejects_invalid_and_oversized_source(self):
        self.register('alpha')
        invalid = self.client.put(
            '/arena/api/problems/algo-binary-search/workspace',
            json={'source': 42},
        )
        self.assertEqual(invalid.status_code, 400)

        oversized = self.client.put(
            '/arena/api/problems/algo-binary-search/workspace',
            json={'source': 'x' * 20001},
        )
        self.assertEqual(oversized.status_code, 413)

    def test_editorial_requires_an_attempt_and_then_reveals(self):
        self.register('alpha')
        url = '/arena/api/problems/algo-binary-search/editorial'
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403)

        self.client.put(
            '/arena/api/problems/algo-binary-search/workspace',
            json={'source': 'def binary_search(numbers, target):\n    pass\n'},
        )
        allowed = self.client.get(url)
        self.assertEqual(allowed.status_code, 200)
        self.assertIn('binary_search', allowed.get_json()['solution_code'])
        self.assertIn('authoritative grade', allowed.get_json()['notice'])

    def test_editorial_rate_limit_is_configured(self):
        from app.rate_limit import RATE_LIMIT_CONFIG
        self.assertIn('arena-editorial', RATE_LIMIT_CONFIG)

    def test_workspace_api_requires_csrf_when_enabled(self):
        self.register('alpha')
        self.client.get('/arena/')
        with self.client.session_transaction() as session:
            token = session['_csrf_token']
        self.app.config['CSRF_ENABLED'] = True
        url = '/arena/api/problems/algo-binary-search/workspace'

        missing = self.client.put(url, json={'source': 'x = 1'})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(
            missing.get_json()['error'], 'CSRF validation failed',
        )

        accepted = self.client.put(
            url,
            json={'source': 'x = 1'},
            headers={'X-CSRF-Token': token},
        )
        self.assertEqual(accepted.status_code, 200)

    def test_unknown_workspace_problem_returns_404(self):
        self.register('alpha')
        response = self.client.put(
            '/arena/api/problems/nope/workspace', json={'source': 'x = 1'},
        )
        self.assertEqual(response.status_code, 404)


class TutorEngineTests(unittest.TestCase):
    def test_socratic_hint_stages_hold_back_reference_code_until_editorial(self):
        from app.services.tutor import (
            CodeContext, PassportState, TutorContext, generate_hint_stage,
        )

        context = TutorContext(
            code=CodeContext(
                code='def solve(): pass',
                problem_id='example',
                skills_involved=['searching'],
                hints=['concept clue', 'approach clue', 'boundary clue'],
                editorial='Walkthrough',
                solution_code='def solve():\n    return 42',
                error_log='IndexError: list index out of range',
            ),
            passport=PassportState(),
            error_summary='IndexError: list index out of range',
        )
        self.assertEqual(generate_hint_stage(1, context), 'concept clue')
        self.assertEqual(generate_hint_stage(2, context), 'approach clue')
        self.assertIn('IndexError', generate_hint_stage(3, context))
        stage_four = generate_hint_stage(4, context)
        self.assertIn('Pseudocode', stage_four)
        self.assertNotIn('return 42', stage_four)
        self.assertIn('return 42', generate_hint_stage(5, context))

    def test_guardrail_removes_complete_code_from_hints_and_fixes_case(self):
        from app.services.tutor import SocraticGuardrail

        result = SocraticGuardrail.validate_response(
            "THE ANSWER IS below:\n```python\nprint('answer')\n```"
        )
        self.assertNotIn("print('answer')", result)
        self.assertIn('one approach to consider is', result)


if __name__ == '__main__':
    unittest.main()
