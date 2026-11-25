"""Standalone ML worker (M5).

    python -m app.workers.ml_worker

Separate queue, separate handlers, separate heartbeat from the AI worker.
SIGTERM/SIGINT stop cooperatively through ``WorkerStop``.
"""

import logging

import click
from flask import current_app

from app.models import MLBackgroundJob
from app.services.ml_jobs import claim_next_job, finish_job
from app.workers.lifecycle import WorkerStop
from app.workers.ml_handlers import handle

logger = logging.getLogger(__name__)


def _heartbeat(app, status):
    try:
        from app.services.operations import record_heartbeat
        record_heartbeat('ml-worker', status=status, detail={'queue': 'ml_background_job'})
    except Exception:
        logger.warning('Could not record ML worker heartbeat', exc_info=True)


def process_one_job(app):
    """Process at most one ML job; return whether work was found."""
    claimed = claim_next_job(app)
    if claimed is None:
        return False
    job_id, lease = claimed
    with app.app_context():
        from app import db
        job = db.session.get(MLBackgroundJob, job_id)
        if job is None or job.lease_token != lease:
            return True
        if job.status == 'cancelled':
            finish_job(job_id, lease, error='Cancelled before execution')
            return True
        try:
            result = handle(job_id, job.job_type, job.payload)
            finish_job(job_id, lease, result=result)
        except (ValueError, TypeError) as error:
            finish_job(job_id, lease, error=error)
        except Exception as error:
            logger.exception('ML job %s failed', job_id)
            finish_job(job_id, lease, error=error, retry=True)
    return True


def run_worker(app, poll_seconds=1.0, stop=None, once=False):
    """ML worker loop; ``once`` processes at most one job."""
    if stop is None:
        stop = WorkerStop().install()
    _heartbeat(app, 'starting')
    if once:
        processed = process_one_job(app)
        _heartbeat(app, 'idle' if not processed else 'online')
        return processed
    try:
        while not stop.should_stop():
            try:
                processed = process_one_job(app)
                if not processed:
                    stop.wait(max(0.1, poll_seconds))
            except Exception:
                logger.exception('ML worker iteration failed')
                _heartbeat(app, 'degraded')
                stop.wait(max(0.1, poll_seconds))
    finally:
        _heartbeat(app, 'stopped')


@click.command('process-ml-jobs')
@click.option('--once', is_flag=True, help='Process at most one job and exit.')
@click.option('--poll-seconds', default=1.0, show_default=True, type=float)
def process_ml_jobs(once, poll_seconds):
    """Process queued ML jobs from the durable ML-specific queue."""
    app = current_app._get_current_object()
    run_worker(app, poll_seconds, once=once)


def register_ml_job_cli(app):
    app.cli.add_command(process_ml_jobs)


def main():
    from app import create_app
    app = create_app()
    app.logger.info('Starting RUACH ML job worker')
    run_worker(app)


if __name__ == '__main__':
    main()
