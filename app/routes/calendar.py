"""Routes for scheduling study sessions and syncing them with Google Calendar.

The routes only decide *what* should be in the learner's calendar.  All of
the Google API mechanics live in :mod:`app.google_calendar`.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import hmac
import json
import os

from flask import (
    Blueprint, current_app, flash, jsonify, redirect, request, session, url_for,
)
from flask_login import current_user, login_required

from app import db
from app import google_calendar as gcal
from app.learning import day_is_available, next_unlocked_day
from app.curriculum import all_lessons, all_modules, lesson_ordinal
from app.models import CalendarEvent
from app.request_data import get_json_object
from app.user_preferences import (
    get_effective_config_for_user,
    get_effective_schedule_for_user,
)

calendar_bp = Blueprint('calendar', __name__)
GOOGLE_CALENDAR_SCOPE = gcal.CALENDAR_SCOPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _oauth_settings():
    """Return the Google OAuth settings used by the connect flow."""
    return gcal.oauth_settings()


def _oauth_redirect_is_secure(uri):
    """Google accepts HTTPS, or plain HTTP only for a local callback."""
    if not isinstance(uri, str):
        return False
    return uri.startswith((
        'https://',
        'http://localhost',
        'http://127.0.0.1',
        'http://[::1]',
    ))


def _oauth_failure_message(error, redirect_uri):
    """Turn an OAuth token-exchange error into an actionable message."""
    message = str(error).lower()
    if not redirect_uri:
        return (
            'Google OAuth redirect URI could not be determined. Set '
            'GOOGLE_REDIRECT_URI to the HTTPS callback URL and try again.'
        )
    if 'redirect_uri_mismatch' in message:
        return (
            f'Google rejected the redirect URI. Add {redirect_uri} exactly '
            'to the OAuth client\u2019s Authorized redirect URIs, then try again.'
        )
    if 'invalid_client' in message or 'unauthorized_client' in message:
        return (
            'Google rejected the OAuth client. Check GOOGLE_CLIENT_ID and '
            'GOOGLE_CLIENT_SECRET in the deployment environment.'
        )
    if 'invalid_grant' in message:
        return (
            'The Google authorization code was invalid or expired. Start the '
            'connection again.'
        )
    if 'invalid_scope' in message:
        return (
            'Google rejected the requested Calendar scope. Enable the Google '
            'Calendar API and check the OAuth consent screen.'
        )
    if 'scope has changed' in message:
        return (
            'Google returned additional permissions that were previously '
            'granted to this app. Please try connecting Google Calendar again.'
        )
    return (
        'Google Calendar authorization failed. Check the OAuth client, '
        'redirect URI, and enabled APIs, then try again.'
    )


def _calendar_service(user):
    """Return a Google Calendar service for ``user``.

    The indirection keeps the Google client replaceable in tests.
    """
    return gcal.get_calendar_service(user)


def _user_connected(user):
    """Return True when the learner authorized the app at least once."""
    return bool(user.google_access_token or user.google_refresh_token)


def _parse_day_number(data, config):
    lesson_id = data.get('lesson_id')
    if isinstance(lesson_id, str):
        return lesson_ordinal(lesson_id)
    value = data.get('day_number', 1)
    if isinstance(value, bool):
        return None
    try:
        day_number = int(value)
    except (TypeError, ValueError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    if day_number < 1 or day_number > len(all_lessons()):
        return None
    return day_number


def _parse_timezone(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, KeyError, OSError):
        return None


def _requested_timezone(data):
    """Return the timezone of the request, preferring the browser's zone."""
    candidates = [
        data.get('time_zone'),
        request.headers.get('X-Timezone'),
    ]
    for candidate in candidates:
        zone = _parse_timezone(candidate)
        if zone is not None:
            return zone
    return timezone.utc


def _configured_start_date(config):
    """Return the configured course start date, or None when it is automatic."""
    configured = (config.get('schedule') or {}).get('start_date')
    if not configured:
        return None
    try:
        return date.fromisoformat(configured)
    except (TypeError, ValueError):
        return None


def _block_times(local_date, block, zone):
    """Return the naive UTC start and end of a study block on ``local_date``."""
    start = datetime.combine(
        local_date, time.fromisoformat(block['start_time']), tzinfo=zone
    )
    end = datetime.combine(
        local_date, time.fromisoformat(block['end_time']), tzinfo=zone
    )
    if end <= start:
        end += timedelta(days=1)
    return (
        start.astimezone(timezone.utc).replace(tzinfo=None),
        end.astimezone(timezone.utc).replace(tzinfo=None),
    )


class _DesiredState:
    """The values a calendar row should hold once it matches the schedule."""

    __slots__ = ('title', 'description', 'start_time', 'end_time', 'payload', 'hash')

    def __init__(self, title, description, start_time, end_time, payload, digest):
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.payload = payload
        self.hash = digest


class _DesiredEvent:
    """A minimal stand-in for a calendar row used to build Google payloads."""

    __slots__ = ('title', 'description', 'start_time', 'end_time', 'time_zone')

    def __init__(self, title, description, start_time, end_time, time_zone):
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.time_zone = time_zone


def _desired_state(event, block, calendar_config, subjects, start_date):
    """Return the state a calendar row should have for the current schedule."""
    zone = gcal.resolve_timezone(event.time_zone)
    if start_date is not None and event.day_number:
        local_date = start_date + timedelta(days=event.day_number - 1)
    else:
        local_date = gcal.stored_utc(event.start_time).astimezone(zone).date()
    start_time, end_time = _block_times(local_date, block, zone)
    lessons = all_lessons()
    lesson = lessons[event.day_number - 1] if event.day_number and event.day_number <= len(lessons) else None
    title = (f"{calendar_config['event_prefix']} {block['name'].title()} Session - "
             f"Lesson {event.day_number}")
    description = (
        f"Module {lesson['_module']['number']}: {lesson['_module']['title']} · {lesson['title']}"
        if lesson else 'RUACH Engineering Course study session'
    )
    desired = _DesiredEvent(
        title,
        description,
        start_time,
        end_time,
        event.time_zone or gcal.timezone_key(zone),
    )
    payload = gcal.event_payload(desired, calendar_config)
    return _DesiredState(
        title, description, start_time, end_time, payload, gcal.payload_hash(payload)
    )


class _CalendarPlan:
    """The set of changes needed to bring Google Calendar in line."""

    def __init__(self):
        self.operations = []
        self.changed = False
        self.inserted = 0
        self.updated = 0
        self.removed = 0

    @property
    def needs_remote(self):
        return bool(self.operations)


def _plan_removal(plan, event, calendar_config):
    """Schedule the removal of a study block that left the schedule."""
    if event.synced_to_google and event.event_id:
        if not event.delete_pending:
            event.delete_pending = True
            event.sync_pending = False
            plan.changed = True
        plan.operations.append({
            'kind': 'delete',
            'calendar_id': calendar_config['calendar_id'],
            'event_id': event.event_id,
            'event': event,
        })
        plan.removed += 1
        return
    # Nothing was pushed to Google, so the local row can simply go away.
    db.session.delete(event)
    plan.changed = True


def _plan_events(
    user,
    events,
    blocks,
    calendar_config,
    subjects,
    start_date=None,
    include_unsynced=False,
    force_update=False,
):
    """Work out which Google Calendar operations are required.

    The local rows are updated in place so pending work survives a failure,
    and the outstanding remote operations are recorded on the returned plan.
    """
    plan = _CalendarPlan()
    block_by_name = {block['name']: block for block in blocks}
    for event in events:
        if not event.block_name:
            # Events created before block tracking cannot be reconciled.
            continue
        block = block_by_name.get(event.block_name)
        if block is None:
            _plan_removal(plan, event, calendar_config)
            continue
        if event.delete_pending:
            # The block is back in the schedule, so the pending removal is
            # dropped and the event is pushed again instead of lost.
            event.delete_pending = False
            event.sync_pending = True
            plan.changed = True
        desired = _desired_state(
            event, block, calendar_config, subjects, start_date
        )
        if (
            event.title != desired.title
            or event.description != desired.description
            or event.start_time != desired.start_time
            or event.end_time != desired.end_time
        ):
            event.title = desired.title
            event.description = desired.description
            event.start_time = desired.start_time
            event.end_time = desired.end_time
            plan.changed = True
        lesson = all_lessons()[event.day_number - 1] if event.day_number and event.day_number <= len(all_lessons()) else None
        subject_ids = json.dumps([lesson['module_id']] if lesson else [])
        if event.subject_ids != subject_ids:
            event.subject_ids = subject_ids
            plan.changed = True
        if not event.synced_to_google or not event.event_id:
            if include_unsynced:
                plan.operations.append({
                    'kind': 'insert',
                    'calendar_id': calendar_config['calendar_id'],
                    'event_id': gcal.deterministic_event_id(
                        user.id, event.day_number, event.block_name
                    ),
                    'payload': desired.payload,
                    'hash': desired.hash,
                    'event': event,
                })
                event.sync_pending = True
                plan.inserted += 1
            continue
        if force_update or event.sync_pending or event.google_sync_hash != desired.hash:
            event.sync_pending = True
            plan.operations.append({
                'kind': 'update',
                'calendar_id': calendar_config['calendar_id'],
                'event_id': event.event_id,
                'payload': desired.payload,
                'hash': desired.hash,
                'event': event,
            })
            plan.updated += 1
    return plan


def _record_success(event, operation, result):
    """Store the outcome of a successful calendar operation."""
    if operation['kind'] == 'delete':
        db.session.delete(event)
        return
    if operation['kind'] == 'insert':
        response = result.response or {}
        event.event_id = response.get('id') or operation['event_id']
    event.synced_to_google = True
    event.sync_pending = False
    event.google_sync_hash = operation['hash']


def _recover_existing_event(service, operation):
    """Bring an event from a conflicting insert up to the desired state."""
    try:
        existing = gcal.fetch_event(
            service, operation['calendar_id'], operation['event_id']
        )
    except Exception:
        current_app.logger.warning(
            'Could not read the existing Google Calendar event %s',
            operation['event_id'],
            exc_info=True,
        )
        return False
    event = operation['event']
    event.event_id = (existing or {}).get('id') or operation['event_id']
    event.synced_to_google = True
    event.sync_pending = True
    event.google_sync_hash = None
    update = {
        'kind': 'update',
        'calendar_id': operation['calendar_id'],
        'event_id': event.event_id,
        'payload': operation['payload'],
        'hash': operation['hash'],
        'event': event,
    }
    result = gcal.apply_operations(service, [update])[0]
    if not result.ok:
        current_app.logger.warning(
            'Could not update the existing Google Calendar event %s: %s',
            event.event_id,
            result.error,
        )
        return False
    _record_success(event, update, result)
    return True


def _recreate_missing_event(service, operation):
    """Recreate a remote event that was removed outside the app.

    The original identifier is reused so the recreation replaces the event
    instead of adding a second one next to it.
    """
    insert = {
        'kind': 'insert',
        'calendar_id': operation['calendar_id'],
        'event_id': operation['event_id'],
        'payload': operation['payload'],
        'hash': operation['hash'],
        'event': operation['event'],
    }
    result = gcal.apply_operations(service, [insert])[0]
    if result.ok:
        _record_success(insert['event'], insert, result)
        return True
    if getattr(result.error, 'status', None) == 409:
        return _recover_existing_event(service, insert)
    current_app.logger.warning(
        'Could not recreate the Google Calendar event %s: %s',
        operation['event_id'],
        result.error,
    )
    return False


def _apply_plan(service, plan):
    """Run the planned operations and record the outcome on the local rows."""
    results = gcal.apply_operations(service, plan.operations)
    failures = []
    for operation, result in zip(plan.operations, results):
        event = operation['event']
        if result.ok:
            _record_success(event, operation, result)
            continue
        error = result.error
        status = getattr(error, 'status', None)
        if operation['kind'] == 'insert' and status == 409:
            if _recover_existing_event(service, operation):
                continue
        if operation['kind'] == 'delete' and status == 404:
            db.session.delete(event)
            continue
        if operation['kind'] == 'update' and status == 404:
            # The event was removed on Google's side, so put it back.
            if _recreate_missing_event(service, operation):
                continue
        event.sync_pending = True
        failures.append((operation, error))
    return failures


def _sync_events(user, events, config):
    """Push the given calendar rows to Google and return the plan."""
    calendar_config = gcal.calendar_settings(config)
    subjects = all_modules()
    blocks = get_effective_schedule_for_user(user)
    plan = _plan_events(
        user,
        events,
        blocks,
        calendar_config,
        subjects,
        _configured_start_date(config),
        include_unsynced=True,
    )
    # Store the plan before calling Google so unfinished work is retried later.
    db.session.commit()
    service = _calendar_service(user)
    failures = _apply_plan(service, plan)
    db.session.commit()
    return plan, failures

def _failure_message(failures):
    """Return an actionable, single-line summary of the failed operations."""
    if not failures:
        return 'Google Calendar sync failed.'
    first_error = failures[0][1]
    detail = getattr(first_error, 'user_message', None) or str(first_error)
    detail = ' '.join(detail.split())
    if len(failures) == 1:
        return f'Google Calendar sync failed: {detail}'
    return (
        f'{len(failures)} Google Calendar operation(s) failed. '
        f'First error: {detail}'
    )


def _run_sync(user, events, config):
    """Push calendar rows to Google and return a safe error payload.

    Returns ``(plan, failures, error, status_code)``.  ``error`` is a JSON
    payload when Google could not be reached at all; individual operation
    failures are returned in ``failures`` so they can be retried.
    """
    try:
        plan, failures = _sync_events(user, events, config)
    except gcal.GoogleAuthorizationError as error:
        current_app.logger.warning(
            'Google Calendar needs to be reconnected for user %s: %s',
            user.id,
            error,
        )
        return None, None, {
            'status': 'error',
            'code': 'reauthorize',
            'message': 'Google Calendar authorization expired. '
                       'Please reconnect Google Calendar.',
        }, 401
    except gcal.GoogleCalendarError as error:
        db.session.rollback()
        current_app.logger.exception(
            'Google Calendar sync failed for user %s: %s', user.id, error
        )
        return None, None, {
            'status': 'error',
            'code': 'calendar_error',
            'message': (
                getattr(error, 'user_message', None)
                or str(error)
                or 'Google Calendar sync failed; check the connection and try again'
            ),
        }, 502

    for operation, error in failures:
        current_app.logger.warning(
            'Google Calendar %s failed for user %s '
            '(status=%s, reason=%s): %s',
            operation.get('kind'),
            user.id,
            getattr(error, 'status', None),
            getattr(error, 'reason', None),
            error,
        )
    return plan, failures, None, None


# ---------------------------------------------------------------------------
# Account cleanup
# ---------------------------------------------------------------------------


def prepare_user_calendar_cleanup(user):
    """Return the service, calendar and event ids to remove for a learner."""
    events = CalendarEvent.query.filter_by(
        user_id=user.id, synced_to_google=True,
    ).filter(CalendarEvent.event_id.isnot(None)).all()
    if not events:
        return None
    service = _calendar_service(user)
    config = get_effective_config_for_user(user)
    calendar_id = (config.get('google_calendar') or {}).get('calendar_id', 'primary')
    return service, calendar_id, [event.event_id for event in events]


def perform_user_calendar_cleanup(cleanup, user_id):
    """Remove the learner's events from Google Calendar."""
    if cleanup is None:
        return True
    service, calendar_id, event_ids = cleanup
    operations = [
        {'kind': 'delete', 'calendar_id': calendar_id, 'event_id': event_id}
        for event_id in event_ids
    ]
    results = gcal.apply_operations(service, operations)
    complete = True
    for result in results:
        if result.ok:
            continue
        complete = False
        current_app.logger.error(
            'Could not delete a Google Calendar event for user %s: %s',
            user_id,
            result.error,
        )
    return complete


def delete_user_calendar_events(user):
    """Remove every synced event of a learner from Google Calendar."""
    try:
        cleanup = prepare_user_calendar_cleanup(user)
    except Exception:
        current_app.logger.exception(
            'Could not prepare Calendar cleanup for user %s', user.id
        )
        return
    return perform_user_calendar_cleanup(cleanup, user.id)


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


def reconcile_calendar_schedule(user, blocks, force_update=False):
    """Align the local schedule with Google Calendar.

    Returns True when the local calendar rows changed.  Remote work that
    could not be completed stays flagged on the rows so it is retried by the
    next sync instead of being lost.
    """
    config = get_effective_config_for_user(user)
    calendar_config = gcal.calendar_settings(config)
    subjects = all_modules()
    events = CalendarEvent.query.filter_by(
        user_id=user.id,
    ).order_by(CalendarEvent.start_time).all()
    plan = _plan_events(
        user,
        events,
        blocks,
        calendar_config,
        subjects,
        _configured_start_date(config),
        force_update=force_update,
    )
    # Store the plan first: if Google is unavailable the work is retried on
    # the next sync instead of being lost.
    db.session.commit()
    if not plan.needs_remote or not _user_connected(user):
        return plan.changed
    service = _calendar_service(user)
    failures = _apply_plan(service, plan)
    db.session.commit()
    if failures:
        raise gcal.GoogleCalendarError(_failure_message(failures))
    return plan.changed


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@calendar_bp.route('/schedule', methods=['POST'])
@login_required
def schedule_study_sessions():
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    user = current_user
    config = get_effective_config_for_user(user)
    day_number = _parse_day_number(data, config)
    if day_number is None:
        return jsonify({'error': 'lesson_id must identify a course lesson'}), 400
    if not day_is_available(user, config, day_number):
        return jsonify({'error': 'Day is locked', 'next_unlocked_day': next_unlocked_day(user, config)}), 403

    zone = _requested_timezone(data)
    subjects = all_modules()
    blocks = get_effective_schedule_for_user(user)
    calendar_config = gcal.calendar_settings(config)
    start_date = _configured_start_date(config) or datetime.now(zone).date()
    target_date = start_date + timedelta(days=day_number - 1)

    events = CalendarEvent.query.filter_by(
        user_id=user.id, day_number=day_number,
    ).order_by(CalendarEvent.start_time).all()
    existing = {event.block_name: event for event in events}

    events_created = []
    for block in blocks:
        if block['name'] in existing:
            continue
        start_time, end_time = _block_times(target_date, block, zone)
        event = CalendarEvent(
            user_id=user.id,
            title=(
                f"{calendar_config['event_prefix']} "
                f"{block['name'].title()} Session - Lesson {day_number}"
            ),
            description=(
                (f"Module {all_lessons()[day_number - 1]['_module']['number']}: "
                 f"{all_lessons()[day_number - 1]['_module']['title']} · "
                 f"{all_lessons()[day_number - 1]['title']}")
            ),
            start_time=start_time,
            end_time=end_time,
            subject_ids=json.dumps([all_lessons()[day_number - 1]['module_id']]),
            day_number=day_number,
            block_name=block['name'],
            time_zone=gcal.timezone_key(zone),
            synced_to_google=False,
        )
        db.session.add(event)
        existing[block['name']] = event
        events_created.append({
            'block': block['name'],
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
        })
    db.session.commit()

    # Keep the stored rows aligned with the current schedule so a later sync
    # pushes the right times.
    _plan_events(
        user,
        list(existing.values()),
        blocks,
        calendar_config,
        subjects,
        _configured_start_date(config),
    )
    db.session.commit()

    sync_state = None
    if calendar_config['enabled'] and _user_connected(user):
        try:
            synced_plan, failures, error, _ = _run_sync(
                user, list(existing.values()), config
            )
        except Exception:
            current_app.logger.exception(
                'Unexpected Calendar sync failure for user %s', user.id
            )
            sync_state = {
                'status': 'error',
                'message': (
                    'Study sessions were saved locally, but Google Calendar '
                    'sync failed unexpectedly. Retry from Settings.'
                ),
            }
        else:
            if error:
                sync_state = {
                    'status': 'error',
                    'message': error['message'],
                }
            elif failures:
                sync_state = {
                    'status': 'partial',
                    'message': _failure_message(failures),
                }
            else:
                sync_state = {
                    'status': 'success',
                    'events_created': synced_plan.inserted,
                    'events_updated': synced_plan.updated,
                    'events_removed': synced_plan.removed,
                    'message': (
                        'Study sessions scheduled and synced to Google Calendar.'
                    ),
                }

    pending = sum(
        1 for event in CalendarEvent.query.filter_by(
            user_id=user.id, day_number=day_number,
        ).all()
        if not event.synced_to_google or event.sync_pending or event.delete_pending
    )
    response = {
        'status': 'success',
        'events_created': events_created,
        'pending_sync': pending,
        'message': (
            sync_state['message'] if sync_state
            else 'Study sessions scheduled (Google Calendar sync pending)'
        ),
    }
    if sync_state:
        response['sync'] = sync_state
    return jsonify(response)


@calendar_bp.route('/events', methods=['GET'])
@login_required
def get_events():
    user = current_user
    events = CalendarEvent.query.filter_by(
        user_id=user.id,
    ).order_by(CalendarEvent.start_time).all()

    result = []
    for event in events:
        zone = gcal.resolve_timezone(event.time_zone)
        start_time = gcal.stored_utc(event.start_time).astimezone(zone)
        end_time = gcal.stored_utc(event.end_time).astimezone(zone)
        result.append({
            'id': event.id,
            'event_id': event.event_id,
            'title': event.title,
            'description': event.description,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'day_number': event.day_number,
            'block_name': event.block_name,
            'time_zone': event.time_zone,
            'synced_to_google': event.synced_to_google,
            'sync_pending': event.sync_pending,
            'delete_pending': event.delete_pending,
        })

    return jsonify(result)


@calendar_bp.route('/status', methods=['GET'])
@login_required
def calendar_status():
    user = current_user
    config = get_effective_config_for_user(user)
    calendar_config = gcal.calendar_settings(config)
    client_id, client_secret, _ = gcal.oauth_settings()
    counts = {
        'total': 0,
        'synced': 0,
        'pending': 0,
    }
    pending_days = set()
    for event in CalendarEvent.query.filter_by(user_id=user.id).all():
        counts['total'] += 1
        if event.delete_pending:
            # The removal itself still has to reach Google.
            counts['pending'] += 1
            if event.day_number:
                pending_days.add(event.day_number)
        elif event.synced_to_google and not event.sync_pending:
            counts['synced'] += 1
        else:
            counts['pending'] += 1
            if event.day_number:
                pending_days.add(event.day_number)
    return jsonify({
        'enabled': calendar_config['enabled'],
        'connected': _user_connected(user),
        'oauth_configured': bool(client_id and client_secret),
        'calendar_id': calendar_config['calendar_id'],
        'events_total': counts['total'],
        'events_synced': counts['synced'],
        'events_pending': counts['pending'],
        'pending_days': sorted(pending_days),
    })


@calendar_bp.route('/sync', methods=['POST'])
@login_required
def sync_to_google():
    user = current_user
    app_config = get_effective_config_for_user(user)
    if not app_config['google_calendar']['enabled']:
        return jsonify({'status': 'error', 'message': 'Google Calendar integration is disabled in your preferences'}), 403
    if not _user_connected(user):
        return jsonify({'status': 'error', 'message': 'Google Calendar not connected. Please authorize first.'}), 401

    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Request body must be a JSON object'}), 400
    day_number = _parse_day_number(data, app_config)
    if day_number is None:
        return jsonify({'status': 'error', 'message': 'lesson_id must identify a course lesson'}), 400
    if not day_is_available(user, app_config, day_number):
        return jsonify({'status': 'error', 'message': 'Day is locked'}), 403

    events = CalendarEvent.query.filter_by(
        user_id=user.id, day_number=day_number,
    ).order_by(CalendarEvent.start_time).all()
    if not events:
        return jsonify({'status': 'error', 'message': 'Schedule this day locally before syncing it'}), 409

    plan, failures, error, status_code = _run_sync(user, events, app_config)
    if error:
        return jsonify(error), status_code
    if failures:
        return jsonify({
            'status': 'error',
            'message': _failure_message(failures),
            'events_created': plan.inserted - len(
                [item for item in failures if item[0]['kind'] == 'insert']
            ),
            'events_updated': plan.updated - len(
                [item for item in failures if item[0]['kind'] == 'update']
            ),
        }), 502
    return jsonify({
        'status': 'success',
        'events_created': plan.inserted,
        'events_updated': plan.updated,
        'events_removed': plan.removed,
        'message': 'Events synced to Google Calendar',
    })


@calendar_bp.route('/sync-all', methods=['POST'])
@login_required
def sync_all_to_google():
    """Sync every locally scheduled day with Google Calendar."""
    user = current_user
    app_config = get_effective_config_for_user(user)
    if not app_config['google_calendar']['enabled']:
        return jsonify({'status': 'error', 'message': 'Google Calendar integration is disabled in your preferences'}), 403
    if not _user_connected(user):
        return jsonify({'status': 'error', 'message': 'Google Calendar not connected. Please authorize first.'}), 401

    events = CalendarEvent.query.filter_by(
        user_id=user.id,
    ).order_by(CalendarEvent.start_time).all()
    if not events:
        return jsonify({'status': 'success', 'events_created': 0, 'events_updated': 0,
                        'message': 'Nothing is scheduled locally yet'})

    plan, failures, error, status_code = _run_sync(user, events, app_config)
    if error:
        return jsonify(error), status_code
    if failures:
        return jsonify({
            'status': 'error',
            'message': _failure_message(failures),
            'events_created': plan.inserted - len(
                [item for item in failures if item[0]['kind'] == 'insert']
            ),
            'events_updated': plan.updated - len(
                [item for item in failures if item[0]['kind'] == 'update']
            ),
        }), 502
    return jsonify({
        'status': 'success',
        'events_created': plan.inserted,
        'events_updated': plan.updated,
        'events_removed': plan.removed,
        'message': 'Scheduled study blocks synced to Google Calendar',
    })


@calendar_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect_google():
    """Revoke and forget the stored Google authorization for this learner."""
    user = current_user
    revoked = gcal.revoke_authorization(user)
    user.google_access_token = None
    user.google_refresh_token = None
    user.token_expiry = None
    db.session.commit()
    flash('Google Calendar has been disconnected.', 'info')
    return jsonify({'status': 'success', 'google_revoked': revoked})


@calendar_bp.route('/auth/google')
@login_required
def google_auth():
    from google_auth_oauthlib.flow import Flow
    if not get_effective_config_for_user(current_user)['google_calendar']['enabled']:
        flash('Google Calendar integration is disabled in your preferences.', 'info')
        return redirect(url_for('main.schedule'))
    client_id, client_secret, redirect_uri = _oauth_settings()
    if not client_id or not client_secret:
        flash(
            'Google Calendar is not configured. Set GOOGLE_CLIENT_ID and '
            'GOOGLE_CLIENT_SECRET, plus GOOGLE_REDIRECT_URI when the app URL '
            'differs from its callback URL.',
            'error',
        )
        return redirect(url_for('main.schedule'))
    if not redirect_uri:
        flash(
            'Google OAuth redirect URI could not be determined. Set '
            'GOOGLE_REDIRECT_URI to the HTTPS callback URL and try again.',
            'error',
        )
        return redirect(url_for('main.schedule'))
    if not _oauth_redirect_is_secure(redirect_uri):
        flash(
            'Google OAuth requires an HTTPS callback. Set '
            'GOOGLE_REDIRECT_URI to the HTTPS URL for '
            '/api/calendar/oauth2callback and try again.',
            'error',
        )
        return redirect(url_for('main.schedule'))
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": gcal.GOOGLE_AUTHORIZATION_URI,
                "token_uri": gcal.GOOGLE_TOKEN_URI,
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=[GOOGLE_CALENDAR_SCOPE]
    )
    flow.redirect_uri = redirect_uri
    # A refresh token is only issued when the learner is asked to consent
    # again, so the prompt is only forced when one is actually missing.
    # Calendar only needs calendar.events. Do not request previously granted
    # scopes here; the app-owned Gmail scope is not part of the learner token.
    request_options = {
        'access_type': 'offline',
    }
    if not current_user.google_refresh_token:
        request_options['prompt'] = 'consent'
    authorization_url, state = flow.authorization_url(**request_options)
    session['state'] = state
    return redirect(authorization_url)


@calendar_bp.route('/oauth2callback')
@login_required
def google_callback():
    from google_auth_oauthlib.flow import Flow
    client_id, client_secret, redirect_uri = _oauth_settings()
    if not client_id or not client_secret:
        flash(
            'Google Calendar is not configured. Set GOOGLE_CLIENT_ID and '
            'GOOGLE_CLIENT_SECRET before connecting.',
            'error',
        )
        return redirect(url_for('main.schedule'))
    if request.args.get('error'):
        session.pop('state', None)
        flash('Google Calendar authorization was cancelled or denied.', 'error')
        return redirect(url_for('main.schedule'))
    state = session.pop('state', None)
    returned_state = request.args.get('state', '')
    if not state or not returned_state or not hmac.compare_digest(state, returned_state):
        flash('Google OAuth state validation failed. Please try connecting again.', 'error')
        return redirect(url_for('main.schedule'))
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": gcal.GOOGLE_AUTHORIZATION_URI,
                "token_uri": gcal.GOOGLE_TOKEN_URI,
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=[GOOGLE_CALENDAR_SCOPE],
        state=state
    )
    flow.redirect_uri = redirect_uri
    try:
        code = request.args.get('code')
        if not code:
            raise ValueError('Google OAuth callback did not include an authorization code')
        # Google can return scopes that were previously granted to this OAuth
        # client even when only calendar.events was requested. oauthlib treats
        # that superset as an error unless scope validation is relaxed. The
        # token is still valid, and this app only uses calendar.events here.
        previous_relax = os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE')
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        try:
            flow.fetch_token(code=code)
        finally:
            if previous_relax is None:
                os.environ.pop('OAUTHLIB_RELAX_TOKEN_SCOPE', None)
            else:
                os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = previous_relax
    except Exception as error:
        current_app.logger.exception('Google Calendar OAuth token exchange failed')
        flash(_oauth_failure_message(error, redirect_uri), 'error')
        return redirect(url_for('main.schedule'))
    credentials = flow.credentials
    user = current_user
    user.google_access_token = credentials.token
    if credentials.refresh_token:
        user.google_refresh_token = credentials.refresh_token
    if credentials.expiry:
        user.token_expiry = gcal.naive_utc(credentials.expiry)
    db.session.commit()
    flash('Google Calendar connected successfully!', 'success')
    return redirect(url_for('main.schedule'))
