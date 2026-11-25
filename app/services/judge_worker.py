"""Database-backed worker for durable Practice Arena submissions (M3).

The worker is the only process that invokes the container sandbox. It claims
queue rows atomically, applies server-selected execution profiles, enforces
per-user concurrency and submission limits, records health, and publishes
execution metrics back to the submission row.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from datetime import timedelta

import click
from flask import current_app
from sqlalchemy import func, or_

from app import db
from app.execution.profiles import (
    list_profiles,
    profile_for_problem,
    profile_for_workload,
)
from app.models import JudgeWorkerHeartbeat, Submission, utcnow
from app.services.judge import execute_in_sandbox


logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=10)
RATE_WINDOW = timedelta(minutes=1)


def _config_int(name, default):
    try:
        value = int(current_app.config.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _worker_id():
    return os.environ.get('JUDGE_WORKER_ID') or f'{socket.gethostname()}:{os.getpid()}'


def reclaim_stale_submissions(app) -> int:
    """Return RUNNING submissions older than the lease to the pending queue."""
    with app.app_context():
        cutoff = utcnow() - STALE_AFTER
        count = Submission.query.filter(
            Submission.verdict == 'RUNNING',
            or_(
                Submission.started_at.is_(None),
                Submission.started_at < cutoff,
            ),
        ).update({
            Submission.verdict: 'PENDING',
            Submission.started_at: None,
        }, synchronize_session=False)
        db.session.commit()
        if count:
            logger.warning('Reclaimed %s stale judge submissions', count)
        return count


def _excluded_user_ids(limit_key, cutoff, minimum):
    if minimum is None:
        return set()
    rows = (
        db.session.query(Submission.user_id)
        .filter(Submission.submitted_at >= cutoff)
        .group_by(Submission.user_id)
        .having(func.count(Submission.id) >= minimum)
        .all()
    )
    return {row[0] for row in rows}


def _busy_user_ids():
    limit = _config_int('SANDBOX_MAX_CONCURRENCY_PER_USER', 2)
    cutoff = utcnow() - STALE_AFTER
    rows = (
        db.session.query(Submission.user_id)
        .filter(
            Submission.verdict == 'RUNNING',
            or_(Submission.started_at.is_(None), Submission.started_at >= cutoff),
        )
        .group_by(Submission.user_id)
        .having(func.count(Submission.id) >= limit)
        .all()
    )
    return {row[0] for row in rows}


def update_worker_heartbeat(app, *, status='online', processed_increment=0) -> dict:
    """Persist and return the latest worker health snapshot."""
    with app.app_context():
        now = utcnow()
        pending = Submission.query.filter_by(verdict='PENDING').count()
        running = Submission.query.filter_by(verdict='RUNNING').count()
        worker_id = _worker_id()
        heartbeat = db.session.get(JudgeWorkerHeartbeat, worker_id)
        if heartbeat is None:
            heartbeat = JudgeWorkerHeartbeat(
                id=worker_id,
                hostname=socket.gethostname(),
                pid=os.getpid(),
                started_at=now,
                processed_count=0,
            )
            db.session.add(heartbeat)
        heartbeat.hostname = socket.gethostname()
        heartbeat.pid = os.getpid()
        heartbeat.status = status
        heartbeat.execution_profiles = json.dumps([
            profile.name for profile in list_profiles() if profile.enabled
        ])
        heartbeat.pending_count = pending
        heartbeat.running_count = running
        heartbeat.processed_count = (
            heartbeat.processed_count or 0
        ) + processed_increment
        heartbeat.last_seen_at = now
        db.session.commit()
        return {
            'id': heartbeat.id,
            'status': heartbeat.status,
            'hostname': heartbeat.hostname,
            'pid': heartbeat.pid,
            'started_at': heartbeat.started_at.isoformat(),
            'last_seen_at': heartbeat.last_seen_at.isoformat(),
            'pending_count': heartbeat.pending_count,
            'running_count': heartbeat.running_count,
            'processed_count': heartbeat.processed_count,
            'execution_profiles': json.loads(heartbeat.execution_profiles or '[]'),
        }


def get_worker_health(app) -> dict:
    """Return an operator-facing health snapshot without claiming work."""
    with app.app_context():
        cutoff = utcnow() - STALE_AFTER
        stale = Submission.query.filter(
            Submission.verdict == 'RUNNING',
            or_(Submission.started_at.is_(None), Submission.started_at < cutoff),
        ).count()
        heartbeat = (
            JudgeWorkerHeartbeat.query
            .order_by(JudgeWorkerHeartbeat.last_seen_at.desc())
            .first()
        )
        return {
            'submissions_enabled': bool(
                app.config.get('JUDGE_SUBMISSIONS_ENABLED')
            ),
            'sandbox_image': app.config.get('SANDBOX_IMAGE'),
            'max_concurrency_per_user': _config_int(
                'SANDBOX_MAX_CONCURRENCY_PER_USER', 2
            ),
            'submission_limit_per_minute': _config_int(
                'SANDBOX_SUBMISSION_LIMIT_PER_MINUTE', 10
            ),
            'enabled_profiles': [
                profile.name for profile in list_profiles() if profile.enabled
            ],
            'pending': Submission.query.filter_by(verdict='PENDING').count(),
            'running': Submission.query.filter_by(verdict='RUNNING').count(),
            'stale': stale,
            'worker': {
                'id': heartbeat.id,
                'status': heartbeat.status,
                'hostname': heartbeat.hostname,
                'last_seen_at': heartbeat.last_seen_at.isoformat(),
                'processed_count': heartbeat.processed_count,
            } if heartbeat is not None else None,
        }


def process_next_submission(app) -> bool:
    """Claim and execute one eligible queued submission."""
    with app.app_context():
        reclaim_stale_submissions(app)
        rate_limited = _excluded_user_ids(
            'SANDBOX_SUBMISSION_LIMIT_PER_MINUTE',
            utcnow() - RATE_WINDOW,
            _config_int('SANDBOX_SUBMISSION_LIMIT_PER_MINUTE', 10),
        )
        busy = _busy_user_ids()
        excluded = rate_limited | busy
        query = Submission.query.filter_by(verdict='PENDING')
        if excluded:
            query = query.filter(~Submission.user_id.in_(excluded))
        submission = (
            query.order_by(Submission.submitted_at, Submission.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if submission is None:
            db.session.rollback()
            return False

        submission_id = submission.id
        from app.practice_arena import get_arena_problem
        problem = get_arena_problem(submission.problem_id)
        mode = getattr(submission, 'mode', 'judge') or 'judge'
        workload = 'arena_run' if mode == 'run' else 'arena_submit'
        try:
            profile = profile_for_problem(problem or {}) if problem else (
                profile_for_workload(workload)
            )
        except ValueError:
            profile = profile_for_workload(workload)
        submission.verdict = 'RUNNING'
        submission.started_at = utcnow()
        submission.execution_profile = profile.name
        db.session.commit()

        submission = db.session.get(Submission, submission_id)
        try:
            if mode == 'run':
                result = execute_in_sandbox(
                    submission.code_snapshot,
                    '',
                    timeout_sec=profile.timeout_sec,
                    memory_mb=profile.memory_mb,
                    mode='run',
                    profile=profile,
                )
            else:
                if problem is None:
                    raise ValueError('Problem test suite is unavailable')
                tests = problem.get('judge_tests') or problem.get('browser_checks') or ''
                if not tests:
                    raise ValueError('Problem test suite is unavailable')
                result = execute_in_sandbox(
                    submission.code_snapshot,
                    tests,
                    timeout_sec=profile.timeout_sec,
                    memory_mb=profile.memory_mb,
                    profile=profile,
                )
            submission.verdict = result.verdict
            submission.output = getattr(result, 'output', '') or ''
            submission.execution_time_ms = result.execution_time_ms
            submission.memory_kb = result.memory_kb
            submission.tests_passed = result.tests_passed
            submission.total_tests = result.total_tests
            submission.error_details = result.error_details
            submission.execution_profile = result.execution_profile or profile.name
            logger.info(
                'Judge submission %s profile=%s verdict=%s ms=%s memory_kb=%s',
                submission_id, submission.execution_profile, submission.verdict,
                submission.execution_time_ms, submission.memory_kb,
            )
        except Exception:
            logger.exception('Judge worker failed submission %s', submission_id)
            submission.verdict = 'INTERNAL_ERROR'
            submission.error_details = 'Sandbox execution could not be completed'
        submission.completed_at = utcnow()
        db.session.commit()
        if submission.verdict == 'ACCEPTED':
            try:
                from app.services.skill_passport import update_skill_progress_from_submission
                update_skill_progress_from_submission(submission)
            except Exception:
                logger.exception(
                    'Could not update Skill Passport for submission %s',
                    submission_id,
                )
        update_worker_heartbeat(
            app, status='online', processed_increment=1
        )
        return True


def run_worker(app, poll_seconds: float = 1.0,
               stop: 'WorkerStop | None' = None) -> None:
    """Continuously process queued submissions until a stop signal arrives."""
    if stop is None:
        from app.workers.lifecycle import WorkerStop
        stop = WorkerStop().install()
    reclaim_stale_submissions(app)
    update_worker_heartbeat(app, status='starting')
    try:
        while not stop.should_stop():
            try:
                if not process_next_submission(app):
                    update_worker_heartbeat(app, status='idle')
                    stop.wait(poll_seconds)
            except KeyboardInterrupt:
                stop.handle()
            except Exception:
                logger.exception('Judge worker loop failed')
                update_worker_heartbeat(app, status='error')
                stop.wait(max(poll_seconds, 1.0))
    finally:
        update_worker_heartbeat(app, status='stopped')


@click.command('process-submissions')
@click.option('--once', is_flag=True, help='Process at most one submission and exit.')
@click.option('--poll-seconds', default=1.0, show_default=True, type=float)
def process_submissions(once, poll_seconds):
    """Process queued judge submissions from the durable database queue."""
    app = current_app._get_current_object()
    reclaim_stale_submissions(app)
    if once:
        process_next_submission(app)
        return
    run_worker(app, poll_seconds)


@click.command('judge-worker-health')
def judge_worker_health():
    """Print the execution subsystem health snapshot as JSON."""
    click.echo(json.dumps(get_worker_health(current_app._get_current_object())))


def register_judge_worker_cli(app) -> None:
    app.cli.add_command(process_submissions)
    app.cli.add_command(judge_worker_health)


def main() -> None:
    from app import create_app

    app = create_app()
    app.logger.info('Starting RUACH judge worker')
    run_worker(app)


if __name__ == '__main__':
    main()
