"""Shared learner-specific lesson state helpers."""

from datetime import datetime, timezone
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import has_request_context, request

from app.course_data import SETUP_CHECKS
from app.models import CoursePlan


def learner_today(timezone_name=None):
    """Return today's date in the learner timezone supplied by the browser."""
    if timezone_name is None and has_request_context():
        timezone_name = request.headers.get('X-Timezone')
    name = (timezone_name or '').strip()
    zone = timezone.utc
    if name:
        try:
            zone = ZoneInfo(name)
        except (ValueError, ZoneInfoNotFoundError):
            pass
    return datetime.now(zone).date()


def setup_checks_for_plan(plan):
    stored = {}
    if plan and plan.setup_checks:
        try:
            decoded = json.loads(plan.setup_checks)
        except (TypeError, ValueError):
            decoded = None
        if isinstance(decoded, dict):
            stored = {
                check['id']: bool(decoded.get(check['id']))
                for check in SETUP_CHECKS
            }
    return {check['id']: bool(stored.get(check['id'])) for check in SETUP_CHECKS}


def stored_setup_checks(user):
    """Return per-check guided-start ticks from the learner's saved plan."""
    plan = CoursePlan.query.filter_by(user_id=user.id).first()
    return setup_checks_for_plan(plan)
