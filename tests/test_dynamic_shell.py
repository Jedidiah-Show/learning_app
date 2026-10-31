"""The dashboard grid, nav shell, and app name follow the chosen pathway.

A learner who confirms ``pathway_destination = 'ml'`` studies the shared
foundation (modules 00-02) and the ML pathway's four modules.  Modules 03-12
are the AI continuation and belong to a different course, so they must never
appear in that learner's curriculum grid, header totals, or next-step pointers.
The nav follows the same rule: the learner's own pathway sits directly under
Dashboard, the brand subtitle names it, and the long app name is
``RUACH AI & ML Engineering`` everywhere it is rendered.
"""

import json
import os
import re
import tempfile
import unittest

from app import create_app, db
from app.curriculum import all_modules, curriculum
from app.models import CoursePlan, CourseProject, LessonCompletion, User


FOUNDATION_IDS = ('00', '01', '02')
FOUNDATION_TITLES = (
    'AI Engineering Foundations',
    'Python for AI Engineers',
    'Backend Engineering',
)
ML_TITLES = (
    'Data and problem formulation',
    'Classical machine learning',
    'Reproducible training',
    'Production machine learning',
)
# Modules 03-12: the AI-specific continuation an ML learner never signs up for.
AI_ONLY_TITLES = (
    'LLM Fundamentals',
    'LLM Application Engineering',
    'RAG (Retrieval-Augmented Generation)',
    'AI Agents',
    'Agent Orchestration',
    'MCP (Model Context Protocol)',
    'Production AI Engineering',
    'Docker & Deployment',
    'AI System Design',
    'Final Capstone: Build and Review an AI System',
)


class DynamicShellTestCase(unittest.TestCase):
    """Shared setup: one registered learner whose destination can be switched."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        response = self.client.post('/register', data={
            'username': 'shelllearner',
            'email': 'shelllearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

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

    def _set_destination(self, destination):
        with self.app.app_context():
            user = User.query.filter_by(username='shelllearner').one()
            plan = CoursePlan.query.filter_by(user_id=user.id).first()
            if plan is None:
                plan = CoursePlan(user_id=user.id, track='standard')
                db.session.add(plan)
            plan.skill_level = 'new'
            plan.weekly_hours = 10
            plan.pathway_destination = destination
            db.session.commit()

    def _page(self, path='/'):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    @staticmethod
    def _nav(html):
        match = re.search(r'<nav id="app-navigation".*?</nav>', html, re.S)
        assert match, 'the nav shell did not render'
        return match.group(0)

    @staticmethod
    def _subtitle(html):
        match = re.search(r'brand-subtitle[^>]*>([^<]*)<', html)
        assert match, 'the brand subtitle did not render'
        return match.group(1).strip()


class DashboardCurriculumGridTests(DynamicShellTestCase):
    """The "Your curriculum" grid is scoped to the learner's pathway."""

    def test_ml_destination_shows_foundation_plus_pathway_and_hides_ai_modules(self):
        self._set_destination('ml')
        html = self._page()

        self.assertIn('7 modules · 64 lessons', html)
        for title in FOUNDATION_TITLES + ML_TITLES:
            self.assertIn(title, html)
        for title in AI_ONLY_TITLES:
            self.assertNotIn(title, html)

    def test_grid_badges_disambiguate_the_colliding_module_numbers(self):
        # The foundation numbers 0-2 and the pathway's 1-4 would otherwise both
        # render as "Module 1"/"Module 2" in the same grid.
        self._set_destination('ml')
        html = self._page()

        self.assertIn('Shared foundation · Module 0', html)
        self.assertIn('Shared foundation · Module 1', html)
        self.assertIn('Shared foundation · Module 2', html)
        self.assertIn('ML pathway · Module 1', html)
        self.assertIn('ML pathway · Module 4', html)

    def test_ai_and_unset_destinations_keep_the_full_course(self):
        for destination in ('ai', None):
            with self.subTest(destination=destination):
                self._set_destination(destination)
                html = self._page()

                self.assertIn('13 modules · 213 lessons', html)
                self.assertIn('LLM Fundamentals', html)
                self.assertNotIn('ML pathway · Module 1', html)
                self.assertNotIn('Shared foundation · Module 0', html)

    def test_foundation_complete_ml_learner_is_never_pointed_at_an_ai_module(self):
        # Once the shared foundation is finished the AI course's own next step
        # would be a module 03+ lesson, which must not surface for this learner.
        self._set_destination('ml')
        with self.app.app_context():
            user = User.query.filter_by(username='shelllearner').one()
            for module in all_modules():
                if module['id'] not in FOUNDATION_IDS:
                    continue
                for index, lesson in enumerate(module['lessons'], start=1):
                    db.session.add(LessonCompletion(
                        user_id=user.id, lesson_id=lesson['id'],
                        subject_id=module['id'], day_number=index,
                        completed=True,
                    ))
                db.session.add(CourseProject(
                    user_id=user.id, module_id=module['id'],
                    project='{}', completed=True,
                ))
            db.session.commit()

        html = self._page()

        self.assertIn('7 modules · 64 lessons', html)
        for title in AI_ONLY_TITLES:
            self.assertNotIn(title, html)
        # The foundation pointer is spent, so no generic "continue" card is left
        # pointing at the AI course; the pathway card carries the next step.
        self.assertNotIn('Continue your course', html)
        self.assertIn('Continue your pathway', html)


class PathwayAwareNavTests(DynamicShellTestCase):
    """The nav orders the learner's own pathway first and names it."""

    def test_ml_learner_opens_the_pathway_directly_under_dashboard(self):
        self._set_destination('ml')
        # Checked on a page other than the dashboard so the shell, not the
        # route, is what is being exercised.
        nav = self._nav(self._page('/lessons'))

        order = re.findall(r'>(?:Course Lessons|ML Pathway)<', nav)
        self.assertEqual(order, ['>ML Pathway<', '>Course Lessons<'])
        self.assertLess(
            nav.find('/specializations/machine-learning'),
            nav.find('href="/lessons"'),
        )
        self.assertEqual(self._subtitle(self._page()), 'ML Engineering')

    def test_ai_and_undecided_learners_keep_course_lessons_first(self):
        for destination, subtitle in (
            ('ai', 'AI Engineering'),
            (None, 'AI & ML Engineering'),
        ):
            with self.subTest(destination=destination):
                self._set_destination(destination)
                nav = self._nav(self._page())

                order = re.findall(r'>(?:Course Lessons|ML Pathway)<', nav)
                self.assertEqual(order, ['>Course Lessons<', '>ML Pathway<'])
                self.assertEqual(self._subtitle(self._page()), subtitle)

    def test_the_other_pathway_stays_reachable_as_the_alternate(self):
        self._set_destination('ml')
        nav = self._nav(self._page())
        # An ML learner still needs the shared foundation that lives on /lessons.
        self.assertIn('href="/lessons"', nav)
        self.assertIn('href="/specializations/machine-learning"', nav)

        self._set_destination('ai')
        nav = self._nav(self._page())
        self.assertIn('href="/lessons"', nav)
        self.assertIn('href="/specializations/machine-learning"', nav)


class BrandRenameTests(DynamicShellTestCase):
    """The long app name now covers both disciplines wherever it renders."""

    def test_rendered_pages_carry_the_new_name_and_drop_the_old_one(self):
        for path in ('/', '/lessons'):
            with self.subTest(path=path):
                html = self._page(path)
                self.assertIn('RUACH AI & ML Engineering', html)
                # Deliberate substring: the new name does not contain the old.
                self.assertNotIn('RUACH AI Engineering', html)

        # The signed-out shell uses a separate session; /login redirects when a
        # learner is already authenticated.
        guest = self.app.test_client()
        response = guest.get('/login')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('RUACH AI & ML Engineering', html)
        self.assertNotIn('RUACH AI Engineering', html)

    def test_course_title_and_pwa_manifest_use_the_new_name(self):
        self.assertEqual(curriculum()['course']['title'], 'RUACH AI & ML Engineering')

        manifest_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'manifest', 'site.webmanifest',
        )
        with open(manifest_path, encoding='utf-8') as source:
            manifest = json.load(source)
        self.assertEqual(manifest['name'], 'RUACH AI & ML Engineering')
        # The compact wordmark stays as it is.
        self.assertEqual(manifest['short_name'], 'RUACH')


if __name__ == '__main__':
    unittest.main()
