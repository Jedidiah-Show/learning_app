"""M7 worker lifecycle tests: cooperative SIGTERM/SIGINT shutdown."""

import signal
from unittest.mock import patch

from app.workers.lifecycle import WorkerStop


def test_worker_stop_is_a_flag_with_bounded_wait():
    stop = WorkerStop()
    assert stop.should_stop() is False
    assert stop.wait(0.001) is False
    stop.handle(signal.SIGTERM, None)
    assert stop.should_stop() is True
    assert stop.wait(0.001) is True


def test_install_registers_sigterm_and_sigint_once():
    stop = WorkerStop()
    with patch('app.workers.lifecycle.signal.signal') as register:
        stop.install()
        stop.install()
    assert register.call_count == 2
    assert {call.args[0] for call in register.call_args_list} == {
        signal.SIGTERM, signal.SIGINT,
    }
    assert all(call.args[1] == stop.handle for call in register.call_args_list)


def test_ai_worker_exits_poll_loop_on_stop_and_publishes_stopped_heartbeat():
    from app.workers import base

    stop = WorkerStop()
    stop.handle()
    app = object()
    with patch.object(base, 'reclaim_stale_jobs'), \
         patch.object(base, '_record_worker_heartbeat') as heartbeat, \
         patch.object(base, 'process_one_job') as process:
        result = base.run_worker(app, poll_seconds=0.001, stop=stop)
    assert result is True
    process.assert_not_called()
    assert any(
        call.kwargs.get('status') == 'stopped' or 'stopped' in call.args
        for call in heartbeat.call_args_list
    )


def test_ai_worker_processes_once_before_stopping():
    from app.workers import base

    stop = WorkerStop()
    calls = {'n': 0}

    def fake_process(app):
        calls['n'] += 1
        stop.handle()
        return True

    with patch.object(base, 'reclaim_stale_jobs'), \
         patch.object(base, '_record_worker_heartbeat'), \
         patch.object(base, 'process_one_job', side_effect=fake_process):
        base.run_worker(object(), poll_seconds=0.001, stop=stop)
    assert calls['n'] == 1


def test_judge_worker_exits_poll_loop_on_stop_and_publishes_stopped_heartbeat():
    from app.services import judge_worker

    stop = WorkerStop()
    stop.handle()
    app = object()
    with patch.object(judge_worker, 'reclaim_stale_submissions'), \
         patch.object(judge_worker, 'update_worker_heartbeat') as heartbeat, \
         patch.object(judge_worker, 'process_next_submission') as process:
        judge_worker.run_worker(app, poll_seconds=0.001, stop=stop)
    process.assert_not_called()
    assert any(call.kwargs.get('status') == 'stopped'
               for call in heartbeat.call_args_list)


def test_duplicate_claims_cannot_execute_one_job_twice():
    """M7: concurrent duplicate delivery must not run the same job twice."""
    import os
    import tempfile
    from datetime import timedelta

    from app import create_app, db
    from app.models import AIBackgroundJob, User, utcnow
    from app.workers.base import claim_next_job, reclaim_stale_jobs

    tmp = tempfile.TemporaryDirectory()
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = f'sqlite:///{tmp.name}/dupes.db'
    app = create_app()
    app.config.update(TESTING=True, GEMINI_API_KEY=None, OPENROUTER_API_KEY=None)
    try:
        with app.app_context():
            db.create_all()
            user = User(username='dupe', email='dupe@example.test', password_hash='x')
            db.session.add(user)
            db.session.commit()
            db.session.add(AIBackgroundJob(
                user_id=user.id, job_key='same-key', job_type='ai_generation',
                payload='{}', status='queued', available_at=utcnow(),
                max_attempts=3,
            ))
            db.session.commit()
            first = claim_next_job(app)
            second = claim_next_job(app)
            assert first is not None and second is None
            # A crashed worker's lease is recoverable after the stale window.
            job = db.session.get(AIBackgroundJob, first[0])
            job.locked_at = utcnow() - timedelta(seconds=1200)
            db.session.commit()
            assert reclaim_stale_jobs(app, stale_seconds=600) == 1
            assert claim_next_job(app) is not None
    finally:
        with app.app_context():
            db.drop_all()
            db.engine.dispose()
        if previous is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = previous
        tmp.cleanup()


def test_worker_publishes_degraded_heartbeat_before_stopping():
    """M7: an iteration failure is visible, then shutdown is still clean."""
    from app.workers import base

    stop = WorkerStop()
    calls = {'n': 0}

    def failing_process(app):
        calls['n'] += 1
        stop.handle()
        raise RuntimeError('injected worker failure')

    with patch.object(base, 'reclaim_stale_jobs'), \
         patch.object(base, '_record_worker_heartbeat') as heartbeat, \
         patch.object(base, 'process_one_job', side_effect=failing_process):
        base.run_worker(object(), poll_seconds=0.001, stop=stop)
    statuses = [call.kwargs.get('status') for call in heartbeat.call_args_list]
    assert 'degraded' in statuses and 'stopped' in statuses
    assert calls['n'] == 1
