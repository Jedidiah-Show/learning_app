"""Worker entry point for durable AI jobs (M2.5)."""

import click
from flask import current_app

from app.workers.base import run_worker


@click.command('process-ai-jobs')
@click.option('--once', is_flag=True, help='Process at most one job and exit.')
@click.option('--poll-seconds', default=1.0, show_default=True, type=float)
def process_ai_jobs(once, poll_seconds):
    """Process queued AI jobs from the durable database queue."""
    run_worker(current_app._get_current_object(), poll_seconds, once=once)


def register_ai_job_cli(app) -> None:
    app.cli.add_command(process_ai_jobs)


def main() -> None:
    """Standalone entry point: python -m app.workers.ai_worker."""
    from app import create_app

    app = create_app()
    app.logger.info('Starting RUACH AI job worker')
    run_worker(app)


if __name__ == '__main__':
    main()
