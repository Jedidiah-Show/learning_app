from flask import Blueprint, request, jsonify, current_app, redirect, url_for, session, flash
from flask_login import login_required, current_user
from app.user_subjects import (
    get_effective_config_for_user,
    get_effective_subjects_for_user,
    get_effective_schedule_for_user,
)
from app import db
from app.models import CalendarEvent
from app.learning import day_is_available, next_unlocked_day
from app.request_data import get_json_object
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import hashlib
import hmac
import json
import os

calendar_bp = Blueprint('calendar', __name__)
GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'


def _oauth_settings():
    app_config = current_app.config
    app_defaults = app_config.get('APP_CONFIG') or {}
    calendar_config = app_defaults.get('google_calendar') or {}
    client_id = (
        app_config.get('GOOGLE_CLIENT_ID')
        or os.environ.get('GOOGLE_CLIENT_ID')
        or app_defaults.get('google_client_id')
        or calendar_config.get('client_id')
    )
    client_secret = (
        app_config.get('GOOGLE_CLIENT_SECRET')
        or os.environ.get('GOOGLE_CLIENT_SECRET')
        or app_defaults.get('google_client_secret')
        or calendar_config.get('client_secret')
    )
    redirect_uri = (
        app_config.get('GOOGLE_REDIRECT_URI')
        or os.environ.get('GOOGLE_REDIRECT_URI')
        or app_defaults.get('google_redirect_uri')
        or calendar_config.get('redirect_uri')
        or url_for('calendar.google_callback', _external=True)
    )
    return client_id, client_secret, redirect_uri


def _parse_day_number(data, config):
    value = data.get('day_number', 1)
    if isinstance(value, bool):
        return None
    try:
        day_number = int(value)
    except (TypeError, ValueError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    if day_number < 1 or day_number > config['app']['curriculum_days']:
        return None
    return day_number


def _parse_timezone(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _calendar_service(user):
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    client_id, client_secret, _ = _oauth_settings()
    if not user.google_access_token:
        raise RuntimeError('Google Calendar is not connected')
    if not client_id or not client_secret:
        raise RuntimeError('Google Calendar credentials are not configured')
    expiry = user.token_expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    credentials = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=[GOOGLE_CALENDAR_SCOPE],
        expiry=expiry,
    )
    if credentials.expired:
        if not user.google_refresh_token:
            raise RuntimeError('Google authorization has expired; reconnect Google Calendar')
        credentials.refresh(GoogleRequest())
        user.google_access_token = credentials.token
        if credentials.expiry:
            user.token_expiry = credentials.expiry
    return build('calendar', 'v3', credentials=credentials)


def _google_event_body(event, user_id, calendar_config):
    if event.time_zone:
        zone = _parse_timezone(event.time_zone) or timezone.utc
        start_time = event.start_time.replace(tzinfo=timezone.utc).astimezone(zone)
        end_time = event.end_time.replace(tzinfo=timezone.utc).astimezone(zone)
    else:
        start_time = event.start_time.replace(tzinfo=timezone.utc).astimezone()
        end_time = event.end_time.replace(tzinfo=timezone.utc).astimezone()
    return {
        'id': event.event_id or hashlib.sha256(
            f'learning-app:{user_id}:{event.id}'.encode()
        ).hexdigest(),
        'summary': event.title,
        'description': event.description,
        'start': {'dateTime': start_time.isoformat()},
        'end': {'dateTime': end_time.isoformat()},
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': value}
                for value in calendar_config.get('reminder_minutes', [30])
            ],
        },
    }


def _delete_google_event(service, calendar_id, event_id):
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except Exception as error:
        if getattr(getattr(error, 'resp', None), 'status', None) != 404:
            raise


def delete_user_calendar_events(user):
    events = CalendarEvent.query.filter_by(
        user_id=user.id, synced_to_google=True,
    ).filter(CalendarEvent.event_id.isnot(None)).all()
    if not events:
        return
    service = _calendar_service(user)
    config = get_effective_config_for_user(user)
    calendar_id = (config.get('google_calendar') or {}).get('calendar_id', 'primary')
    for event in events:
        _delete_google_event(service, calendar_id, event.event_id)


def reconcile_calendar_schedule(user, blocks, force_update=False):
    config = get_effective_config_for_user(user)
    calendar_config = config.get('google_calendar') or {}
    block_by_name = {block['name']: block for block in blocks}
    events = CalendarEvent.query.filter_by(user_id=user.id).all()
    updates = []
    removals = []
    for event in events:
        if not event.block_name:
            continue
        block = block_by_name.get(event.block_name)
        if block is None:
            removals.append(event)
            continue
        zone = _parse_timezone(event.time_zone) or timezone.utc
        local_date = event.start_time.replace(tzinfo=timezone.utc).astimezone(zone).date()
        start_time = datetime.combine(
            local_date, time.fromisoformat(block['start_time']), tzinfo=zone
        )
        end_time = datetime.combine(
            local_date, time.fromisoformat(block['end_time']), tzinfo=zone
        )
        if end_time <= start_time:
            end_time += timedelta(days=1)
        start_utc = start_time.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_time.astimezone(timezone.utc).replace(tzinfo=None)
        title = (
            f"{calendar_config.get('event_prefix', '[Learning App]')} "
            f"{block['name'].title()} Session - Day {event.day_number}"
        )
        if force_update or (
            event.start_time != start_utc
            or event.end_time != end_utc
            or event.title != title
        ):
            event.start_time = start_utc
            event.end_time = end_utc
            event.title = title
            updates.append(event)

    remote_updates = [event for event in updates if event.synced_to_google]
    remote_removals = [
        event for event in removals
        if event.synced_to_google and event.event_id
    ]
    service = _calendar_service(user) if remote_updates or remote_removals else None
    calendar_id = calendar_config.get('calendar_id', 'primary')
    if service:
        for event in remote_updates:
            service.events().update(
                calendarId=calendar_id,
                eventId=event.event_id,
                body=_google_event_body(event, user.id, calendar_config),
            ).execute()
        for event in remote_removals:
            _delete_google_event(service, calendar_id, event.event_id)
    for event in removals:
        db.session.delete(event)
    return bool(updates or removals)


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
        return jsonify({'error': 'day_number must be an integer inside the curriculum'}), 400
    if not day_is_available(user, config, day_number):
        return jsonify({'error': 'Day is locked', 'next_unlocked_day': next_unlocked_day(user, config)}), 403

    zone = _parse_timezone(data.get('time_zone', 'UTC'))
    if zone is None:
        return jsonify({'error': 'time_zone must be a valid IANA timezone'}), 400
    subjects = get_effective_subjects_for_user(user)
    configured_start = config.get('schedule', {}).get('start_date')
    try:
        start_date = date.fromisoformat(configured_start) if configured_start else datetime.now(zone).date()
    except (TypeError, ValueError):
        return jsonify({'error': 'Configured schedule.start_date must be a valid ISO date'}), 400
    target_date = start_date + timedelta(days=day_number - 1)
    events_created = []
    for block in get_effective_schedule_for_user(user):
        start_time = datetime.combine(target_date, time.fromisoformat(block['start_time']), tzinfo=zone)
        end_time = datetime.combine(target_date, time.fromisoformat(block['end_time']), tzinfo=zone)
        if end_time <= start_time:
            end_time += timedelta(days=1)
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
        end_time = end_time.astimezone(timezone.utc).replace(tzinfo=None)
        title = f"{config['google_calendar']['event_prefix']} {block['name'].title()} Session - Day {day_number}"
        existing = CalendarEvent.query.filter_by(
            user_id=user.id,
            day_number=day_number,
            block_name=block['name'],
        ).first()
        if existing:
            continue
        event = CalendarEvent(
            user_id=user.id,
            title=title,
            description=f"Daily deep-dive study session. Subjects: {', '.join(subject['name'] for subject in subjects)}",
            start_time=start_time,
            end_time=end_time,
            subject_ids=json.dumps([subject['id'] for subject in subjects]),
            day_number=day_number,
            block_name=block['name'],
            time_zone=zone.key,
            synced_to_google=False
        )
        db.session.add(event)
        events_created.append({
            'block': block['name'],
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        })
    db.session.commit()
    return jsonify({
        'status': 'success',
        'events_created': events_created,
        'message': 'Study sessions scheduled (Google Calendar sync pending)'
    })

@calendar_bp.route('/events', methods=['GET'])
@login_required
def get_events():
    user = current_user
    events = CalendarEvent.query.filter_by(user_id=user.id).all()
    
    result = []
    for e in events:
        if e.time_zone:
            zone = _parse_timezone(e.time_zone) or timezone.utc
            start_time = e.start_time.replace(tzinfo=timezone.utc).astimezone(zone)
            end_time = e.end_time.replace(tzinfo=timezone.utc).astimezone(zone)
        else:
            start_time = e.start_time.astimezone()
            end_time = e.end_time.astimezone()
        result.append({
            'id': e.id,
            'event_id': e.event_id,
            'title': e.title,
            'description': e.description,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'synced_to_google': e.synced_to_google
        })
    
    return jsonify(result)


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
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=[GOOGLE_CALENDAR_SCOPE]
    )
    flow.redirect_uri = redirect_uri
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
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
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
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
        flow.fetch_token(code=code)
    except Exception:
        current_app.logger.exception('Google Calendar OAuth token exchange failed')
        flash('Google Calendar authorization failed. Check OAuth setup and try again.', 'error')
        return redirect(url_for('main.schedule'))
    credentials = flow.credentials
    user = current_user
    user.google_access_token = credentials.token
    if credentials.refresh_token:
        user.google_refresh_token = credentials.refresh_token
    if credentials.expiry:
        user.token_expiry = credentials.expiry
    db.session.commit()
    flash('Google Calendar connected successfully!', 'success')
    return redirect(url_for('main.schedule'))


@calendar_bp.route('/sync', methods=['POST'])
@login_required
def sync_to_google():
    user = current_user
    app_config = get_effective_config_for_user(user)
    if not app_config['google_calendar']['enabled']:
        return jsonify({'status': 'error', 'message': 'Google Calendar integration is disabled in your preferences'}), 403
    if not user.google_access_token:
        return jsonify({'status': 'error', 'message': 'Google Calendar not connected. Please authorize first.'}), 401
    
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Request body must be a JSON object'}), 400
    day_number = _parse_day_number(data, app_config)
    if day_number is None:
        return jsonify({'status': 'error', 'message': 'day_number must be an integer inside the curriculum'}), 400
    if not day_is_available(user, app_config, day_number):
        return jsonify({'status': 'error', 'message': 'Day is locked'}), 403
    gcal_cfg = app_config.get('google_calendar') or {}
    client_id = current_app.config.get('GOOGLE_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID') or gcal_cfg.get('client_id')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET') or os.environ.get('GOOGLE_CLIENT_SECRET') or gcal_cfg.get('client_secret')
    if not client_id or not client_secret:
        return jsonify({'status': 'error', 'message': 'Google Calendar credentials are not configured'}), 503
    local_events = CalendarEvent.query.filter_by(
        user_id=user.id,
        day_number=day_number,
        synced_to_google=False,
    ).order_by(CalendarEvent.start_time).all()
    if not local_events:
        already_synced = CalendarEvent.query.filter_by(
            user_id=user.id,
            day_number=day_number,
            synced_to_google=True,
        ).count()
        if already_synced:
            return jsonify({'status': 'success', 'events_created': 0, 'message': 'Study blocks are already synced'})
        return jsonify({'status': 'error', 'message': 'Schedule this day locally before syncing it'}), 409
    try:
        service = _calendar_service(user)
        event_ids = []
        for local_event in local_events:
            body = _google_event_body(local_event, user.id, gcal_cfg)
            calendar_id = gcal_cfg.get('calendar_id', 'primary')
            try:
                created_event = service.events().insert(
                    calendarId=calendar_id,
                    body=body,
                ).execute()
            except Exception as error:
                if getattr(getattr(error, 'resp', None), 'status', None) != 409:
                    raise
                created_event = service.events().get(
                    calendarId=calendar_id,
                    eventId=body['id'],
                ).execute()
            local_event.event_id = created_event['id']
            local_event.synced_to_google = True
            db.session.commit()
            event_ids.append(created_event['id'])
        return jsonify({'status': 'success', 'events_created': len(event_ids), 'message': 'Events synced to Google Calendar'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Google Calendar sync failed for user %s, day %s', user.id, day_number)
        return jsonify({'status': 'error', 'message': 'Google Calendar sync failed; check the connection and try again'}), 502
