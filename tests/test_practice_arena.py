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
    def test_all_arena_problems_defensive_deep_copy(self):
        p1 = all_arena_problems()
        key = next(iter(p1))
        p1[key]['hints'].append('mutated_hint')
        p2 = all_arena_problems()
        self.assertNotIn('mutated_hint', p2[key]['hints'])

    def test_get_arena_problem_supplies_fallback_judge_tests(self):
        from app.practice_arena import get_arena_problem
        for problem_id, original in all_arena_problems().items():
            problem = get_arena_problem(problem_id)
            self.assertIsNotNone(problem)
            self.assertIn('judge_tests', problem)
            self.assertIsInstance(problem['judge_tests'], str)
            if original.get('source') == 'arena':
                self.assertTrue(problem['judge_tests'])

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

    def test_every_problem_has_a_dedicated_hidden_suite_that_passes(self):
        # Hidden suites are the judge's source of truth; the public browser
        # checks are only a fallback for problems without one. Every published
        # problem now ships a dedicated suite that the reference solution passes.
        import ast
        import asyncio
        import inspect
        for problem in all_arena_problems().values():
            with self.subTest(problem=problem['id']):
                suite = problem['judge_tests']
                self.assertTrue(suite.strip())
                self.assertNotEqual(
                    suite.strip(), problem['browser_checks'].strip(),
                    'judge_tests must not copy the public browser checks',
                )
                compile(
                    suite, problem['id'], 'exec',
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )
                namespace = {'__name__': '__main__'}
                source = problem['solution_code'] + '\n\n' + suite
                code = compile(
                    source, problem['id'], 'exec',
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                )
                outcome = eval(code, namespace)
                if inspect.isawaitable(outcome):
                    asyncio.run(outcome)

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

    def test_machine_learning_problems_are_published_and_pass_checks(self):
        problems = all_arena_problems()
        ml = [
            problem for problem in problems.values()
            if problem['track'] == 'machine-learning'
        ]
        self.assertEqual(len(ml), 15)
        for problem in ml:
            with self.subTest(problem=problem['id']):
                self.assertIn(problem['difficulty'], DIFFICULTIES)
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

    def test_machine_learning_feature_scaling_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-data-preparation-feature-scaling']
        self.assertEqual(problem['topic'], 'ml-data-analysis')
        self.assertEqual(problem['skills'], ['data-preparation', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_train_validation_test_split_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-data-preparation-train-validation-test-split']
        self.assertEqual(problem['topic'], 'ml-data-analysis')
        self.assertEqual(problem['skills'], ['data-preparation', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_precision_recall_f1_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-classification-precision-recall-f1']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['classification', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_overfitting_underfitting_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-evaluation-overfitting-underfitting']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['model-evaluation', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_forward_propagation_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-deep-learning-forward-propagation']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['deep-learning', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_model_serialization_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-engineering-model-serialization']
        self.assertEqual(problem['topic'], 'ml-data-analysis')
        self.assertEqual(problem['skills'], ['ml-deployment', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_cross_validation_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-evaluation-cross-validation']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['model-evaluation', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_hyperparameter_grid_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-optimisation-hyperparameter-grid']
        self.assertEqual(problem['topic'], 'ml-statistics')
        self.assertEqual(problem['skills'], ['optimisation', 'python'])
        namespace = {}
        exec(problem['solution_code'], namespace)
        exec(problem['browser_checks'], namespace)

    def test_machine_learning_visualisation_summary_problem(self):
        problems = all_arena_problems()
        problem = problems['ml-data-analysis-visualisation-summary']
        self.assertEqual(problem['topic'], 'ml-data-analysis')
        self.assertEqual(problem['skills'], ['data-analysis', 'python'])
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
    def test_submit_fails_closed_when_no_authoritative_judge_is_configured(self):
        self.register('unavailablejudge')
        self.app.config.update(
            TESTING=False, CSRF_ENABLED=False, JUDGE_SUBMISSIONS_ENABLED=False,
        )
        response = self.client.post(
            '/arena/api/problems/algo-binary-search/submit',
            json={'code': 'def binary_search(numbers, target):\n    return -1\n'},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn('temporarily unavailable', response.get_json()['error'])

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
        self.assertNotIn('judge_tests', data['problem'])
        self.assertNotIn('hints', data['problem'])
        self.assertEqual(data['status'], 'not-started')

    def test_legacy_exercise_with_dedicated_suite_is_gradeable(self):
        # Every legacy exercise now ships a dedicated hidden judge_tests
        # suite, so the old "not gradeable" 409 path only applies to data
        # built without a suite. A normal exercise submit enqueues durable
        # judge work instead.
        self.register('legacylearner')
        self.app.config.update(TESTING=False, CSRF_ENABLED=False, JUDGE_SUBMISSIONS_ENABLED=True)
        response = self.client.post(
            '/arena/api/problems/first-python-greeting/submit',
            json={'code': 'def greet(name):\n    return f"Hello, {name}!"\n\nprint(greet("AI engineering"))\n'},
        )
        self.assertEqual(response.status_code, 202)
        payload = response.get_json()
        self.assertEqual(payload['status'], 'queued')
        self.assertEqual(payload['verdict'], 'PENDING')

    def test_submit_returns_409_when_problem_has_no_hidden_suite(self):
        # Defensive guard for data built without a dedicated hidden suite.
        # All shipped problems have one, so the branch is exercised here by
        # patching the catalogue lookup.
        self.register('nosuitelearner')
        self.app.config.update(TESTING=False, CSRF_ENABLED=False, JUDGE_SUBMISSIONS_ENABLED=True)
        suiteless = {
            'id': 'synthetic-exercise', 'source': 'lesson', 'track': 'algorithms',
            'topic': 'arrays-strings', 'title': 'Synthetic', 'statement': 'x',
            'difficulty': 'beginner', 'skills': ['python'], 'prerequisites': [],
            'starter_code': 'pass', 'solution_code': 'pass',
            'browser_checks': 'assert True', 'judge_tests': '',
            'hints': [], 'editorial': '',
        }
        with patch('app.routes.practice_arena.get_arena_problem', return_value=suiteless):
            response = self.client.post(
                '/arena/api/problems/synthetic-exercise/submit',
                json={'code': 'pass\n'},
            )
        self.assertEqual(response.status_code, 409)
        self.assertIn('Verified grading is not available', response.get_json()['error'])

    def test_worker_passes_the_private_suite_not_the_public_checks(self):
        from app.practice_arena import get_arena_problem

        self.register('suitelearner')
        with self.app.app_context():
            user = User.query.filter_by(username='suitelearner').one()
            db.session.add(Submission(
                id='judge-suite-submission',
                user_id=user.id,
                problem_id='algo-binary-search',
                code_snapshot='def binary_search(numbers, target): return -1',
                verdict='PENDING',
            ))
            db.session.commit()
            problem = get_arena_problem('algo-binary-search')

        from app.services.judge import JudgeResult
        from app.services.judge_worker import process_next_submission

        result = JudgeResult()
        result.verdict = 'WRONG_ANSWER'
        with patch(
            'app.services.judge_worker.execute_in_sandbox',
            return_value=result,
        ) as execute:
            self.assertTrue(process_next_submission(self.app))

        _, test_suite = execute.call_args.args
        self.assertEqual(test_suite, problem['judge_tests'])

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

    def test_run_fails_closed_when_no_authoritative_judge_is_configured(self):
        self.register('unavailablejudge')
        self.app.config.update(
            TESTING=False, CSRF_ENABLED=False, JUDGE_SUBMISSIONS_ENABLED=False,
        )
        response = self.client.post(
            '/arena/api/problems/algo-binary-search/run',
            json={'code': 'def binary_search(numbers, target):\n    return -1\n'},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn('unavailable', response.get_json()['error'])

    def test_run_queues_valid_code_without_executing_on_the_web_request(self):
        self.register('arena')
        response = self.client.post(
            '/arena/api/problems/algo-binary-search/run',
            json={'code': 'def binary_search(numbers, target):\n    return -1\n'},
        )
        self.assertEqual(response.status_code, 202)
        payload = response.get_json()
        for key in ('run_id', 'status', 'stream_url'):
            self.assertIn(key, payload)
        self.assertEqual(payload['status'], 'queued')
        with self.app.app_context():
            record = db.session.get(Submission, payload['run_id'])
            self.assertEqual(record.mode, 'run')
            self.assertEqual(record.verdict, 'PENDING')

    def test_worker_records_unavailable_sandbox_as_terminal_run_error(self):
        self.register('arenafallback')
        from app.services.judge import JudgeResult
        from app.services.judge_worker import process_next_submission
        mock_result = JudgeResult(
            verdict='INTERNAL_ERROR',
            error_details='Sandbox runtime is unavailable',
        )
        queued = self.client.post(
            '/arena/api/problems/algo-binary-search/run',
            json={'code': 'def binary_search(numbers, target):\n    return -1\n'},
        )
        with patch(
            'app.services.judge_worker.execute_in_sandbox',
            return_value=mock_result,
        ):
            self.assertTrue(process_next_submission(self.app))
        status = self.client.get(
            f"/arena/api/submissions/{queued.get_json()['run_id']}",
        )
        self.assertEqual(status.get_json()['verdict'], 'INTERNAL_ERROR')
        self.assertIn('unavailable', status.get_json()['error_details'])

    def test_run_rejects_invalid_source(self):
        self.register('arena')
        invalid = self.client.post(
            '/arena/api/problems/algo-binary-search/run',
            json={'code': 'def broken(:'},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_async_run_queues_and_streams_sse_events(self):
        from app.services.judge import JudgeResult
        from app.services.judge_worker import process_next_submission

        self.register('streamlearner')
        queued = self.client.post(
            '/arena/api/problems/algo-binary-search/run',
            json={
                'code': 'def binary_search(numbers, target): return -1',
                'async': True,
            },
        )
        self.assertEqual(queued.status_code, 202)
        data = queued.get_json()
        self.assertEqual(data['status'], 'queued')
        self.assertIn('stream_url', data)
        run_id = data['run_id']

        mock_result = JudgeResult(
            verdict='COMPLETED',
            output='Found target at -1',
            execution_time_ms=18,
            memory_kb=1024,
        )
        with patch('app.services.judge_worker.execute_in_sandbox', return_value=mock_result):
            self.assertTrue(process_next_submission(self.app))

        stream_resp = self.client.get(data['stream_url'])
        self.assertEqual(stream_resp.status_code, 200)
        self.assertIn('text/event-stream', stream_resp.mimetype)
        stream_text = stream_resp.get_data(as_text=True)
        self.assertIn('data: ', stream_text)
        self.assertIn('COMPLETED', stream_text)
        self.assertIn('Found target at -1', stream_text)

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

    def test_ml_aware_concept_hint_includes_statistics_context(self):
        from app.services.tutor import (
            CodeContext, PassportState, TutorContext, generate_hint_stage,
        )
        context = TutorContext(
            code=CodeContext(
                code='def f(x): pass',
                problem_id='ml-statistics-descriptive-statistics',
                skills_involved=['statistics', 'python'],
                hints=[],
                editorial='',
                solution_code='',
            ),
            passport=PassportState(),
            error_summary='',
        )
        hint = generate_hint_stage(1, context)
        self.assertIn('statistics', hint.lower())
        self.assertIn('mean', hint.lower())
        self.assertIn('median', hint.lower())
        self.assertIn('standard deviation', hint.lower())

    def test_ml_aware_edge_case_hint_includes_statistics_context(self):
        from app.services.tutor import (
            CodeContext, PassportState, TutorContext, generate_hint_stage,
        )
        context = TutorContext(
            code=CodeContext(
                code='def f(x): pass',
                problem_id='ml-statistics-descriptive-statistics',
                skills_involved=['statistics', 'python'],
                hints=[],
                editorial='',
                solution_code='',
            ),
            passport=PassportState(),
            error_summary='',
        )
        hint = generate_hint_stage(3, context)
        self.assertIn('empty inputs', hint.lower())
        self.assertIn('zero standard deviation', hint.lower())

    def test_ml_aware_pseudocode_hint_includes_classification_context(self):
        from app.services.tutor import (
            CodeContext, PassportState, TutorContext, generate_hint_stage,
        )
        context = TutorContext(
            code=CodeContext(
                code='def f(x): pass',
                problem_id='ml-classification-confusion-matrix',
                skills_involved=['classification', 'python'],
                hints=[],
                editorial='',
                solution_code='',
            ),
            passport=PassportState(),
            error_summary='',
        )
        hint = generate_hint_stage(4, context)
        self.assertIn('confusion-matrix', hint.lower())
        self.assertIn('actual and predicted', hint.lower())

    def test_diagnose_knowledge_gaps_detects_ml_patterns(self):
        from app.services.tutor import (
            CodeContext, PassportState, TutorContext, diagnose_knowledge_gaps,
        )
        context = TutorContext(
            code=CodeContext(
                code='def f(x): pass',
                problem_id='ml-statistics-descriptive-statistics',
                skills_involved=['statistics', 'python'],
                hints=[],
                editorial='',
                solution_code='',
                error_log='ZeroDivisionError: division by zero in mean',
            ),
            passport=PassportState(),
            error_summary='ZeroDivisionError: division by zero in mean',
        )
        result = diagnose_knowledge_gaps(context)
        self.assertTrue(
            any('division by zero' in g.lower() for g in result['diagnosed_gaps']),
            f"Expected ML division-by-zero gap, got: {result['diagnosed_gaps']}"
        )

    def test_diagnose_knowledge_gaps_detects_classification_patterns(self):
        from app.services.tutor import (
            CodeContext, PassportState, TutorContext, diagnose_knowledge_gaps,
        )
        context = TutorContext(
            code=CodeContext(
                code='def f(x): pass',
                problem_id='ml-classification-confusion-matrix',
                skills_involved=['classification', 'python'],
                hints=[],
                editorial='',
                solution_code='',
                error_log='precision and recall calculation failed',
            ),
            passport=PassportState(),
            error_summary='precision and recall calculation failed',
        )
        result = diagnose_knowledge_gaps(context)
        self.assertTrue(
            any('evaluation metrics' in g.lower() for g in result['diagnosed_gaps']),
            f"Expected ML evaluation-metrics gap, got: {result['diagnosed_gaps']}"
        )

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
