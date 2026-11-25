"""M5 — production-readiness telemetry, process and backup regression tests."""

import json
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import timedelta

from alembic.config import Config
from alembic.script import ScriptDirectory
from werkzeug.security import generate_password_hash
import yaml

from app import create_app, db
from app.core.observability import (
    REQUEST_ID_HEADER, JsonFormatter, reset_request_metrics, request_metrics,
)
from app.models import (
    AIBackgroundJob, JudgeWorkerHeartbeat, ServiceHeartbeat, Submission, User,
    utcnow,
)
from app.services.operations import (
    OperationsError, evaluate_alerts, heartbeats, operations_snapshot,
    record_heartbeat,
)
from app.workers.scheduler import run_once
from scripts.backup_database import create_backup
from scripts.restore_database import execute_restore, restore_plan

ROOT = Path(__file__).resolve().parent.parent


class M5OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            db.create_all()
            self.learner_id = self._create_user('m5learner', is_admin=False)
            self.admin_id = self._create_user('m5admin', is_admin=True)
        self.client = self.app.test_client()
        reset_request_metrics()

    def tearDown(self):
        reset_request_metrics()
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = self.previous_database_url
        self.temp_dir.cleanup()

    def _create_user(self, username, *, is_admin=False):
        user = User(
            username=username,
            email=f'{username}@example.test',
            full_name=username.title(),
            password_hash=generate_password_hash('secure-pass-123'),
            is_admin=is_admin,
        )
        db.session.add(user)
        db.session.commit()
        return user.id

    def _login(self, endpoint, identifier):
        return self.client.post(endpoint, data={
            'identifier' if endpoint == '/admin/login' else 'username': identifier,
            'password': 'secure-pass-123',
        })

    def test_json_formatter_emits_only_whitelisted_fields(self):
        record = logging.LogRecord(
            'ruach.test', logging.INFO, __file__, 1, 'hello %s', ('world',), None,
        )
        record.request_id = 'correlation-1'
        record.event = 'request'
        record.secret_should_not_appear = 'never'
        payload = json.loads(JsonFormatter().format(record))
        self.assertEqual(payload['message'], 'hello world')
        self.assertEqual(payload['request_id'], 'correlation-1')
        self.assertEqual(payload['event'], 'request')
        self.assertIn('app_version', payload)
        self.assertNotIn('secret_should_not_appear', payload)

    def test_request_hooks_add_correlation_id_and_latency_metrics(self):
        reset_request_metrics()

        @self.app.route('/__m5_probe__')
        def m5_probe():
            db.session.query(User).count()
            return 'ok'

        response = self.client.get(
            '/__m5_probe__', headers={REQUEST_ID_HEADER: 'test-correlation-1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers[REQUEST_ID_HEADER], 'test-correlation-1')
        metrics = request_metrics()
        self.assertGreaterEqual(metrics['requests'], 1)
        self.assertGreater(metrics['average_db_queries'], 0)

    def test_operations_endpoint_requires_admin_and_hides_secrets(self):
        anonymous = self.client.get('/api/admin/operations')
        self.assertEqual(anonymous.status_code, 401)

        self._login('/login', 'm5learner')
        learner = self.client.get('/api/admin/operations')
        self.assertEqual(learner.status_code, 403)
        self.client.post('/logout')

        self._login('/admin/login', 'm5admin')
        response = self.client.get('/api/admin/operations')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        for key in (
            'generated_at', 'release', 'database', 'requests', 'queues',
            'workers', 'ai_usage_24h', 'cache', 'storage', 'alerts',
        ):
            self.assertIn(key, payload)
        self.assertIn('ai', payload['queues'])
        self.assertIn('judge', payload['queues'])
        self.assertIn('services', payload['workers'])
        serialized = json.dumps(payload)
        self.assertNotIn('SECRET_KEY', serialized)
        self.assertNotIn('DATABASE_URL', serialized)
        self.assertNotIn('secure-pass-123', serialized)

    def test_heartbeat_is_upserted_and_staleness_is_detected(self):
        with self.app.app_context():
            record_heartbeat('ai-worker', detail={'pass': 1}, instance_id='worker-a')
            record_heartbeat(
                'ai-worker', status='degraded',
                detail={'pass': 2}, instance_id='worker-b',
            )
            rows = heartbeats()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['status'], 'degraded')
            self.assertEqual(rows[0]['detail']['pass'], 2)
            self.assertFalse(rows[0]['stale'])

            with self.assertRaises(OperationsError):
                record_heartbeat('Bad Service')
            with self.assertRaises(OperationsError):
                record_heartbeat('scheduler', status='unknown')

            row = db.session.get(ServiceHeartbeat, 'ai-worker')
            row.last_seen_at = utcnow() - timedelta(seconds=999)
            db.session.commit()
            self.assertTrue(heartbeats(stale_after_seconds=10)[0]['stale'])

    def test_queue_metrics_and_alert_conditions(self):
        with self.app.app_context():
            db.session.add(AIBackgroundJob(
                job_key='m5-queue-probe',
                job_type='ai_generation',
                user_id=self.learner_id,
                payload='{}',
                status='queued',
                available_at=utcnow() - timedelta(seconds=1200),
            ))
            db.session.commit()
            snapshot = operations_snapshot(self.app)
            self.assertEqual(snapshot['queues']['ai']['queued'], 1)
            self.assertGreaterEqual(
                snapshot['queues']['ai']['oldest_queued_age_seconds'], 1000
            )
            self.app.config['AI_QUEUE_ALERT_DEPTH'] = 1
            self.app.config['AI_QUEUE_ALERT_AGE_SECONDS'] = 1
            codes = {alert['code'] for alert in evaluate_alerts(snapshot)}
            self.assertIn('ai_queue_backlog', codes)
            self.assertIn('ai_queue_oldest_pending', codes)

    def test_stale_judge_worker_raises_derived_alert(self):
        """The judge worker's own heartbeat must produce an alert when dead."""
        with self.app.app_context():
            db.session.add(JudgeWorkerHeartbeat(
                id='judge-a', hostname='judge-host', pid=4242,
                status='online', started_at=utcnow() - timedelta(seconds=2000),
                last_seen_at=utcnow() - timedelta(seconds=999),
            ))
            db.session.commit()
            self.app.config['HEARTBEAT_STALE_SECONDS'] = 10
            snapshot = operations_snapshot(self.app)
            codes = {alert['code'] for alert in snapshot['alerts']}
            self.assertIn('judge_worker_stale', codes)
            self.assertNotIn('judge_heartbeat_invalid', codes)
            # Snapshot shape and secret-free guarantee remain unchanged.
            self.assertIn('judge', snapshot['workers'])
            serialized = json.dumps(snapshot)
            self.assertNotIn('SECRET_KEY', serialized)
            self.assertNotIn('secure-pass-123', serialized)

            row = db.session.get(JudgeWorkerHeartbeat, 'judge-a')
            row.status = 'degraded'
            row.last_seen_at = utcnow()
            db.session.commit()
            codes = {alert['code'] for alert in evaluate_alerts(operations_snapshot(self.app))}
            self.assertNotIn('judge_worker_stale', codes)
            self.assertIn('judge_worker_unhealthy', codes)

    def test_judge_backlog_and_dead_letter_alerts_use_existing_data(self):
        with self.app.app_context():
            db.session.add(Submission(
                id='judge-backlog-1', user_id=self.learner_id,
                problem_id='p1', code_snapshot='print(1)', verdict='PENDING',
            ))
            db.session.add(AIBackgroundJob(
                job_key='m5-dead-letter', job_type='ai_generation',
                user_id=self.learner_id, payload='{}', status='dead_letter',
                available_at=utcnow(),
            ))
            db.session.commit()
            self.app.config['AI_QUEUE_ALERT_DEPTH'] = 1
            codes = {
                alert['code'] for alert in operations_snapshot(self.app)['alerts']
            }
            self.assertIn('judge_queue_backlog', codes)
            self.assertIn('ai_job_dead_letter', codes)

    def test_scheduler_pass_records_generic_heartbeat(self):
        with self.app.app_context():
            report = run_once(self.app, tasks=('ai-queue-reclaim',))
            self.assertEqual(report['status'], 'online')
            row = db.session.get(ServiceHeartbeat, 'scheduler')
            self.assertIsNotNone(row)
            self.assertEqual(row.status, 'online')
            self.assertEqual(row.get_detail()['tasks'], ['ai-queue-reclaim'])

    def test_sqlite_backup_and_restore_round_trip(self):
        source = Path(self.temp_dir.name) / 'source.sqlite3'
        with sqlite3.connect(source) as connection:
            connection.execute('CREATE TABLE marker (value TEXT)')
            connection.execute("INSERT INTO marker VALUES ('original')")

        destination_dir = Path(self.temp_dir.name) / 'backups'
        dry = create_backup(
            database_url=f'sqlite:///{source}',
            output_dir=destination_dir,
            dry_run=True,
        )
        self.assertTrue(dry['dry_run'])
        self.assertFalse(destination_dir.exists())

        result = create_backup(
            database_url=f'sqlite:///{source}', output_dir=destination_dir,
        )
        backup = Path(result['destination'])
        self.assertTrue(backup.exists())
        self.assertGreater(result['size_bytes'], 0)

        with sqlite3.connect(source) as connection:
            connection.execute("UPDATE marker SET value = 'changed'")
        plan = restore_plan(
            backup_path=backup, database_url=f'sqlite:///{source}'
        )
        execute_restore(plan)
        with sqlite3.connect(source) as connection:
            value = connection.execute('SELECT value FROM marker').fetchone()[0]
        self.assertEqual(value, 'original')

    def test_backup_and_restore_refuse_unsafe_inputs(self):
        output_dir = Path(self.temp_dir.name) / 'backups'
        with self.assertRaises(ValueError):
            create_backup(
                database_url='sqlite:///:memory:', output_dir=output_dir,
                dry_run=True,
            )

        postgres_url = 'postgresql://user:secret@db.example.test:5432/ruach'
        planned = create_backup(
            database_url=postgres_url, output_dir=output_dir, dry_run=True,
        )
        self.assertIn('pg_dump', planned['command'])
        self.assertNotIn('secret', planned['command'])

        empty = Path(self.temp_dir.name) / 'empty.dump'
        empty.write_bytes(b'')
        with self.assertRaises(ValueError):
            restore_plan(backup_path=empty, database_url=postgres_url)

        real_backup = Path(self.temp_dir.name) / 'valid.dump'
        real_backup.write_bytes(b'pgdump-bytes')
        restore = restore_plan(backup_path=real_backup, database_url=postgres_url)
        self.assertEqual(restore['argv'][0], 'pg_restore')
        self.assertNotIn('secret', restore['command'])

        with self.assertRaises(ValueError):
            restore_plan(backup_path=real_backup, database_url=os.environ['DATABASE_URL'])

    def test_render_manifest_and_dependency_monitoring(self):
        data = yaml.safe_load((ROOT / 'render.yaml').read_text(encoding='utf-8'))
        names = {service['name'] for service in data['services']}
        self.assertIn('ruach-learning-app', names)
        self.assertIn('ruach-ai-worker', names)
        self.assertIn('ruach-scheduler', names)
        self.assertNotIn('ruach-judge-worker', names)

        web = next(
            service for service in data['services']
            if service['name'] == 'ruach-learning-app'
        )
        web_env = {entry['key']: entry for entry in web['envVars']}
        self.assertEqual(web_env['JUDGE_SUBMISSIONS_ENABLED']['value'], 'false')
        self.assertEqual(web_env['LOG_FORMAT']['value'], 'json')

        dependabot = yaml.safe_load(
            (ROOT / '.github' / 'dependabot.yml').read_text(encoding='utf-8')
        )
        self.assertEqual(dependabot['version'], 2)
        ecosystems = {entry['package-ecosystem'] for entry in dependabot['updates']}
        self.assertTrue({'pip', 'npm', 'github-actions'}.issubset(ecosystems))

    def test_m5_migration_descends_from_m4_head(self):
        config = Config()
        config.set_main_option('script_location', str(ROOT / 'migrations'))
        script = ScriptDirectory.from_config(config)
        revision = script.get_revision('k6l7m8n9o0p1')
        self.assertEqual(revision.down_revision, 'j5k6l7m8n9o0')

    def test_m5_modules_do_not_introduce_a_second_queue(self):
        for module in ('app/services/operations.py', 'app/workers/scheduler.py'):
            source = (ROOT / module).read_text(encoding='utf-8').lower()
            self.assertNotIn('celery', source)
            self.assertNotIn('rabbitmq', source)
            self.assertNotIn('redis', source)


if __name__ == '__main__':
    unittest.main()
