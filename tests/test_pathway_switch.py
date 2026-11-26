"""Instant, self-service pathway switching (AI Engineering ↔ Machine Learning).

The product rule:

* Everyone starts with the shared foundations; the specialisation is chosen
  then or later — never locked in.
* Switching is instant, free, and available at any time. It changes which
  pathway the whole app leads with and nothing else: enrolments, lesson
  completions, projects, and credentials for the other pathway are untouched.
* ``CoursePlan.pathway_destination`` is the explicit focus the app reads;
  enrolments are a record of what the learner has opted into.
"""

import os
import tempfile
import unittest

from app import create_app, db
from app.models import (
    CoursePlan, LearnerPathwayEnrollment, LessonCompletion,
    MLSpecializationLessonCompletion, User,
)
from app.pathway_scope import (
    destination_for, enrol_learner,
    seed_learning_pathways, switch_pathway,
)

ML_PATHWAY_ID = 'machine-learning-engineering'

ML_ANSWERS = {
    'fit.outcome': 'trained-model',
    'fit.weekend': 'train-evaluate',
    'fit.curiosity': 'how-knows',
    'fit.pride': 'data-insight',
    'fit.workday': 'experiments',
}


class PathwaySwitchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
            seed_learning_pathways()
        self.client = self.app.test_client()
        self.client.post('/register', data={
            'username': 'switchlearner',
            'email': 'switchlearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)

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

    def _complete_setup(self):
        self.client.post('/onboarding', data={
            'skill_level': 'new', 'weekly_hours': '10-12', 'track': 'standard',
        })
        self.client.post('/onboarding/pathway', data=ML_ANSWERS)
        self.client.post('/onboarding/pathway', data={
            'action': 'confirm', 'pathway_destination': 'ml',
        })

    def _uid(self):
        with self.app.app_context():
            return User.query.filter_by(username='switchlearner').one().id

    def _plan(self):
        with self.app.app_context():
            return CoursePlan.query.filter_by(user_id=self._uid()).one()

    def _enrolment_statuses(self):
        with self.app.app_context():
            return {
                row.pathway_id: row.status
                for row in LearnerPathwayEnrollment.query.filter_by(
                    learner_id=self._uid()).all()
            }

    # ---------------------------------------------------- service level

    def test_switch_requires_a_specialization(self):
        with self.app.app_context():
            with self.assertRaises(ValueError):
                switch_pathway(self._uid(), 'blockchain')
            with self.assertRaises(ValueError):
                switch_pathway(self._uid(), 'shared-foundations')

    def test_switch_is_allowed_at_any_time_and_keeps_both_enrolments(self):
        with self.app.app_context():
            uid = self._uid()
            # Learner confirmed AI at onboarding; switching needs no foundation.
            enrol_learner(uid, 'shared-foundations')
            enrol_learner(uid, 'ai-engineering')
            plan = CoursePlan.query.filter_by(user_id=uid).first() or CoursePlan(
                user_id=uid, track='standard', pathway_destination='ai',
            )
            plan.pathway_destination = 'ai'
            db.session.add(plan)
            db.session.commit()

            switch_pathway(uid, 'machine-learning')
            self.assertEqual(
                CoursePlan.query.filter_by(user_id=uid).one().pathway_destination,
                'machine-learning',
            )
            self.assertEqual(
                self._enrolment_statuses(),
                {'shared-foundations': 'ENROLLED',
                 'ai-engineering': 'ENROLLED',
                 'machine-learning': 'ENROLLED'},
            )

            switch_pathway(uid, 'ai-engineering')
            self.assertEqual(
                CoursePlan.query.filter_by(user_id=uid).one().pathway_destination,
                'ai-engineering',
            )
            # Switching back and forth never unenrolled AI Engineering.
            self.assertEqual(
                self._enrolment_statuses()['ai-engineering'], 'ENROLLED')

    def test_explicit_choice_beats_the_historical_ai_priority(self):
        with self.app.app_context():
            uid = self._uid()
            enrol_learner(uid, 'ai-engineering')
            enrol_learner(uid, 'machine-learning')
            plan = CoursePlan(user_id=uid, track='standard',
                              pathway_destination='machine-learning')
            db.session.add(plan)
            db.session.commit()
            self.assertEqual(destination_for(uid), 'machine-learning')
            switch_pathway(uid, 'ai-engineering')
            self.assertEqual(destination_for(uid), 'ai-engineering')

    def test_switching_revives_a_paused_enrolment_and_leaves_the_other_paused(self):
        with self.app.app_context():
            uid = self._uid()
            enrol_learner(uid, 'ai-engineering')
            enrol_learner(uid, 'machine-learning')
            ml_row = LearnerPathwayEnrollment.query.filter_by(
                learner_id=uid, pathway_id='machine-learning').one()
            ml_row.status = 'PAUSED'
            db.session.commit()
            switch_pathway(uid, 'machine-learning')
            statuses = self._enrolment_statuses()
            self.assertEqual(statuses['machine-learning'], 'ENROLLED')
            self.assertEqual(statuses['ai-engineering'], 'ENROLLED')

    def test_progress_in_both_pathways_survives_any_number_of_switches(self):
        with self.app.app_context():
            uid = self._uid()
            db.session.add(LessonCompletion(
                user_id=uid, lesson_id='03.1', subject_id='03',
                day_number=1, completed=True,
            ))
            db.session.add(MLSpecializationLessonCompletion(
                user_id=uid, pathway_id=ML_PATHWAY_ID, lesson_id='mle.1.1',
            ))
            db.session.commit()

            for target in ('machine-learning', 'ai-engineering', 'machine-learning'):
                switch_pathway(uid, target)

            ai_done = {row.lesson_id for row in LessonCompletion.query.filter_by(
                user_id=uid, completed=True).all()}
            ml_done = {row.lesson_id for row in
                       MLSpecializationLessonCompletion.query.filter_by(
                           user_id=uid, pathway_id=ML_PATHWAY_ID).all()}
            self.assertEqual(ai_done, {'03.1'})
            self.assertEqual(ml_done, {'mle.1.1'})

    # ---------------------------------------------------- web flow

    def test_switch_route_requires_login(self):
        anon = self.app.test_client()
        response = anon.post('/account/pathway-switch',
                             data={'pathway_id': 'machine-learning'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_switch_route_changes_the_active_pathway_and_redirects(self):
        self._complete_setup()
        response = self.client.post('/account/pathway-switch', data={
            'pathway_id': 'ai-engineering', 'next': '/',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self._plan().pathway_destination, 'ai-engineering')

    def test_switch_route_rejects_a_non_specialization(self):
        self._complete_setup()
        response = self.client.post('/account/pathway-switch', data={
            'pathway_id': 'undecided',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._plan().pathway_destination, 'ml')

    def test_undecided_dashboard_invites_the_choice_and_switch_closes_it(self):
        self.client.post('/onboarding', data={
            'skill_level': 'new', 'weekly_hours': '10-12', 'track': 'standard',
        })
        self.client.post('/onboarding/pathway', data={'action': 'skip'})
        page = self.client.get('/').get_data(as_text=True)
        self.assertIn('Choose your specialization', page)

        self.client.post('/account/pathway-switch', data={
            'pathway_id': 'machine-learning', 'next': '/',
        })
        page = self.client.get('/').get_data(as_text=True)
        self.assertNotIn('Choose your specialization', page)

    def test_nav_exposes_the_one_click_switcher_on_every_page(self):
        self._complete_setup()
        for path in ('/', '/lessons', '/progress'):
            page = self.client.get(path).get_data(as_text=True)
            self.assertIn('name="pathway_id" value="ai-engineering"', page, path)
            self.assertIn('name="pathway_id" value="machine-learning"', page, path)

    def test_profile_shows_both_pathways_and_no_lock_copy(self):
        self._complete_setup()
        page = self.client.get('/profile').get_data(as_text=True)
        self.assertIn('Switch to AI Engineering', page)
        self.assertNotIn('Locked', page)
        self.assertNotIn('one-time pathway change', page)

    def test_onboarding_confirm_enrols_in_foundations_and_the_choice(self):
        self._complete_setup()
        self.assertEqual(
            self._enrolment_statuses(),
            {'shared-foundations': 'ENROLLED', 'machine-learning': 'ENROLLED'},
        )

    def test_skip_enrols_foundations_only(self):
        self.client.post('/onboarding', data={
            'skill_level': 'new', 'weekly_hours': '10-12', 'track': 'standard',
        })
        self.client.post('/onboarding/pathway', data={'action': 'skip'})
        self.assertEqual(
            self._enrolment_statuses(),
            {'shared-foundations': 'ENROLLED'},
        )


if __name__ == '__main__':
    unittest.main()
