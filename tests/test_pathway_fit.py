"""Pathway fit assessment: scoring, the two-step onboarding flow, and the
dashboard lead switch (Stage D item 1).

The assessment must suit brand-new learners, need no external services, and
propose rather than write: the learner's explicit confirmation is what stores
``CoursePlan.pathway_destination``, and only that value reorders the dashboard.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, db
from app.models import CoursePlan, CourseProject, User
from app.pathway_fit import (
    PATHWAY_DESTINATIONS, PATHWAY_FIT_QUESTIONS, PROPOSAL_MIN_LEAD,
    PathwayFitError, pathway_fit_question, score_pathway_fit,
    validate_pathway_fit_answers,
)


AI_ANSWERS = {
    'fit.outcome': 'product-feature',
    'fit.weekend': 'model-feature',
    'fit.curiosity': 'how-built',
    'fit.pride': 'ship-ai',
    'fit.workday': 'design-ai',
}
ML_ANSWERS = {
    'fit.outcome': 'trained-model',
    'fit.weekend': 'train-evaluate',
    'fit.curiosity': 'how-knows',
    'fit.pride': 'data-insight',
    'fit.workday': 'experiments',
}
BOTH_ANSWERS = {
    'fit.outcome': 'both',
    'fit.weekend': 'either',
    'fit.curiosity': 'both-wonder',
    'fit.pride': 'useful-either',
    'fit.workday': 'mixed-day',
}


class PathwayFitScoringTests(unittest.TestCase):
    """Pure scoring behaviour — no app, no database, no network."""

    def test_questions_are_deterministic_scenarios_not_a_knowledge_test(self):
        self.assertEqual(len(PATHWAY_FIT_QUESTIONS), 5)
        for question in PATHWAY_FIT_QUESTIONS:
            self.assertEqual(len(question['options']), 3)
            for option in question['options']:
                self.assertIn('ai', option['weights'])
                self.assertIn('ml', option['weights'])
        self.assertIs(pathway_fit_question('fit.outcome'), PATHWAY_FIT_QUESTIONS[0])
        self.assertIsNone(pathway_fit_question('missing.question'))

    def test_clear_preferences_propose_the_matching_pathway(self):
        ai = score_pathway_fit(AI_ANSWERS)
        self.assertEqual(ai['proposal'], 'ai')
        self.assertEqual(ai['ai_score'], 10)
        self.assertEqual(ai['ml_score'], 0)
        self.assertEqual(ai['lead'], 10)

        ml = score_pathway_fit(ML_ANSWERS)
        self.assertEqual(ml['proposal'], 'ml')
        self.assertEqual(ml['ai_score'], 0)
        self.assertEqual(ml['ml_score'], 10)

    def test_all_moderate_answers_are_too_close_to_call(self):
        result = score_pathway_fit(BOTH_ANSWERS)
        self.assertEqual(result['proposal'], 'undecided')
        self.assertEqual(result['ai_score'], 5)
        self.assertEqual(result['ml_score'], 5)
        self.assertEqual(result['lead'], 0)

    def test_a_2_point_lead_stays_undecided_but_4_points_proposes(self):
        # Weights are even per side, so reachable leads are 0, 2, 4 ... The
        # threshold therefore reads as "at least a two-question margin".
        self.assertGreater(PROPOSAL_MIN_LEAD, 2)
        slim = dict(ML_ANSWERS)
        slim.update({
            'fit.outcome': 'product-feature',   # ai +2
            'fit.weekend': 'model-feature',     # ai +2
            'fit.curiosity': 'both-wonder',     # +1 / +1
            'fit.pride': 'useful-either',       # +1 / +1
            'fit.workday': 'experiments',       # ml +2
        })
        result = score_pathway_fit(slim)
        self.assertEqual((result['ai_score'], result['ml_score']), (6, 4))
        self.assertEqual(result['proposal'], 'undecided')

        clear = dict(slim)
        clear['fit.pride'] = 'ship-ai'          # moves 1 ml point to 2 ai points
        decided = score_pathway_fit(clear)
        self.assertEqual(decided['lead'], 4)
        self.assertEqual(decided['proposal'], 'ai')

    def test_validation_reports_each_missing_or_unknown_answer(self):
        errors = validate_pathway_fit_answers({})
        self.assertEqual(set(errors), {q['id'] for q in PATHWAY_FIT_QUESTIONS})

        partial = dict(ML_ANSWERS)
        partial.pop('fit.pride')
        self.assertIn('fit.pride', validate_pathway_fit_answers(partial))

        bad = dict(ML_ANSWERS)
        bad['fit.pride'] = 'not-an-option'
        self.assertIn('fit.pride', validate_pathway_fit_answers(bad))

        self.assertEqual(validate_pathway_fit_answers(AI_ANSWERS), {})
        with self.assertRaises(PathwayFitError):
            score_pathway_fit({'fit.outcome': 'product-feature'})


class PathwayFitOnboardingFlowTests(unittest.TestCase):
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
            'username': 'fitlearner',
            'email': 'fitlearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

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

    def _plan(self):
        with self.app.app_context():
            return CoursePlan.query.one()

    def _complete_step_one(self):
        response = self.client.post('/onboarding', data={
            'skill_level': 'new', 'weekly_hours': '10-12', 'track': 'standard',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/onboarding/pathway', response.headers['Location'])
        return response

    def test_step_one_saves_answers_but_keeps_the_gate_closed(self):
        self._complete_step_one()
        plan = self._plan()
        self.assertEqual(plan.skill_level, 'new')
        self.assertEqual(plan.weekly_hours, 11)
        self.assertIsNone(plan.pathway_destination)
        # The fit check is not optional-by-navigation: /projects still bounces.
        self.assertEqual(
            self.client.get('/projects', follow_redirects=False).status_code, 302
        )

    def test_fit_check_redirects_back_until_step_one_is_answered(self):
        response = self.client.get(
            '/onboarding/pathway', follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/onboarding', response.headers['Location'])

    def test_answers_store_a_proposal_but_never_a_destination(self):
        self._complete_step_one()
        page = self.client.get('/onboarding/pathway')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Which pathway fits you?', page.get_data(as_text=True))

        answered = self.client.post('/onboarding/pathway', data=ML_ANSWERS)
        self.assertEqual(answered.status_code, 200)
        html = answered.get_data(as_text=True)
        self.assertIn('We propose: Machine Learning Engineering pathway', html)
        plan = self._plan()
        self.assertEqual(plan.pathway_proposal, 'ml')
        self.assertIsNone(plan.pathway_destination)
        # Gate stays closed until the learner confirms or skips.
        self.assertEqual(
            self.client.get('/projects', follow_redirects=False).status_code, 302
        )

    def test_confirmation_stores_the_destination_and_opens_the_gate(self):
        self._complete_step_one()
        self.client.post('/onboarding/pathway', data=ML_ANSWERS)
        confirmed = self.client.post('/onboarding/pathway', data={
            'action': 'confirm', 'pathway_destination': 'ml',
        })
        self.assertEqual(confirmed.status_code, 302)
        plan = self._plan()
        self.assertEqual(plan.pathway_proposal, 'ml')
        self.assertEqual(plan.pathway_destination, 'ml')
        self.assertEqual(self.client.get('/projects').status_code, 200)

    def test_learner_can_override_the_proposal(self):
        self._complete_step_one()
        self.client.post('/onboarding/pathway', data=ML_ANSWERS)
        confirmed = self.client.post('/onboarding/pathway', data={
            'action': 'confirm', 'pathway_destination': 'ai',
        })
        self.assertEqual(confirmed.status_code, 302)
        plan = self._plan()
        self.assertEqual(plan.pathway_proposal, 'ml')
        self.assertEqual(plan.pathway_destination, 'ai')

    def test_confirm_without_a_proposal_writes_nothing(self):
        self._complete_step_one()
        response = self.client.post('/onboarding/pathway', data={
            'action': 'confirm', 'pathway_destination': 'ml',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/onboarding/pathway', response.headers['Location'])
        plan = self._plan()
        self.assertIsNone(plan.pathway_proposal)
        self.assertIsNone(plan.pathway_destination)

    def test_unknown_destination_is_rejected_with_an_error(self):
        self._complete_step_one()
        self.client.post('/onboarding/pathway', data=ML_ANSWERS)
        response = self.client.post('/onboarding/pathway', data={
            'action': 'confirm', 'pathway_destination': 'blockchain',
        })
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Choose where your dashboard should lead.', html)
        self.assertIsNone(self._plan().pathway_destination)

    def test_partial_answers_show_errors_and_store_no_proposal(self):
        self._complete_step_one()
        partial = dict(ML_ANSWERS)
        partial.pop('fit.curiosity')
        response = self.client.post('/onboarding/pathway', data=partial)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Choose one of the options.', html)
        plan = self._plan()
        self.assertIsNone(plan.pathway_proposal)
        self.assertIsNone(plan.pathway_destination)

    def test_skipping_step_two_completes_onboarding_without_a_destination(self):
        self._complete_step_one()
        skipped = self.client.post('/onboarding/pathway', data={'action': 'skip'})
        self.assertEqual(skipped.status_code, 302)
        plan = self._plan()
        self.assertIsNone(plan.pathway_proposal)
        self.assertIsNone(plan.pathway_destination)
        self.assertEqual(self.client.get('/projects').status_code, 200)


class DashboardPathwayLeadTests(unittest.TestCase):
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
            'username': 'leadlearner',
            'email': 'leadlearner@example.test',
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
            user = User.query.filter_by(username='leadlearner').one()
            plan = CoursePlan.query.filter_by(user_id=user.id).first()
            if plan is None:
                plan = CoursePlan(user_id=user.id, track='standard')
                db.session.add(plan)
            plan.skill_level = 'new'
            plan.weekly_hours = 10
            plan.pathway_destination = destination
            db.session.commit()

    def _complete_shared_prerequisites(self):
        with self.app.app_context():
            user = User.query.filter_by(username='leadlearner').one()
            for module_id in ('01', '02'):
                db.session.add(CourseProject(
                    user_id=user.id, module_id=module_id,
                    project='{}', completed=True,
                ))
            db.session.commit()

    def _dashboard(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_ml_destination_leads_with_the_pathway_section(self):
        self._set_destination('ml')
        html = self._dashboard()
        # Section promoted above the shared next-action cards, exactly once.
        self.assertIn('Your pathway', html)
        self.assertNotIn('Optional pathway', html)
        self.assertEqual(html.count('Machine Learning Engineering specialization'), 1)
        self.assertLess(html.index('Your pathway'), html.index('Getting started'))
        self.assertLess(html.index('Your pathway'), html.index('Continue your course'))
        # Shared foundation stays visible below, and the locked state points
        # at the shared next step rather than a dead end.
        self.assertIn('Opens after your Module 01 and Module 02 course projects', html)
        self.assertIn('Start the shared foundation', html)
        self.assertIn('Continue your course', html)

    def test_unlocked_ml_destination_leads_the_hero_with_the_pathway(self):
        self._set_destination('ml')
        self._complete_shared_prerequisites()
        html = self._dashboard()
        self.assertIn('Continue your pathway', html)
        self.assertIn('pathway lessons', html)
        self.assertLess(html.index('Your pathway'), html.index('Continue your course'))

    def test_unset_destination_keeps_the_current_order(self):
        html = self._dashboard()
        self.assertIn('Optional pathway', html)
        self.assertNotIn('Your pathway', html)
        self.assertLess(html.index('Continue your course'), html.index('Optional pathway'))

    def test_ai_destination_keeps_the_current_order(self):
        self._set_destination('ai')
        html = self._dashboard()
        self.assertIn('Optional pathway', html)
        self.assertLess(html.index('Continue your course'), html.index('Optional pathway'))

    def test_ml_destination_with_a_failing_overview_stays_contained(self):
        self._set_destination('ml')
        with patch(
            'app.routes.main.ml_pathway_overview',
            side_effect=RuntimeError('overview unavailable'),
        ):
            html = self._dashboard()
        self.assertNotIn('Optional pathway', html)
        self.assertNotIn('Your pathway', html)
        self.assertIn('Continue your course', html)


if __name__ == '__main__':
    unittest.main()
