"""Database-backed worker for durable Practice Arena submissions."""

import logging
import time
from datetime import timedelta

from app import db
from app.models import Submission, utcnow
from app.services.judge import execute_in_sandbox


logger = logging.getLogger(__name__)


def process_next_submission(app) -> bool:
    """Claim and execute one queued submission; return whether work was found."""
    with app.app_context():
        submission = (
            Submission.query
            .filter_by(verdict='PENDING')
            .order_by(Submission.submitted_at, Submission.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if submission is None:
            db.session.rollback()
            return False
        submission.verdict = 'RUNNING'
        submission.started_at = utcnow()
        submission_id = submission.id
        db.session.commit()

        submission = db.session.get(Submission, submission_id)
        from app.practice_arena import get_arena_problem
        problem = get_arena_problem(submission.problem_id)
        try:
            if problem is None:
                raise ValueError('Problem test suite is unavailable')
            result = execute_in_sandbox(
                submission.code_snapshot,
                problem['judge_tests'],
                timeout_sec=3.0,
            )
            submission.verdict = result.verdict
            submission.execution_time_ms = result.execution_time_ms
            submission.memory_kb = result.memory_kb
            submission.tests_passed = result.tests_passed
            submission.total_tests = result.total_tests
            submission.error_details = result.error_details
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
        return True


def run_worker(app, poll_seconds: float = 1.0) -> None:
    """Continuously process queued submissions until the worker is stopped."""
    with app.app_context():
        cutoff = utcnow() - timedelta(minutes=10)
        Submission.query.filter(
            Submission.verdict == 'RUNNING',
            Submission.started_at < cutoff,
        ).update({
            Submission.verdict: 'PENDING',
            Submission.started_at: None,
        })
        db.session.commit()
    while True:
        if not process_next_submission(app):
            time.sleep(poll_seconds)


def main() -> None:
    from app import create_app

    app = create_app()
    app.logger.info('Starting RUACH judge worker')
    run_worker(app)


if __name__ == '__main__':
    main()
