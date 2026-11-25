"""Scheduled maintenance runner for M5.

This is a plain Python loop sharing the existing database-backed queue. It is
not a second job system: it only invokes maintenance hooks already owned by
other modules and reports availability through the generic service heartbeat.
"""

from __future__ import annotations

import logging
import os
import socket
import time

import click
from flask import current_app

from app.core.logging import configure_worker_logging
from app.services.operations import record_heartbeat

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_TASKS = ('ai-queue-reclaim',)


def _config_int(name, default):
    raw = current_app.config.get(name, os.environ.get(name))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _task_functions():
    from app.leaderboard import rebuild_leaderboard_scores
    from app.workers.base import reclaim_stale_jobs

    return {
        'ai-queue-reclaim': reclaim_stale_jobs,
        'leaderboard-rebuild': lambda app: rebuild_leaderboard_scores(),
    }


def configured_tasks():
    raw = os.environ.get(
        'SCHEDULED_TASKS', ','.join(DEFAULT_TASKS)
    )
    allowed = set(_task_functions())
    tasks = tuple(
        dict.fromkeys(
            item.strip() for item in raw.split(',')
            if item.strip() in allowed
        )
    )
    return tasks or DEFAULT_TASKS


def run_once(app, *, tasks=None):
    """Run one maintenance pass and return a secret-free report."""
    configure_worker_logging()
    selected = tuple(tasks) if tasks is not None else configured_tasks()
    started = time.monotonic()
    with app.app_context():
        instance = f'{socket.gethostname()}:{os.getpid()}'
        record_heartbeat(
            'scheduler', status='starting',
            detail={'instance': instance, 'tasks': list(selected)},
            instance_id=instance,
        )
        report = {}
        for name in selected:
            try:
                function = _task_functions()[name]
                result = function(app)
                report[name] = {
                    'ok': True,
                    'result': result if isinstance(result, int) else None,
                }
            except Exception as error:  # keep other tasks running
                logger.exception('Scheduled task %s failed', name)
                report[name] = {'ok': False, 'error_type': type(error).__name__}
        status = 'degraded' if any(not row['ok'] for row in report.values()) else 'online'
        record_heartbeat(
            'scheduler', status=status,
            detail={
                'instance': instance,
                'tasks': list(selected),
                'failed_tasks': [
                    name for name, row in report.items() if not row['ok']
                ],
                'duration_ms': round((time.monotonic() - started) * 1000, 2),
            },
            instance_id=instance,
        )
    return {'status': status, 'tasks': report}


@click.command('run-scheduled-jobs')
@click.option('--once', is_flag=True, help='Run one maintenance pass and exit.')
@click.option('--interval-seconds', default=300, show_default=True, type=int)
def scheduled_jobs(once, interval_seconds):
    """Run configured maintenance tasks on a bounded interval."""
    from app import create_app

    app = create_app()
    configure_worker_logging()
    if once:
        run_once(app)
        return
    interval = max(30, interval_seconds)
    from app.workers.lifecycle import WorkerStop
    stop = WorkerStop().install()
    while not stop.should_stop():
        try:
            run_once(app)
        except Exception:
            logger.exception('Scheduled maintenance pass failed')
        stop.wait(interval)


def register_scheduler_cli(app) -> None:
    app.cli.add_command(scheduled_jobs)


def main() -> None:
    """Standalone entry point: python -m app.workers.scheduler."""
    configure_worker_logging()
    raw = os.environ.get('SCHEDULER_INTERVAL_SECONDS', str(DEFAULT_INTERVAL_SECONDS))
    try:
        interval = int(raw)
    except (TypeError, ValueError):
        interval = DEFAULT_INTERVAL_SECONDS
    interval = max(30, interval)
    scheduled_jobs.main(
        args=['--interval-seconds', str(interval)], prog_name='scheduled-jobs',
        standalone_mode=True,
    )


if __name__ == '__main__':
    main()
