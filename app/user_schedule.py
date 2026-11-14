"""Per-learner study schedule helpers.

The schedule is learner-scoped data, not an administrator setting, so the
endpoints that read and write it live under ``/api/settings``. This module
holds the validation and persistence logic so both the HTTP routes and the
calendar reconciliation share one implementation.
"""

from datetime import time
import json

from flask import current_app

from app import db
from app.google_calendar import GoogleAuthorizationError, GoogleCalendarError
from app.models import UserSchedule
from app.user_preferences import get_effective_config_for_user


MAX_SCHEDULE_BLOCKS = 12
MAX_BLOCK_FIELD_LENGTH = 120


def validate_schedule(blocks):
    """Return an error message when the daily blocks are invalid."""
    if not isinstance(blocks, list) or len(blocks) > MAX_SCHEDULE_BLOCKS:
        return 'daily_blocks must be a list of at most 12 blocks'
    names = set()
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get('name'), str) or not block['name'].strip():
            return 'Every schedule block needs a name'
        if block['name'] in names:
            return 'Schedule block names must be unique'
        names.add(block['name'])
        try:
            start = time.fromisoformat(block['start_time'])
            end = time.fromisoformat(block['end_time'])
        except (KeyError, TypeError, ValueError):
            return 'Every schedule block needs valid start_time and end_time values'
        if start == end:
            return 'Schedule block start and end times must differ'
        for field in ('name', 'description'):
            if len(str(block.get(field, ''))) > MAX_BLOCK_FIELD_LENGTH:
                return f'Schedule block {field} must be 120 characters or fewer'
    return None


def get_schedule_blocks(user):
    """Return the learner's effective daily blocks."""
    return get_effective_config_for_user(user)['schedule']['daily_blocks']


def save_schedule_blocks(user, blocks):
    """Persist the learner's daily blocks.

    Returns ``(error, status_code)``. On success the calendar is reconciled so
    Google Calendar stays in step with the new schedule.
    """
    schedule = UserSchedule.query.filter_by(user_id=user.id).first()
    if not schedule:
        schedule = UserSchedule(user_id=user.id)
        db.session.add(schedule)
    schedule.daily_blocks = json.dumps(blocks)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            'Could not save schedule for user %s', user.id
        )
        return 'Could not save schedule', 500
    try:
        from app.routes.calendar import reconcile_calendar_schedule
        reconcile_calendar_schedule(user, blocks)
    except GoogleAuthorizationError:
        db.session.rollback()
        current_app.logger.warning(
            'Google Calendar needs to be reconnected for user %s', user.id
        )
        return (
            'Schedule saved, but Google Calendar needs to be reconnected.',
            401,
        )
    except GoogleCalendarError as error:
        db.session.rollback()
        current_app.logger.warning(
            'Calendar reconciliation failed for user %s: %s', user.id, error,
        )
        return f'Schedule saved, but {error}', 502
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            'Could not reconcile calendar events for user %s', user.id
        )
        return (
            'Schedule saved, but Calendar sync is incomplete. '
            'Retry to finish syncing.',
            502,
        )
    return None, 200
