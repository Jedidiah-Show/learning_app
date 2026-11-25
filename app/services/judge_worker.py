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
import re
import socket
from typing import TYPE_CHECKING

from app.services.judge import JudgeResult

if TYPE_CHECKING:
    from app.workers.lifecycle import WorkerStop
from datetime import timedelta

import click
from flask import current_app
from sqlalchemy import func, or_

from app import db
from app.core.observability import log_context
from app.execution.profiles import (
    ProfileDisabledError,
    list_profiles,
    profile_for_problem,
    profile_for_workload,
)
from app.models import JudgeWorkerHeartbeat, Submission, utcnow
from app.services.judge import (
    execute_in_sandbox,
    normalize_verdict,
    sanitize_result_for_storage,
)


logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=10)
RATE_WINDOW = timedelta(minutes=1)
# Default matches the container_python profile; operators can raise it with
# SANDBOX_MAX_CONCURRENCY (app config or environment) without a model change.
MAX_GLOBAL_CONCURRENCY = 4
DEDUPE_WINDOW_SECONDS = 300
_ATTEMPT_MARKER = re.compile(r'\[judge-attempt:(\d+)\]')


def _config_nonnegative_int(name, default, maximum=None):
    raw = current_app.config.get(name, os.environ.get(name, default))
    try:
        value = int(raw)
    except (TypeError, ValueError, OverflowError):
        return default
    value = max(0, value)
    return value if maximum is None else min(value, maximum)


def _global_concurrency_limit():
    """Process-wide cap derived from existing submission state/config."""
    value = _config_nonnegative_int(
        'SANDBOX_MAX_CONCURRENCY', MAX_GLOBAL_CONCURRENCY, 1000,
    )
    return value or MAX_GLOBAL_CONCURRENCY


def _max_attempts():
    """Bounded retry budget; one attempt (no retry) by default."""
    value = _config_nonnegative_int('SANDBOX_MAX_ATTEMPTS', 1, 5)
    return max(1, value)


def _dedupe_window_seconds():
    return _config_nonnegative_int(
        'SANDBOX_DEDUPE_WINDOW_SECONDS', DEDUPE_WINDOW_SECONDS, 3600,
    )


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


def _running_count(profile_name=None):
    """Active leases only; stale RUNNING rows are reclaimed before counting.

    ``execution_profile`` is already on the submission row, so profile-level
    concurrency can be counted without a schema change.
    """
    cutoff = utcnow() - STALE_AFTER
    query = Submission.query.filter(
        Submission.verdict == 'RUNNING',
        or_(Submission.started_at.is_(None), Submission.started_at >= cutoff),
    )
    if profile_name:
        query = query.filter(Submission.execution_profile == profile_name)
    return query.count()


def _find_completed_twin(submission):
    """Find a recent, deterministic result for the same queued work.

    The schema has no idempotency column, so a short-window query over the
    existing identity columns provides dedupe without a migration.
    """
    window = _dedupe_window_seconds()
    if window <= 0:
        return None
    mode = getattr(submission, 'mode', 'judge') or 'judge'
    version = getattr(submission, 'problem_version', None) or ''
    return (
        Submission.query.filter(
            Submission.id != submission.id,
            Submission.user_id == submission.user_id,
            Submission.problem_id == submission.problem_id,
            Submission.code_snapshot == submission.code_snapshot,
            func.coalesce(Submission.mode, 'judge') == mode,
            func.coalesce(Submission.problem_version, '') == version,
            Submission.verdict.in_(('ACCEPTED', 'WRONG_ANSWER')),
            Submission.submitted_at >= utcnow() - timedelta(seconds=window),
        )
        .order_by(Submission.submitted_at.desc())
        .first()
    )


def _attempt_count(error_details):
    matches = _ATTEMPT_MARKER.findall(error_details or '')
    return int(matches[-1]) if matches else 0


def _with_attempt_marker(error_details, attempt, *, dead_letter=False):
    base = _ATTEMPT_MARKER.sub('', error_details or '').strip().rstrip(';')
    marker = f'[judge-attempt:{attempt}]'
    if dead_letter:
        marker += ' [judge-dead-letter]'
    return f'{base}; {marker}' if base else marker


def _apply_storage_fields(submission, fields, *, queue_state=False):
    """Assign only pre-validated, Enum-safe values to the submission row."""
    # Retry deliberately re-queues a row; every other path must be terminal.
    submission.verdict = (
        fields['verdict'] if queue_state else normalize_verdict(fields['verdict'])
    )
    for key in (
        'tests_passed', 'total_tests', 'execution_time_ms', 'memory_kb',
        'error_details', 'output',
    ):
        setattr(submission, key, fields[key])
    if fields.get('execution_profile'):
        submission.execution_profile = fields['execution_profile']


def _store_result(submission_id, fields, *, retry=False):
    """Persist a result, guaranteeing the row never stays RUNNING."""
    try:
        submission = db.session.get(Submission, submission_id)
        if submission is None:
            return None
        _apply_storage_fields(submission, fields, queue_state=retry)
        submission.started_at = None if retry else submission.started_at
        submission.completed_at = None if retry else utcnow()
        db.session.commit()
        return submission.verdict
    except Exception:
        db.session.rollback()
        logger.exception('Could not store judge result for submission %s', submission_id)
        try:
            submission = db.session.get(Submission, submission_id)
            if submission is not None:
                _apply_storage_fields(submission, {
                    'verdict': 'INTERNAL_ERROR',
                    'tests_passed': 0,
                    'total_tests': 0,
                    'execution_time_ms': 0,
                    'memory_kb': 0,
                    'error_details': 'Judge result could not be recorded',
                    'output': '',
                    'execution_profile': '',
                })
                submission.completed_at = utcnow()
                db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception('Could not dead-letter submission %s', submission_id)
        return 'INTERNAL_ERROR'


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
            'max_concurrency': _global_concurrency_limit(),
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


def _internal_result(details, *, profile_name=''):
    result = JudgeResult(
        verdict='INTERNAL_ERROR', error_details=details,
        execution_profile=profile_name,
    )
    return result.safe_fields()


def _finish(submission, app, verdict):
    if verdict == 'ACCEPTED' and submission is not None:
        try:
            from app.services.skill_passport import update_skill_progress_from_submission
            update_skill_progress_from_submission(submission)
        except Exception:
            logger.exception(
                'Could not update Skill Passport for submission %s', submission.id,
            )
    update_worker_heartbeat(app, status='online', processed_increment=1)
    return True


def process_next_submission(app) -> bool:
    """Claim and execute one eligible queued submission."""
    with app.app_context():
        reclaim_stale_submissions(app)
        global_limit = _global_concurrency_limit()
        running = _running_count()
        if running >= global_limit:
            return False
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
        with log_context(job_id=submission_id):
            return _process_claimed_submission(app, submission_id)


def _process_claimed_submission(app, submission_id) -> bool:
    """Validate, run and finalize one already-claimed submission."""
    with app.app_context():
        submission = db.session.get(Submission, submission_id)
        if submission is None:
            return False
        # Duplicate delivery / double-click retry: reuse a recent identical
        # result instead of paying for a second sandbox execution.
        twin = _find_completed_twin(submission)
        if twin is not None:
            logger.info(
                'Judge submission %s reused a recent identical result', submission_id,
            )
            stored_verdict = _store_result(
                submission_id, sanitize_result_for_storage(twin),
            )
            return _finish(
                db.session.get(Submission, submission_id), app, stored_verdict,
            )

        from app.practice_arena import get_arena_problem
        problem = get_arena_problem(submission.problem_id)
        mode = getattr(submission, 'mode', 'judge') or 'judge'
        workload = 'arena_run' if mode == 'run' else 'arena_submit'
        try:
            profile = profile_for_problem(problem or {}) if problem else (
                profile_for_workload(workload)
            )
        except ProfileDisabledError:
            db.session.rollback()
            logger.warning(
                'Judge submission %s requested a disabled execution profile',
                submission_id,
            )
            _store_result(
                submission_id,
                _internal_result('The requested execution profile is disabled'),
            )
            update_worker_heartbeat(app, status='online', processed_increment=1)
            return True
        except ValueError:
            # Unknown declared profiles fall back to the workload default.
            profile = profile_for_workload(workload)

        # Both the global cap and the selected profile's concurrency ceiling
        # apply; stale leases have already been reclaimed above.
        if _running_count(profile.name) >= profile.max_concurrency:
            db.session.rollback()
            return False

        submission.verdict = 'RUNNING'
        submission.started_at = utcnow()
        submission.execution_profile = profile.name
        db.session.commit()

        submission = db.session.get(Submission, submission_id)
        previous_error_details = getattr(submission, 'error_details', '') or ''
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
            fields = result.safe_fields(profile=profile)
            if not fields['execution_profile']:
                fields['execution_profile'] = profile.name
            logger.info(
                'Judge submission %s profile=%s verdict=%s ms=%s memory_kb=%s',
                submission_id, fields['execution_profile'], fields['verdict'],
                fields['execution_time_ms'], fields['memory_kb'],
            )
        except Exception:
            logger.exception('Judge worker failed submission %s', submission_id)
            fields = _internal_result(
                'Sandbox execution could not be completed', profile.name,
            )

        # Bounded retry/dead-letter for transient sandbox/OS failures. The
        # attempt count lives in error_details because the schema has no
        # attempts column; a final INTERNAL_ERROR is the dead-letter state.
        max_attempts = _max_attempts()
        retry = False
        if fields['verdict'] == 'INTERNAL_ERROR' and max_attempts > 1:
            attempt = max(
                _attempt_count(fields['error_details']),
                _attempt_count(previous_error_details),
            ) + 1
            if attempt < max_attempts:
                fields['verdict'] = 'PENDING'
                fields['error_details'] = _with_attempt_marker(
                    fields['error_details'], attempt,
                )
                retry = True
            else:
                fields['error_details'] = _with_attempt_marker(
                    fields['error_details'], attempt, dead_letter=True,
                )
        elif fields['verdict'] != 'INTERNAL_ERROR':
            fields['error_details'] = _ATTEMPT_MARKER.sub(
                '', fields['error_details'],
            ).strip()

        verdict = _store_result(submission_id, fields, retry=retry)
        if verdict is None:
            return True
        if retry:
            update_worker_heartbeat(app, status='idle', processed_increment=0)
            return True
        return _finish(db.session.get(Submission, submission_id), app, verdict)


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


def _configure_worker_logging(app) -> None:
    """Adopt the shared worker log format when the sibling module is present."""
    try:
        from app.core.logging import configure_worker_logging
    except ImportError:
        return
    try:
        configure_worker_logging(app)
    except TypeError:
        configure_worker_logging()
    except Exception:
        logger.exception('Could not configure worker logging')


def main() -> None:
    from app import create_app

    app = create_app()
    _configure_worker_logging(app)
    app.logger.info('Starting RUACH judge worker')
    run_worker(app)


if __name__ == '__main__':
    main()
