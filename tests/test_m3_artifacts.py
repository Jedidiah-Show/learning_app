"""M3 durable artifact and MLflow mapping tests."""

import hashlib
import json
import os
import tempfile
import unittest
from io import BytesIO

from app import create_app, db
from app.models import CourseProject, MLProjectExperiment, User
from app.services.artifacts import ArtifactError, create_artifact, get_artifact
from app.services.experiment_tracking import (
    TrackingError,
    build_run_payload,
    record_mlflow_run,
)


class M3ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
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

    def make_course_project(self, username):
        self.register(username)
        self.login(username)
        with self.app.app_context():
            user = User.query.filter_by(username=username).first()
            project = CourseProject(
                user_id=user.id,
                module_id='01',
                project='Build a classifier',
            )
            db.session.add(project)
            db.session.commit()
            return project.id

    def upload(self, project_id, data=b'print("hello")\n', **overrides):
        payload = {
            'file': (BytesIO(data), 'solution.py', 'text/x-python'),
            'project_type': 'course',
            'project_id': str(project_id),
            'artifact_type': 'source',
            'access_policy': 'private',
        }
        payload.update(overrides)
        return self.client.post(
            '/api/artifacts', data=payload, content_type='multipart/form-data'
        )

    def test_upload_list_download_and_delete_artifact(self):
        project_id = self.make_course_project('artifact-owner')
        response = self.upload(project_id)
        self.assertEqual(response.status_code, 201)
        artifact = response.get_json()['artifact']
        self.assertEqual(artifact['artifact_type'], 'source')
        self.assertEqual(artifact['size_bytes'], len(b'print("hello")\n'))
        self.assertEqual(
            artifact['checksum_sha256'],
            hashlib.sha256(b'print("hello")\n').hexdigest(),
        )
        self.assertNotIn('url', artifact)

        listing = self.client.get('/api/artifacts')
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.get_json()['artifacts']), 1)

        detail = self.client.get(f"/api/artifacts/{artifact['id']}")
        self.assertEqual(detail.status_code, 200)

        download = self.client.get(f"/api/artifacts/{artifact['id']}/download")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.data, b'print("hello")\n')

        deleted = self.client.delete(f"/api/artifacts/{artifact['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/artifacts/{artifact['id']}").status_code, 404
        )

    def test_private_artifact_is_hidden_from_other_learners(self):
        project_id = self.make_course_project('artifact-owner')
        artifact = self.upload(project_id).get_json()['artifact']
        self.client.post('/logout', follow_redirects=True)
        self.register('artifact-other')
        self.login('artifact-other')
        self.assertEqual(
            self.client.get(f"/api/artifacts/{artifact['id']}").status_code, 404
        )
        self.assertEqual(
            self.client.get(
                f"/api/artifacts/{artifact['id']}/download"
            ).status_code,
            404,
        )

    def test_upload_validates_project_and_artifact_metadata(self):
        project_id = self.make_course_project('artifact-owner')
        self.assertEqual(
            self.upload(project_id + 99).status_code, 404
        )
        response = self.upload(
            project_id, artifact_type='malware', access_policy='private'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('artifact type', response.get_json()['error'])

    def test_oversized_upload_is_rejected(self):
        project_id = self.make_course_project('artifact-owner')
        with self.app.app_context():
            self.app.config['ARTIFACT_MAX_BYTES'] = 8
        response = self.upload(project_id, data=b'x' * 9)
        self.assertEqual(response.status_code, 413)

    def test_worker_can_store_execution_artifact(self):
        with self.app.app_context():
            user = User(username='worker-owner', email='worker@example.test')
            db.session.add(user)
            db.session.commit()
            artifact = create_artifact(
                owner_id=user.id,
                project_type='execution',
                project_id=None,
                artifact_type='output',
                filename='run.log',
                data=b'ok\n',
                content_type='text/plain',
            )
            self.assertEqual(get_artifact(artifact.id).storage_key, artifact.storage_key)
            with self.assertRaises(ArtifactError):
                create_artifact(
                    owner_id=user.id,
                    project_type='execution',
                    project_id=None,
                    artifact_type='output',
                    filename='bad.txt',
                    data=b'x',
                    access_policy='unrestricted',
                )

    def test_mlflow_payload_tracks_existing_experiment_as_source_of_truth(self):
        with self.app.app_context():
            user = User(username='ml-owner', email='ml@example.test')
            db.session.add(user)
            db.session.commit()
            experiment = MLProjectExperiment(
                user_id=user.id,
                pathway_id='ml-specialization',
                module_id='06',
                experiment_name='Baseline model',
                dataset_version='v3',
                model_type='logistic-regression',
                hyperparameters=json.dumps({'C': 1.0}),
                evaluation_metrics=json.dumps({'accuracy': 0.91}),
            )
            db.session.add(experiment)
            db.session.commit()
            create_artifact(
                owner_id=user.id,
                project_type='ml',
                project_id=experiment.id,
                artifact_type='model',
                filename='model.pkl',
                data=b'model-bytes',
            )
            payload = build_run_payload(experiment)
            self.assertEqual(payload['params'], {'C': 1.0})
            self.assertEqual(payload['metrics'], {'accuracy': 0.91})
            self.assertEqual(payload['tags']['dataset.version'], 'v3')
            self.assertEqual(len(payload['artifacts']), 1)

            updated = record_mlflow_run(
                experiment,
                experiment_id='exp-1',
                run_id='run-1',
                tracking_uri='http://mlflow.internal:5000',
                status='finished',
                environment={'python': '3.12', 'profile': 'container_data_science'},
            )
            self.assertEqual(updated['run_id'], 'run-1')
            self.assertEqual(
                updated['environment']['profile'], 'container_data_science'
            )
            with self.assertRaises(TrackingError):
                record_mlflow_run(
                    experiment,
                    experiment_id='exp-1',
                    run_id='run-2',
                    tracking_uri='',
                    status='unknown',
                )


if __name__ == '__main__':
    unittest.main()
