"""Durable, database-backed background work for lesson preparation."""

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

import click
from flask_login import login_user, logout_user

from app import db
from app.models import AIBackgroundJob, User


def enqueue_lesson_preparation(user, day_number, config, subjects):
    source = json.dumps({
        'user_id': user.id,
        'day_number': day_number,
        'subjects': subjects,
        'ai': config.get('ai', {}),
        'learning': config.get('learning', {}),
        'lesson_generation': config.get('lesson_generation', {}),
    }, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(source.encode('utf-8')).hexdigest()[:32]
    job_key = f'lesson-day-{user.id}-{day_number}-{digest}'
    job = AIBackgroundJob.query.filter_by(job_key=job_key).first()
    if job is None:
        job = AIBackgroundJob(
            job_key=job_key,
            job_type='prepare_lesson_day',
            user_id=user.id,
            payload=json.dumps({'day_number': day_number}),
            status='queued',
            attempts=0,
            available_at=datetime.now(timezone.utc),
        )
        db.session.add(job)
    elif job.status == 'failed':
        job.status = 'queued'
        job.attempts = 0
        job.last_error = None
        job.locked_at = None
        job.available_at = datetime.now(timezone.utc)
    db.session.commit()
    return job


def _aware(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def process_one_ai_job(app):
    """Claim and process one due job. Safe for multiple worker processes."""
    now = datetime.now(timezone.utc)
    with app.app_context():
        stale_before = now - timedelta(minutes=20)
        stale_jobs = AIBackgroundJob.query.filter(
            AIBackgroundJob.status == 'running',
            AIBackgroundJob.locked_at < stale_before,
        ).all()
        for stale in stale_jobs:
            stale.status = 'queued'
            stale.locked_at = None
            stale.available_at = now
        if stale_jobs:
            db.session.commit()

        job = AIBackgroundJob.query.filter(
            AIBackgroundJob.status == 'queued',
            AIBackgroundJob.available_at <= now,
        ).order_by(AIBackgroundJob.created_at, AIBackgroundJob.id).first()
        if job is None:
            return False
        job_id = job.id
        claimed = AIBackgroundJob.query.filter_by(
            id=job_id, status='queued'
        ).update({
            'status': 'running',
            'attempts': AIBackgroundJob.attempts + 1,
            'locked_at': now,
            'updated_at': now,
        }, synchronize_session=False)
        if not claimed:
            db.session.rollback()
            return False
        db.session.commit()

        try:
            payload = json.loads(job.payload)
            user = db.session.get(User, job.user_id)
            if user is None:
                job.status = 'cancelled'
                job.locked_at = None
                db.session.commit()
                return True
            if job.job_type != 'prepare_lesson_day':
                raise ValueError(f'Unsupported AI job type: {job.job_type}')

            from app.routes.lessons import prepare_lesson_day
            from app.user_subjects import (
                get_effective_config_for_user,
                get_effective_subjects_for_user,
            )

            # A request context gives Gemini's usage limiter the correct user.
            with app.test_request_context('/_worker/ai-jobs'):
                login_user(user, force=True)
                config = get_effective_config_for_user(user)
                prepare_lesson_day(
                    user,
                    int(payload['day_number']),
                    config,
                    get_effective_subjects_for_user(user),
                )
                logout_user()

            job = db.session.get(AIBackgroundJob, job_id)
            job.status = 'complete'
            job.locked_at = None
            job.last_error = None
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            job = db.session.get(AIBackgroundJob, job_id)
            if job is None:
                return True
            job.locked_at = None
            job.last_error = str(error)[:1000]
            if job.attempts >= 4:
                job.status = 'failed'
            else:
                job.status = 'queued'
                job.available_at = now + timedelta(seconds=min(300, 15 * 2 ** (job.attempts - 1)))
            db.session.commit()
            app.logger.exception('AI background job %s failed', job_id)
        return True


def register_ai_job_cli(app):
    @app.cli.command('process-ai-jobs')
    @click.option('--once', 'run_once', is_flag=True, help='Process at most one due job.')
    @click.option('--poll-seconds', default=5, show_default=True, type=click.IntRange(1, 60))
    def process_ai_jobs(run_once, poll_seconds):
        """Run the durable lesson preparation queue."""
        click.echo('AI job worker started.')
        while True:
            processed = process_one_ai_job(app)
            if run_once:
                if not processed:
                    click.echo('No due AI jobs.')
                break
            if not processed:
                time.sleep(poll_seconds)

