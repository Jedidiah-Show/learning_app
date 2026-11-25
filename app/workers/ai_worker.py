"""Worker entry point for durable AI jobs (M2.5)."""

import click
from flask import current_app

from app.core.logging import configure_worker_logging
from app.workers.base import run_worker


@click.command('process-ai-jobs')
@click.option('--once', is_flag=True, help='Process at most one job and exit.')
@click.option('--poll-seconds', default=1.0, show_default=True, type=float)
def process_ai_jobs(once, poll_seconds):
    """Process queued AI jobs from the durable database queue."""
    configure_worker_logging()
    run_worker(current_app._get_current_object(), poll_seconds, once=once)


@click.command('clear-ai-cache')
@click.option(
    '--shared', is_flag=True,
    help='Also purge Redis-backed shared cache in addition to local state.',
)
def clear_ai_cache_command(shared):
    """Operator maintenance: clear cached AI responses (no HTTP endpoint)."""
    from app.ai_cache import clear_ai_cache
    clear_ai_cache(include_shared=shared)
    click.echo(
        'AI cache cleared (%s)' % ('shared and local' if shared else 'local only')
    )


def register_ai_job_cli(app) -> None:
    app.cli.add_command(process_ai_jobs)
    app.cli.add_command(clear_ai_cache_command)


def main() -> None:
    """Standalone entry point: python -m app.workers.ai_worker."""
    from app import create_app

    app = create_app()
    configure_worker_logging()
    app.logger.info('Starting RUACH AI job worker')
    run_worker(app)


if __name__ == '__main__':
    main()
