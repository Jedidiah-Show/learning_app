"""Guided Project Studio milestones and pathway-safe page behavior."""

import json
import os
import tempfile
import unittest

from app import create_app, db
from app.curriculum import all_modules
from app.models import CoursePlan, CourseProject, User


class ProjectStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.register('studiolearner')

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

    def register(self, username, client=None):
        client = client or self.client
        response = client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        client.post('/onboarding', data={'action': 'skip'})

    def select_project(self, project_id='production-rag'):
        return self.client.post('/api/course-plan/required-project', json={
            'required_project_id': project_id,
        })

    def test_flagship_milestones_persist_and_ci_is_server_verified(self):
        selected = self.select_project()
        self.assertEqual(selected.status_code, 200, selected.get_json())

        with self.app.app_context():
            user = User.query.filter_by(username='studiolearner').one()
            db.session.add(CourseProject(
                user_id=user.id,
                module_id=all_modules()[-1]['id'],
                project=json.dumps({'required_project_id': 'production-rag'}),
                repository_url='https://github.com/learner/production-rag',
                checks_url='https://github.com/learner/production-rag/actions/runs/42',
                checks_verified=True,
            ))
            db.session.commit()

        page = self.client.get('/projects')
        html = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn('Project Studio milestones', html)
        self.assertIn('Design ingestion and access boundaries', html)
        self.assertIn('Verified', html)
        self.assertIn('Open public repository', html)
        self.assertIn('View GitHub Actions run', html)
        self.assertIn('Verified against submitted commit', html)
        self.assertIn('they do not claim the repository contents were verified', html)

        saved = self.client.post('/api/course-plan/project-studio/milestone', json={
            'project_id': 'production-rag',
            'milestone_id': 'design',
            'completed': True,
        })
        self.assertEqual(saved.status_code, 200, saved.get_json())

        refreshed = self.client.get('/projects').get_data(as_text=True)
        self.assertIn('data-milestone-id="design"', refreshed)
        self.assertRegex(
            refreshed,
            r'data-milestone-id="design"[^>]*checked',
        )

        automated = self.client.post(
            '/api/course-plan/project-studio/milestone',
            json={
                'project_id': 'production-rag',
                'milestone_id': 'verified-ci',
                'completed': True,
            },
        )
        self.assertEqual(automated.status_code, 400)

    def test_milestones_are_scoped_to_the_selected_project_and_user(self):
        not_selected = self.client.post(
            '/api/course-plan/project-studio/milestone',
            json={
                'project_id': 'multi-tool-agent-mcp',
                'milestone_id': 'tool-contracts',
                'completed': True,
            },
        )
        self.assertEqual(not_selected.status_code, 409)

        self.assertEqual(self.select_project('multi-tool-agent-mcp').status_code, 200)
        second_client = self.app.test_client()
        self.register('anotherlearner', client=second_client)
        unselected_user = second_client.post(
            '/api/course-plan/project-studio/milestone',
            json={
                'project_id': 'multi-tool-agent-mcp',
                'milestone_id': 'tool-contracts',
                'completed': True,
            },
        )
        self.assertEqual(unselected_user.status_code, 409)

        page = self.client.get('/projects').get_data(as_text=True)
        self.assertIn('Bounded tool-using assistant or MCP server', page)
        self.assertIn('Define bounded tool contracts', page)

    def test_ml_pathway_projects_page_omits_track_form_safely(self):
        with self.app.app_context():
            user = User.query.filter_by(username='studiolearner').one()
            plan = CoursePlan.query.filter_by(user_id=user.id).first()
            if plan is None:
                plan = CoursePlan(user_id=user.id, track='standard')
                db.session.add(plan)
            plan.pathway_destination = 'ml'
            plan.weekly_hours = 10
            db.session.commit()

        response = self.client.get('/projects')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('id="track-form"', html)
        self.assertIn('trackForm?.addEventListener', html)


if __name__ == '__main__':
    unittest.main()
