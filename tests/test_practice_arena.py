"""Practice Arena: catalogue, workspace, and honest progress labels."""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import PracticeWorkspace, User
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
    def test_two_tracks_are_present_and_ai_is_primary(self):
        self.assertEqual(
            [track['id'] for track in TRACKS],
            ['ai-engineering', 'algorithms'],
        )
        self.assertTrue(TRACKS[0]['primary'])
        self.assertFalse(TRACKS[1]['primary'])

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
        self.assertIn('formative practice feedback, not secure grading', html)
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
        self.assertIn('browser_checks', data['problem'])
        self.assertEqual(data['status'], 'not-started')

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


if __name__ == '__main__':
    unittest.main()
