import os
import tempfile
import unittest

from app import create_app, db
from app.models import CommunityPost, CommunityReply, CoursePlan, CourseProject
from app.models import LessonCompletion, User


class CommunityAndLeaderboardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True)
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

    def register(self, client, username):
        response = client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        return response

    def test_progress_lists_five_monthly_milestones_and_leaderboard_privacy(self):
        self.register(self.client, 'alpha')
        response = self.client.get('/progress')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Monthly milestones', response.data)
        self.assertIn(b'Month 5', response.data)
        self.assertIn('You\u2019re not ranked yet'.encode(), response.data)
        self.assertNotIn(b'alpha</td>', response.data)

        opted_in = self.client.post('/api/leaderboard/visibility', json={'opt_in': True})
        self.assertEqual(opted_in.status_code, 200)
        board = self.client.get('/api/leaderboard').get_json()
        self.assertTrue(board['opted_in'])
        self.assertEqual(board['rank'], 1)
        self.assertEqual(board['entries'][0]['username'], 'alpha')
        ranked_progress = self.client.get('/progress')
        self.assertIn(b'Your rank: #1', ranked_progress.data)

        opted_out = self.client.post('/api/leaderboard/visibility', json={'opt_in': False})
        self.assertEqual(opted_out.status_code, 200)
        board = self.client.get('/api/leaderboard').get_json()
        self.assertFalse(board['opted_in'])
        self.assertEqual(board['participants'], 0)

    def test_leaderboard_orders_opted_in_learners_by_transparent_points(self):
        self.register(self.client, 'alpha')
        second_client = self.app.test_client()
        self.register(second_client, 'beta')
        self.client.post('/api/leaderboard/visibility', json={'opt_in': True})
        second_client.post('/api/leaderboard/visibility', json={'opt_in': True})
        with self.app.app_context():
            alpha = User.query.filter_by(username='alpha').one()
            beta = User.query.filter_by(username='beta').one()
            for index in range(3):
                db.session.add(LessonCompletion(
                    user_id=alpha.id, lesson_id=f'alpha-{index}', subject_id='00',
                    day_number=index + 1, completed=True,
                ))
            for index in range(2):
                db.session.add(LessonCompletion(
                    user_id=beta.id, lesson_id=f'beta-{index}', subject_id='00',
                    day_number=index + 1, completed=True,
                ))
            db.session.add(CourseProject(
                user_id=beta.id, module_id='00', project='{}', completed=True,
            ))
            db.session.commit()
        board = self.client.get('/api/leaderboard').get_json()
        self.assertEqual(board['entries'][0]['username'], 'beta')
        self.assertEqual(board['entries'][0]['points'], 70)
        self.assertEqual(board['entries'][1]['username'], 'alpha')
        self.assertEqual(board['rank'], 2)
        self.assertEqual(board['lesson_points'], 10)
        self.assertEqual(board['project_points'], 50)

    def test_learners_can_create_reply_and_remove_their_own_discussion(self):
        self.register(self.client, 'author')
        other_client = self.app.test_client()
        self.register(other_client, 'collaborator')
        created = self.client.post('/community/posts', data={
            'topic': 'RAG',
            'title': 'How are you evaluating retrieval quality?',
            'body': 'I am comparing rerankers and would like to discuss a useful test set.',
        })
        self.assertEqual(created.status_code, 302)
        with self.app.app_context():
            post = CommunityPost.query.one()
            post_id = post.id
        page = other_client.get('/community')
        self.assertIn(b'How are you evaluating retrieval quality?', page.data)
        reply = other_client.post(f'/community/posts/{post_id}/replies', data={
            'body': 'Try measuring recall at several k values against labeled questions.',
        })
        self.assertEqual(reply.status_code, 302)
        detail = self.client.get(f'/community/posts/{post_id}')
        self.assertIn(b'collaborator', detail.data)
        self.assertIn(b'recall at several k values', detail.data)
        with self.app.app_context():
            self.assertEqual(CommunityReply.query.count(), 1)
            self.assertEqual(CoursePlan.query.count(), 0)
        removed = self.client.post(f'/community/posts/{post_id}/delete', data={})
        self.assertEqual(removed.status_code, 302)
        self.assertEqual(other_client.get(f'/community/posts/{post_id}').status_code, 404)
        with self.app.app_context():
            self.assertEqual(CommunityPost.query.count(), 0)
            self.assertEqual(CommunityReply.query.count(), 0)

    def test_community_rejects_invalid_topics_and_oversized_replies(self):
        self.register(self.client, 'learner')
        invalid = self.client.post('/community/posts', data={
            'topic': 'not a topic', 'title': 'Question', 'body': 'Details',
        })
        self.assertEqual(invalid.status_code, 302)
        with self.app.app_context():
            self.assertEqual(CommunityPost.query.count(), 0)
            post = CommunityPost(
                user_id=User.query.one().id, topic='General', title='Question', body='Details',
            )
            db.session.add(post)
            db.session.commit()
            post_id = post.id
        too_long = self.client.post(
            f'/community/posts/{post_id}/replies', data={'body': 'x' * 3001}
        )
        self.assertEqual(too_long.status_code, 302)
        with self.app.app_context():
            self.assertEqual(CommunityReply.query.count(), 0)
