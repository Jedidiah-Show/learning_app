"""Application-level checks for the independent ML specialization."""

import os
import re
import tempfile
import unittest
from io import BytesIO
from urllib.parse import urlsplit
from unittest.mock import patch
from zipfile import ZipFile

from app import create_app, db
from app.curriculum import all_lessons
from app.ml_pathway import PATHWAY_ID, machine_learning_pathway, ml_pathway_pacing
from app.models import (
    CoursePlan, CourseProject, LessonCompletion, MLSpecializationLessonCompletion,
    MLSpecializationProject, ReviewItem, User,
)
from app.routes.ml_specialization import _dataset_sha256, _report_matches


class MLSpecializationFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY=None)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.register()

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

    def register(self):
        response = self.client.post('/register', data={
            'username': 'mllearner',
            'email': 'mllearner@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})

    def _complete_quiz(self, lesson, answer=None):
        page = self.client.get(
            f"/specializations/machine-learning/lessons/{lesson['id']}"
        )
        self.assertEqual(page.status_code, 200, page.get_data(as_text=True))
        csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
        self.assertIsNotNone(csrf)
        if answer is None:
            answer = lesson['quiz']['answer']
        return self.client.post(
            f"/specializations/machine-learning/lessons/{lesson['id']}",
            data={'csrf_token': csrf.group(1).decode(), 'answer': str(answer)},
        )

    def _complete_shared_prerequisites(self):
        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            for module_id in ('01', '02'):
                db.session.add(CourseProject(
                    user_id=user.id, module_id=module_id,
                    project='{}', completed=True,
                ))
            db.session.commit()

    def _csrf_token(self, response):
        token = re.search(rb'<meta name="csrf-token" content="([^"]+)"', response.data)
        self.assertIsNotNone(token)
        return token.group(1).decode()

    def test_dashboard_card_tracks_the_pathway_without_opening_lessons(self):
        locked = self.client.get('/')
        self.assertEqual(locked.status_code, 200)
        self.assertIn('Machine Learning Engineering specialization', locked.get_data(as_text=True))
        self.assertIn('Opens after your Module 01 and Module 02 course projects', locked.get_data(as_text=True))

        self._complete_shared_prerequisites()
        pathway = machine_learning_pathway()
        first = [
            lesson for module in pathway['modules'] for lesson in module['lessons']
            if lesson.get('status') == 'ready'
        ][0]
        opened = self.client.get('/')
        self.assertIn('Continue: ' + first['title'], opened.get_data(as_text=True))
        self.assertIn('0 of 14 lessons · 0 of 4 projects complete', opened.get_data(as_text=True))

        self._complete_quiz(first)
        advanced = self.client.get('/').get_data(as_text=True)
        self.assertIn('1 of 14 lessons', advanced)

    def test_pathway_content_is_namespaced_and_not_in_shared_curriculum(self):
        pathway = machine_learning_pathway()
        pathway_ids = {
            lesson['id'] for module in pathway['modules']
            for lesson in module['lessons']
        }
        self.assertTrue(pathway_ids)
        self.assertTrue(all(item.startswith('mle.') for item in pathway_ids))
        self.assertFalse(any(lesson['id'] in pathway_ids for lesson in all_lessons()))
        self.assertEqual(pathway['id'], PATHWAY_ID)

    def test_all_starter_downloads_contain_the_expected_project_files(self):
        for module_id, root in (
            ('mle.data-problem-formulation', 'ruach-ml-data-audit'),
            ('mle.classical-ml', 'ruach-ml-classical-baseline'),
            ('mle.reproducible-training', 'ruach-ml-reproducible-training'),
            ('mle.production-ml', 'ruach-ml-production-service'),
        ):
            response = self.client.get(
                f'/specializations/machine-learning/projects/{module_id}/starter'
            )
            self.assertEqual(response.status_code, 200)
            with ZipFile(BytesIO(response.data)) as archive:
                names = set(archive.namelist())
                self.assertIn(f'{root}/README.md', names)
                self.assertTrue(any(name.startswith(f'{root}/src/') for name in names))

    def test_server_report_contracts_reject_metric_threshold_regressions(self):
        classical = {
            'train_rows': 24, 'evaluation_rows': 12,
            'baseline_accuracy': 8 / 12, 'accuracy': .90,
            'precision': .85, 'recall': .85, 'f1': .85,
            'cross_validation_f1_mean': .85,
            'feature_columns': ['support_tickets', 'tenure_months'],
            'leakage_features': ['cancelled_after_snapshot'],
            'cross_validation_folds': 5,
            'preprocessing_in_pipeline': True,
            'evaluation_set_used_for_fitting': False,
            'data_split': 'fixed_holdout',
        }
        self.assertTrue(_report_matches('mle.classical-ml', classical))
        classical['f1'] = .79
        self.assertFalse(_report_matches('mle.classical-ml', classical))

        reproducible = {
            'train_rows': 24, 'evaluation_rows': 12, 'seed': 7,
            'dataset_sha256': _dataset_sha256(3),
            'feature_columns': ['support_tickets', 'tenure_months'],
            'artifact_version': '1.0.0',
            'run_manifest_fields': [
                'artifact_version', 'dataset_sha256', 'feature_columns',
                'fixed_metrics', 'parameters', 'package_versions',
                'source_revision', 'training_seed', 'validation_f1_mean',
            ],
            'repeated_run_predictions_match': True,
            'evaluation_set_used_for_fitting': False,
            'accuracy': .95, 'f1': .90, 'validation_f1_mean': .88,
        }
        self.assertTrue(_report_matches('mle.reproducible-training', reproducible))

        production = {
            'health_status': 200, 'model_version': '1.0.0',
            'batch_prediction_count': 2, 'invalid_feature_rejected': True,
            'extra_feature_rejected': True, 'input_drift_detected': True,
            'drift_proves_quality_failure': False, 'canary_promoted': False,
            'rollback_active_version': '1.0.0', 'rollback_triggered': True,
        }
        self.assertTrue(_report_matches('mle.production-ml', production))

    def test_prerequisites_and_sequential_quizzes_gate_progress_separately(self):
        catalog = self.client.get('/specializations/machine-learning')
        self.assertEqual(catalog.status_code, 200)
        lessons = machine_learning_pathway()['modules'][0]['lessons']
        denied = self.client.get(
            f"/specializations/machine-learning/lessons/{lessons[0]['id']}"
        )
        self.assertEqual(denied.status_code, 403)

        self._complete_shared_prerequisites()
        self.assertEqual(self.client.get(
            f"/specializations/machine-learning/lessons/{lessons[1]['id']}"
        ).status_code, 403)
        for lesson in lessons:
            response = self._complete_quiz(lesson)
            self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            ml_completions = MLSpecializationLessonCompletion.query.filter_by(
                user_id=user.id, pathway_id=PATHWAY_ID
            ).all()
            self.assertEqual(len(ml_completions), len(lessons))
            self.assertEqual(LessonCompletion.query.filter_by(user_id=user.id).count(), 0)

        project = self.client.get(
            '/specializations/machine-learning/projects/mle.data-problem-formulation'
        )
        self.assertEqual(project.status_code, 200)

    def test_project_and_credential_stay_locked_until_requirements_are_met(self):
        project = self.client.get(
            '/specializations/machine-learning/projects/mle.data-problem-formulation'
        )
        self.assertEqual(project.status_code, 403)
        credential = self.client.get('/specializations/machine-learning/credential')
        self.assertEqual(credential.status_code, 200)
        self.assertIn(b'Lessons completed: 0', credential.data)
        with self.app.app_context():
            self.assertEqual(MLSpecializationProject.query.count(), 0)

    def test_project_report_and_rubric_review_can_complete_a_module(self):
        self._complete_shared_prerequisites()
        module = machine_learning_pathway()['modules'][0]
        for lesson in module['lessons']:
            self.assertEqual(self._complete_quiz(lesson).status_code, 302)

        page = self.client.get(
            '/specializations/machine-learning/projects/mle.data-problem-formulation'
        )
        csrf = self._csrf_token(page)
        evaluation = {
            'score': 85,
            'summary': 'The evidence satisfies the project requirements.',
            'strengths': ['The data checks are clear.'],
            'gaps': [],
            'next_steps': ['Keep the audit repeatable.'],
            'criterion_feedback': [{
                'criterion': item['criterion'], 'score': 85,
                'evidence': 'The report and reflection explain this choice.',
                'gap': '',
            } for item in module['project_rubric']],
        }
        with patch(
            'app.routes.ml_specialization.verify_checks',
            return_value={'verified': True, 'checks_status': 200},
        ), patch('app.gemini.generate_json', return_value=evaluation):
            response = self.client.post(
                '/specializations/machine-learning/projects/mle.data-problem-formulation/submit',
                headers={'X-CSRF-Token': csrf},
                json={
                    'repository_url': 'https://github.com/learner/ml-audit',
                    'checks_url': 'https://github.com/learner/ml-audit/actions/runs/1',
                    'reflection': 'I audited the source data, preserved the time boundary, '
                                  'and excluded post-outcome refund information from features.',
                    'report': {
                        'row_count': 12, 'required_columns_present': True,
                        'unique_order_ids': 12, 'missing_order_total_count': 1,
                        'nonpositive_order_total_count': 1, 'returned_count': 4,
                        'development_rows': 8, 'evaluation_rows': 4,
                        'split_strategy': 'time_ordered',
                        'leakage_features': ['refund_reason'],
                    },
                },
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertTrue(response.get_json()['completed'])
        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            project = MLSpecializationProject.query.filter_by(
                user_id=user.id, pathway_id=PATHWAY_ID,
                module_id=module['id'],
            ).one()
            self.assertTrue(project.completed)

    def test_failed_submissions_record_a_classified_failure_stage(self):
        from app.gemini import GeminiError
        from app.project_verification import VerificationError

        self._complete_shared_prerequisites()
        module = machine_learning_pathway()['modules'][0]
        for lesson in module['lessons']:
            self.assertEqual(self._complete_quiz(lesson).status_code, 302)
        url = f"/specializations/machine-learning/projects/{module['id']}/submit"
        page = self.client.get(
            f"/specializations/machine-learning/projects/{module['id']}"
        )
        csrf = self._csrf_token(page)
        report = {
            'row_count': 12, 'required_columns_present': True,
            'unique_order_ids': 12, 'missing_order_total_count': 1,
            'nonpositive_order_total_count': 1, 'returned_count': 4,
            'development_rows': 8, 'evaluation_rows': 4,
            'split_strategy': 'time_ordered',
            'leakage_features': ['refund_reason'],
        }
        reflection = (
            'I audited the source data, preserved the time boundary, '
            'and excluded post-outcome refund information from features. '
            'The split follows the documented contract exactly.'
        )
        rubric = module['project_rubric']

        def submit(payload):
            return self.client.post(url, headers={'X-CSRF-Token': csrf}, json={
                'repository_url': 'https://github.com/learner/ml-audit',
                'checks_url': 'https://github.com/learner/ml-audit/actions/runs/1',
                'reflection': reflection, 'report': payload,
            })

        def recorded():
            with self.app.app_context():
                user = User.query.filter_by(username='mllearner').one()
                record = MLSpecializationProject.query.filter_by(
                    user_id=user.id, pathway_id=PATHWAY_ID, module_id=module['id'],
                ).one()
                return {
                    'stage': record.failure_stage,
                    'detail': record.failure_detail,
                    'completed': record.completed,
                }

        def evaluation(score):
            return {
                'score': score,
                'summary': 'The evidence satisfies the project requirements.',
                'strengths': ['The data checks are clear.'],
                'gaps': [],
                'next_steps': ['Keep the audit repeatable.'],
                'criterion_feedback': [{
                    'criterion': item['criterion'],
                    'score': max(0, min(100, score)),
                    'evidence': 'The report and reflection explain this choice.',
                    'gap': '',
                } for item in rubric],
            }

        # 1. Report does not match the server-owned contract.
        broken = dict(report, row_count=999)
        response = submit(broken)
        self.assertEqual(response.status_code, 422)
        self.assertTrue(response.get_json()['draft_saved'])
        state = recorded()
        self.assertEqual(state['stage'], 'report_contract')
        self.assertIn('fixed dataset checks', state['detail'])
        self.assertFalse(state['completed'])

        # 2. Public CI cannot be verified.
        with patch(
            'app.routes.ml_specialization.verify_checks',
            side_effect=VerificationError('The checks page reports a failed build'),
        ):
            response = submit(report)
        self.assertEqual(response.status_code, 422)
        state = recorded()
        self.assertEqual(state['stage'], 'ci_verification')
        self.assertEqual(state['detail'], 'The checks page reports a failed build')

        # 3. Automated review is down; the draft stays saved.
        with patch(
            'app.routes.ml_specialization.verify_checks',
            return_value={'verified': True, 'checks_status': 200},
        ), patch('app.gemini.generate_json', side_effect=GeminiError('quota reached')):
            response = submit(report)
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.get_json()['draft_saved'])
        self.assertEqual(recorded()['stage'], 'review_unavailable')

        # 4. Review returned a structurally invalid result.
        with patch(
            'app.routes.ml_specialization.verify_checks',
            return_value={'verified': True, 'checks_status': 200},
        ), patch('app.gemini.generate_json', return_value={'score': 90}):
            response = submit(report)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(recorded()['stage'], 'review_invalid')

        # 5. Review completed but below the pass thresholds.
        with patch(
            'app.routes.ml_specialization.verify_checks',
            return_value={'verified': True, 'checks_status': 200},
        ), patch('app.gemini.generate_json', return_value=evaluation(40)):
            response = submit(report)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['completed'])
        state = recorded()
        self.assertEqual(state['stage'], 'rubric_below_threshold')
        self.assertFalse(state['completed'])

        # 6. A pass clears the failure state entirely.
        with patch(
            'app.routes.ml_specialization.verify_checks',
            return_value={'verified': True, 'checks_status': 200},
        ), patch('app.gemini.generate_json', return_value=evaluation(85)):
            response = submit(report)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertTrue(response.get_json()['completed'])
        state = recorded()
        self.assertIsNone(state['stage'])
        self.assertIsNone(state['detail'])
        self.assertTrue(state['completed'])

    def test_eligible_learner_can_issue_and_publicly_verify_credential(self):
        pathway = machine_learning_pathway()
        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            for module_id in ('01', '02'):
                db.session.add(CourseProject(
                    user_id=user.id, module_id=module_id,
                    project='{}', completed=True,
                ))
            for module in pathway['modules']:
                for lesson in module['lessons']:
                    db.session.add(MLSpecializationLessonCompletion(
                        user_id=user.id, pathway_id=PATHWAY_ID,
                        lesson_id=lesson['id'],
                    ))
                db.session.add(MLSpecializationProject(
                    user_id=user.id, pathway_id=PATHWAY_ID,
                    module_id=module['id'], completed=True,
                ))
            db.session.commit()

        page = self.client.get('/specializations/machine-learning/credential')
        response = self.client.post(
            '/specializations/machine-learning/credential/issue',
            headers={'X-CSRF-Token': self._csrf_token(page)},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        verify_url = response.get_json()['credential']['verify_url']
        public_page = self.client.get(urlsplit(verify_url).path + '?' + urlsplit(verify_url).query)
        self.assertEqual(public_page.status_code, 200)
        self.assertIn(b'Valid credential', public_page.data)

        parsed = urlsplit(verify_url)
        tampered = self.client.get(parsed.path + '?sig=invalid')
        self.assertIn(b'could not be verified', tampered.data)

    def test_missed_pathway_check_feeds_the_spaced_review_queue(self):
        self._complete_shared_prerequisites()
        lesson = machine_learning_pathway()['modules'][0]['lessons'][0]
        wrong = (lesson['quiz']['answer'] + 1) % len(lesson['quiz']['choices'])

        response = self._complete_quiz(lesson, answer=wrong)
        self.assertEqual(response.status_code, 200)
        self.assertIn('review queue', response.get_data(as_text=True))

        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            item = ReviewItem.query.filter_by(user_id=user.id).one()
            self.assertEqual(item.pathway_id, PATHWAY_ID)
            self.assertEqual(item.quiz_id, f'{PATHWAY_ID}:{lesson["id"]}')
            self.assertEqual(item.question, lesson['quiz']['question'])
            # A miss never completes the lesson.
            self.assertEqual(MLSpecializationLessonCompletion.query.count(), 0)

        queue = self.client.get('/api/quizzes/review').get_json()
        self.assertEqual(queue['due_count'], 1)
        self.assertEqual(queue['items'][0]['pathway_id'], PATHWAY_ID)
        self.assertEqual(
            queue['items'][0]['pathway_title'], machine_learning_pathway()['title']
        )

        # A correct review answer advances the interval, not the pathway.
        answered = self.client.post(
            f"/api/quizzes/review/{queue['items'][0]['id']}",
            json={'answer': lesson['quiz']['answer']},
        )
        self.assertTrue(answered.get_json()['correct'])
        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            item = ReviewItem.query.filter_by(user_id=user.id).one()
            self.assertEqual(item.repetitions, 1)
            self.assertTrue(item.active)
        self.assertEqual(self._complete_quiz(lesson).status_code, 302)
        self.assertEqual(self.client.get('/api/quizzes/review').get_json()['due_count'], 0)

    def test_pathway_pacing_follows_weekly_hours_and_module_progress(self):
        self._complete_shared_prerequisites()
        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            db.session.add(CoursePlan(user_id=user.id, skill_level='new', weekly_hours=6))
            db.session.commit()
            user_id = user.id

            plan = ml_pathway_pacing(user_id)
            self.assertEqual(plan['pathway_id'], PATHWAY_ID)
            self.assertEqual(plan['weekly_hours'], 6)
            self.assertEqual(len(plan['modules']), 4)
            self.assertGreater(plan['total_hours'], 0)
            self.assertEqual(
                plan['estimated_weeks'],
                -(-plan['total_hours'] // plan['weekly_hours']),
            )
            # The plan is derived from authored order, never reordered.
            self.assertEqual(
                [item['number'] for item in plan['modules']], [1, 2, 3, 4]
            )
            self.assertEqual(plan['modules'][0]['status'], 'In progress')
            self.assertEqual(plan['modules'][1]['status'], 'Up next')

            fast = ml_pathway_pacing(user_id, weekly_hours=24)
            self.assertLess(fast['estimated_weeks'], plan['estimated_weeks'])

            # Shared onboarding hours drive the plan when no override exists.
            self.assertEqual(ml_pathway_pacing(user_id, weekly_hours=None)['weekly_hours'], 6)

            first_module = machine_learning_pathway()['modules'][0]
            for lesson in first_module['lessons']:
                db.session.add(MLSpecializationLessonCompletion(
                    user_id=user_id, pathway_id=PATHWAY_ID, lesson_id=lesson['id'],
                ))
            db.session.add(MLSpecializationProject(
                user_id=user_id, pathway_id=PATHWAY_ID,
                module_id=first_module['id'], completed=True,
            ))
            db.session.commit()

            progressed = ml_pathway_pacing(user_id)
            self.assertEqual(progressed['modules'][0]['status'], 'Complete')
            self.assertEqual(progressed['modules'][0]['percent'], 100)
            self.assertEqual(progressed['modules'][1]['status'], 'In progress')

        catalog = self.client.get('/specializations/machine-learning')
        self.assertIn('Your pathway plan', catalog.get_data(as_text=True))
        self.assertIn('6 hours a week', catalog.get_data(as_text=True))

    def test_lessons_page_promotes_the_second_pathway(self):
        locked = self.client.get('/lessons')
        self.assertEqual(locked.status_code, 200)
        page = locked.get_data(as_text=True)
        self.assertIn('Machine Learning Engineering', page)
        self.assertIn('Preview the ML pathway', page)

        self._complete_shared_prerequisites()
        opened = self.client.get('/lessons').get_data(as_text=True)
        self.assertIn('Continue:', opened)

    def test_bookmarks_and_notes_reach_pathway_lessons_with_the_same_gate(self):
        lessons = machine_learning_pathway()['modules'][0]['lessons']
        first_id = lessons[0]['id']
        # Before the shared prerequisites, pathway bookmarks read as absent.
        denied = self.client.post(f'/api/lessons/{first_id}/bookmark')
        self.assertEqual(denied.status_code, 404)

        self._complete_shared_prerequisites()
        marked = self.client.post(f'/api/lessons/{first_id}/bookmark')
        self.assertEqual(marked.status_code, 200)
        self.assertTrue(marked.get_json()['bookmarked'])

        saved = self.client.post(
            f'/api/lessons/{first_id}/note',
            json={'content': 'Prediction unit first, metric second.'},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(
            self.client.get(f'/api/lessons/{first_id}/note').get_json()['note'],
            'Prediction unit first, metric second.',
        )

        # The next lesson is still locked, so it cannot be annotated yet.
        self.assertEqual(
            self.client.post(f'/api/lessons/{lessons[1]["id"]}/bookmark').status_code,
            404,
        )
        for lesson in lessons:
            self.assertEqual(self._complete_quiz(lesson).status_code, 302)
        self.assertEqual(
            self.client.post(f'/api/lessons/{lessons[1]["id"]}/bookmark').status_code,
            200,
        )

        page = self.client.get(
            f'/specializations/machine-learning/lessons/{first_id}'
        ).get_data(as_text=True)
        self.assertIn('🔖 Bookmarked', page)
        self.assertIn('Prediction unit first, metric second.', page)

        # Completing lessons through the normal quiz flow never queues a review.
        with self.app.app_context():
            user = User.query.filter_by(username='mllearner').one()
            self.assertEqual(
                ReviewItem.query.filter_by(user_id=user.id).count(), 0
            )


if __name__ == '__main__':
    unittest.main()
