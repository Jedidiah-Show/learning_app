from datetime import time
import hmac
import json
import os

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app import db, validate_app_config
from app.google_calendar import GoogleAuthorizationError
from app.models import CalendarEvent, UserSchedule
from app.user_preferences import get_effective_config_for_user
from app.request_data import get_json_object

admin_bp = Blueprint('admin', __name__)


def _validate_schedule(blocks):
    if not isinstance(blocks, list) or len(blocks) > 12:
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
            if len(str(block.get(field, ''))) > 120:
                return f'Schedule block {field} must be 120 characters or fewer'
    return None


@admin_bp.route('/config', methods=['GET'])
@login_required
def get_config():
    return jsonify(get_effective_config_for_user(current_user))


@admin_bp.route('/schedule', methods=['GET'])
@login_required
def get_schedule():
    return jsonify({'daily_blocks': get_effective_config_for_user(current_user)['schedule']['daily_blocks']})


@admin_bp.route('/schedule', methods=['POST'])
@login_required
def update_schedule():
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Schedule must be a JSON object'}), 400
    blocks = data.get('daily_blocks')
    error = _validate_schedule(blocks)
    if error:
        return jsonify({'error': error}), 400
    schedule = UserSchedule.query.filter_by(user_id=current_user.id).first()
    if not schedule:
        schedule = UserSchedule(user_id=current_user.id)
        db.session.add(schedule)
    schedule.daily_blocks = json.dumps(blocks)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            'Could not save schedule for user %s', current_user.id
        )
        return jsonify({'error': 'Could not save schedule'}), 500
    try:
        from app.routes.calendar import reconcile_calendar_schedule
        reconcile_calendar_schedule(current_user, blocks)
    except GoogleAuthorizationError:
        db.session.rollback()
        current_app.logger.warning(
            'Google Calendar needs to be reconnected for user %s', current_user.id
        )
        return jsonify({
            'error': 'Schedule saved, but Google Calendar needs to be reconnected.'
        }), 401
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            'Could not reconcile calendar events for user %s', current_user.id
        )
        return jsonify({
            'error': 'Schedule saved, but Calendar sync is incomplete. Retry to finish syncing.'
        }), 502
    return jsonify({'status': 'success', 'daily_blocks': blocks})


@admin_bp.route('/config', methods=['POST'])
@login_required
def update_config():
    admin_token = os.environ.get('ADMIN_API_TOKEN') or ''
    supplied_token = request.headers.get('X-Admin-Token', '')
    if not admin_token or not hmac.compare_digest(supplied_token, admin_token):
        return jsonify({'error': 'Administrator access required'}), 403
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Configuration must be a JSON object'}), 400
    config = dict(current_app.config['APP_CONFIG'])
    config.update(data)
    try:
        validate_app_config(config)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    current_app.config['APP_CONFIG'] = config
    return jsonify({'status': 'success', 'message': 'Configuration updated'})
