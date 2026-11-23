"""M4 — traceable project evaluation, human review and portfolio evidence."""

import json
import os
import tempfile
import unittest
from io import BytesIO

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.ai_pathway import PATHWAY_ID as AI_PATHWAY, ai_engineering_pathway
from app.ml_pathway import PATHWAY_ID as ML_PATHWAY
from app.models import (
    AIAgentExecutionRecord, AIEvaluationRecord, AIPromptVersion,
    AIRetrievalConfiguration, AISpecializationProject, MLProjectExperiment,
    MLSpecializationProject, ProjectArtifact, SkillVerification, User,
    UserSkillProgress,
)
from app.routes.projects import _public_project_payload
from app.services.artifacts import create_artifact
from app.services.project_competencies import competencies_for
from app.services.project_lifecycle import current_stage, record_transition


VALID_ML_REPORT = {
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
    'regression_train_rows': 12,
    'regression_test_rows': 4,
    'regression_mae': 12000.0,
    'regression_r2': 0.91,
    'regression_features': ['size_sqm', 'bedrooms', 'location_score'],
}


class ProjectEvaluationM4Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_dir.name}/test.db'
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            GEMINI_API_KEY=None,
            STORAGE_BACKEND='local',
            ARTIFACT_STORAGE_DIR=os.path.join(self.temp_dir.name, 'artifacts'),
        )
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()
        self.ai_module = next(
            m['id'] for m in ai_engineering_pathway()['modules']
            if m['id'] == 'ai.05'
        )
        self.ml_module = 'mle.classical-ml'
        self.owner_id = self._register('m4owner')
        self.reviewer_id = self._create_reviewer('m4reviewer')

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

    def _register(self, username):
        response = self.client.post('/register', data={
            'username': username,
            'email': f'{username}@example.test',
            'password': 'secure-pass-123',
            'confirm_password': 'secure-pass-123',
            'full_name': username.title(),
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.client.post('/onboarding', data={'action': 'skip'})
        with self.app.app_context():
            return User.query.filter_by(username=username).one().id

    def _create_reviewer(self, username):
        with self.app.app_context():
            user = User(
                username=username,
                email=f'{username}@example.test',
                full_name=username.title(),
                password_hash=generate_password_hash('secure-pass-123'),
                role='reviewer',
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    def login(self, username):
        response = self.client.post('/login', data={
            'username': username, 'password': 'secure-pass-123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def logout(self):
        self.client.post('/logout', follow_redirects=True)

    def _submit_lifecycle(self, domain, project_key):
        with self.app.app_context():
            owner = db.session.get(User, self.owner_id)
            record_transition(
                self.owner_id, domain, project_key, 'submitted', actor=owner,
            )
            db.session.commit()

    def _seed_ai_project(self, *, with_artifact=True):
        with self.app.app_context():
            project = AISpecializationProject(
                user_id=self.owner_id,
                pathway_id=AI_PATHWAY,
                module_id=self.ai_module,
                submission=json.dumps({
                    'problem_statement': 'Grounded support answers with citations.',
                    'reflection': 'Versioned prompts and measured retrieval before answering.',
                    'repository_url': 'https://example.test/rag-project',
                }),
                evaluation=json.dumps({
                    'summary': 'Retrieval was measured separately from answer quality.',
                    'criterion_feedback': [{
                        'criterion': 'Retrieval evaluation',
                        'score': 82,
                        'evidence': 'Hit rate was recorded for the held-out set.',
                        'gap': 'Add more adversarial queries.',
                    }],
                }),
            )
            db.session.add(project)
            db.session.flush()
            db.session.add_all([
                AIPromptVersion(
                    user_id=self.owner_id, pathway_id=AI_PATHWAY,
                    module_id=self.ai_module, version=1,
                    prompt_content='Answer using only the supplied context.',
                    model_configuration='{"temperature": 0.2}',
                ),
                AIRetrievalConfiguration(
                    user_id=self.owner_id, pathway_id=AI_PATHWAY,
                    module_id=self.ai_module,
                    chunking_configuration='{"size": 512}',
                    embedding_configuration='{"model": "local-test"}',
                    retrieval_parameters='{"top_k": 4}',
                ),
                AIAgentExecutionRecord(
                    user_id=self.owner_id, pathway_id=AI_PATHWAY,
                    module_id=self.ai_module, execution_id='run-1',
                    status='completed', tool_calls='[]', duration=120,
                ),
                AIEvaluationRecord(
                    user_id=self.owner_id, pathway_id=AI_PATHWAY,
                    module_id=self.ai_module,
                    evaluation_dataset='rag-golden-set',
                    evaluation_results=json.dumps({
                        'checks': [{
                            'name': 'citations-present',
                            'passed': True,
                            'detail': 'Each answer cited a stored chunk',
                        }],
                    }),
                    metric_summary=json.dumps({
                        'hit_rate': {'value': 0.9, 'passed': True},
                    }),
                ),
            ])
            db.session.commit()
            project_id = project.id
        if with_artifact:
            with self.app.app_context():
                create_artifact(
                    owner_id=self.owner_id,
                    project_type='ai',
                    project_id=project_id,
                    artifact_type='source',
                    filename='rag_pipeline.py',
                    data=b'def answer(query): return "grounded"\n',
                )
        return project_id

    def _seed_ml_project(self, *, with_artifact=True):
        with self.app.app_context():
            project = MLSpecializationProject(
                user_id=self.owner_id,
                pathway_id=ML_PATHWAY,
                module_id=self.ml_module,
                submission=json.dumps({
                    'repository_url': 'https://example.test/ml-project',
                    'checks_url': 'https://example.test/ml-project/actions',
                    'report': VALID_ML_REPORT,
                }),
                evaluation=json.dumps({
                    'summary': 'Fixed dataset checks and rubric feedback agree.',
                    'criterion_feedback': [{
                        'criterion': 'Model evaluation',
                        'score': 88,
                        'evidence': 'Metrics were compared with the fixed baseline.',
                        'gap': 'Document deployment trade-offs.',
                    }],
                }),
            )
            experiment = MLProjectExperiment(
                user_id=self.owner_id,
                pathway_id=ML_PATHWAY,
                module_id=self.ml_module,
                experiment_name='baseline-classifier',
                dataset_version='synthetic-v1',
                model_type='logistic-regression',
                evaluation_metrics=json.dumps({
                    'f1': {'value': 0.85, 'passed': True},
                }),
            )
            db.session.add_all([project, experiment])
            db.session.commit()
            experiment_id = experiment.id
        if with_artifact:
            with self.app.app_context():
                create_artifact(
                    owner_id=self.owner_id,
                    project_type='ml',
                    project_id=experiment_id,
                    artifact_type='model',
                    filename='model.joblib',
                    data=b'model-bytes',
                )

    def test_single_generated_score_is_not_evidence(self):
        self._seed_ai_project()
        self._submit_lifecycle('ai-engineering', self.ai_module)
        self.login('m4owner')
        response = self.client.post('/api/projects/evaluations', json={
            'domain': 'ai-engineering',
            'project_key': self.ai_module,
            'automated_checks': {'score': 100},
            'rubric_feedback': {'score': 100},
            'evidence_refs': [{'type': 'score', 'id': '100'}],
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('automated_checks', response.get_json()['error'])

    def test_ai_evidence_is_built_from_distinct_sources(self):
        self._seed_ai_project()
        self._submit_lifecycle('ai-engineering', self.ai_module)
        self.login('m4owner')
        response = self.client.post('/api/projects/evaluations', json={
            'domain': 'ai-engineering', 'project_key': self.ai_module,
        })
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        payload = response.get_json()['evaluation']
        self.assertEqual(payload['status'], 'AWAITING_HUMAN_REVIEW')
        self.assertEqual(payload['automated_checks']['source'],
                         'ai-engineering:stored-artifacts')
        self.assertEqual(payload['rubric_feedback']['source'],
                         'ai-engineering:stored-project-review')
        self.assertTrue(all(
            check['passed'] for check in payload['automated_checks']['checks']
        ))
        self.assertIn('artifact', {ref['type'] for ref in payload['evidence_refs']})
        self.assertIsNotNone(payload['rubric_score'])

        listing = self.client.get(
            f'/api/projects/evaluations/ai-engineering/{self.ai_module}'
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.get_json()['evaluations']), 1)

    def test_human_review_links_only_ai_competencies(self):
        self._seed_ai_project()
        self._submit_lifecycle('ai-engineering', self.ai_module)
        self.login('m4owner')
        created = self.client.post('/api/projects/evaluations', json={
            'domain': 'ai-engineering', 'project_key': self.ai_module,
        }).get_json()['evaluation']
        evaluation_id = created['id']

        own_review = self.client.post(
            f'/api/projects/evaluations/{evaluation_id}/review',
            json={'decision': 'approved'},
        )
        self.assertEqual(own_review.status_code, 403)

        self.logout()
        self.login('m4reviewer')
        approved = self.client.post(
            f'/api/projects/evaluations/{evaluation_id}/review',
            json={'decision': 'approved', 'note': 'Evidence checked'},
        )
        self.assertEqual(approved.status_code, 200, approved.get_data(as_text=True))
        payload = approved.get_json()['evaluation']
        self.assertEqual(payload['status'], 'VERIFIED')
        self.assertEqual(payload['human_review']['decision'], 'approved')
        self.assertEqual(payload['human_review']['reviewer_id'], self.reviewer_id)

        with self.app.app_context():
            self.assertEqual(
                current_stage(self.owner_id, 'ai-engineering', self.ai_module),
                'approved',
            )
            expected = competencies_for('ai-engineering', self.ai_module)
            for competency in expected:
                progress = UserSkillProgress.query.filter_by(
                    user_id=self.owner_id, skill_id=competency['id'],
                ).one()
                self.assertEqual(progress.verification_status, 'VERIFIED')
                self.assertEqual(progress.evidence_type, 'PROJECT')
                self.assertEqual(progress.verified_by_user_id, self.reviewer_id)
                self.assertEqual(
                    SkillVerification.query.filter_by(
                        user_id=self.owner_id, skill_id=competency['id'],
                        to_status='VERIFIED',
                    ).count(),
                    1,
                )
            self.assertEqual(
                UserSkillProgress.query.filter(
                    UserSkillProgress.skill_id.like('ml-%')
                ).count(),
                0,
            )

    def test_review_at_published_stage_keeps_lifecycle_and_links_evidence(self):
        self._seed_ai_project()
        self._submit_lifecycle('ai-engineering', self.ai_module)
        self.login('m4owner')
        created = self.client.post('/api/projects/evaluations', json={
            'domain': 'ai-engineering', 'project_key': self.ai_module,
        }).get_json()['evaluation']

        with self.app.app_context():
            reviewer = db.session.get(User, self.reviewer_id)
            owner = db.session.get(User, self.owner_id)
            record_transition(
                self.owner_id, 'ai-engineering', self.ai_module,
                'approved', actor=reviewer,
            )
            record_transition(
                self.owner_id, 'ai-engineering', self.ai_module,
                'published', actor=owner,
            )
            db.session.commit()

        self.logout()
        self.login('m4reviewer')
        approved = self.client.post(
            f"/api/projects/evaluations/{created['id']}/review",
            json={'decision': 'approved'},
        )
        self.assertEqual(approved.status_code, 200, approved.get_data(as_text=True))
        self.assertEqual(approved.get_json()['evaluation']['status'], 'VERIFIED')
        with self.app.app_context():
            self.assertEqual(
                current_stage(self.owner_id, 'ai-engineering', self.ai_module),
                'published',
            )
            self.assertEqual(
                UserSkillProgress.query.filter_by(
                    user_id=self.owner_id, verification_status='VERIFIED',
                ).count(),
                len(competencies_for('ai-engineering', self.ai_module)),
            )

    def test_ml_deterministic_evidence_and_portfolio_visibility(self):
        self._seed_ml_project()
        self._submit_lifecycle('machine-learning', self.ml_module)
        self.login('m4owner')
        created = self.client.post('/api/projects/evaluations', json={
            'domain': 'machine-learning', 'project_key': self.ml_module,
        })
        self.assertEqual(created.status_code, 201, created.get_data(as_text=True))
        payload = created.get_json()['evaluation']
        checks = {row['name']: row['passed']
                  for row in payload['automated_checks']['checks']}
        self.assertTrue(checks['report-contract'])
        self.assertTrue(checks['experiment-recorded'])
        self.assertTrue(checks['model-or-report-artifact'])

        before = self.client.get('/api/projects/portfolio/evidence').get_json()
        self.assertEqual(before['projects'], [])

        self.logout()
        self.login('m4reviewer')
        approved = self.client.post(
            f"/api/projects/evaluations/{payload['id']}/review",
            json={'decision': 'approved'},
        )
        self.assertEqual(approved.status_code, 200, approved.get_data(as_text=True))

        self.logout()
        self.login('m4owner')
        after = self.client.get('/api/projects/portfolio/evidence').get_json()
        self.assertEqual(len(after['projects']), 1)
        entry = after['projects'][0]
        self.assertEqual(entry['domain'], 'machine-learning')
        self.assertEqual(entry['verification_status'], 'Verified')
        self.assertIn('ml-supervised-learning', entry['competencies'])
        self.assertTrue(entry['checks_verified'])
        self.assertEqual(entry['evaluation']['status'], 'VERIFIED')

        public = _public_project_payload(entry)
        self.assertNotIn('rubric_feedback', public)
        self.assertNotIn('human_review', public)
        self.assertEqual(public['evidence_status'], 'VERIFIED')

    def test_ai_project_artifacts_are_owner_scoped(self):
        project_id = self._seed_ai_project(with_artifact=False)
        self.login('m4owner')
        response = self.client.post('/api/artifacts', data={
            'file': (BytesIO(b'print("rag")\n'), 'rag.py', 'text/x-python'),
            'project_type': 'ai',
            'project_id': str(project_id),
            'artifact_type': 'source',
            'access_policy': 'private',
        }, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        artifact = response.get_json()['artifact']
        self.assertEqual(artifact['project_type'], 'ai')
        self.assertEqual(artifact['project_id'], project_id)

        with self.app.app_context():
            self.assertEqual(
                ProjectArtifact.query.filter_by(
                    project_type='ai', project_id=project_id,
                ).count(),
                1,
            )


if __name__ == '__main__':
    unittest.main()
