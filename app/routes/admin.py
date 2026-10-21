from datetime import time
import hmac
import json
import os
import re

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app import db, validate_app_config
from app.models import UserConfig, UserSchedule, UserSubject
from app.user_subjects import (
    get_effective_config_for_user,
    get_effective_subjects_for_user,
    update_user_extra_config,
)

admin_bp = Blueprint('admin', __name__)


def _validate_schedule(blocks):
    if not isinstance(blocks, list) or len(blocks) > 12:
        return 'daily_blocks must be a list of at most 12 blocks'
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get('name'), str) or not block['name'].strip():
            return 'Every schedule block needs a name'
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


@admin_bp.route('/subjects', methods=['GET'])
@login_required
def get_subjects():
    return jsonify({'subjects': get_effective_subjects_for_user(current_user)})


@admin_bp.route('/subjects', methods=['POST'])
@login_required
def create_or_update_subject():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Subject must be a JSON object'}), 400
    subject_id = data.get('id') or data.get('subject_id') or ''
    if not isinstance(subject_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,49}', subject_id):
        return jsonify({'error': 'id must use lowercase letters, numbers, underscores, or hyphens'}), 400
    name = data.get('name', subject_id)
    icon = data.get('icon', '📚')
    description = data.get('description', '')
    color = data.get('color', '#6366f1')
    priority = data.get('priority', 1)
    topics = data.get('topics', [])
    if isinstance(topics, str):
        topics = [topic.strip() for topic in topics.split(',') if topic.strip()]
    if (
        not isinstance(name, str) or not name.strip() or len(name) > 100
        or not isinstance(icon, str) or len(icon) > 10
        or not isinstance(description, str) or len(description) > 1000
        or not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color)
        or not isinstance(priority, int) or isinstance(priority, bool)
        or not isinstance(topics, list) or len(topics) > 100
        or any(not isinstance(topic, str) or len(topic) > 200 for topic in topics)
    ):
        return jsonify({'error': 'Subject fields are invalid or exceed their length limits'}), 400

    subject = UserSubject.query.filter_by(user_id=current_user.id, subject_id=subject_id).first()
    if not subject:
        subject = UserSubject(user_id=current_user.id, subject_id=subject_id)
        db.session.add(subject)
    subject.name = name.strip()
    subject.icon = icon
    subject.description = description
    subject.color = color
    subject.priority = priority
    subject.topics = json.dumps(topics)
    preferences = UserConfig.query.filter_by(user_id=current_user.id).first()
    if preferences:
        extra = preferences.get_extra_config()
        extra['disabled_subject_ids'] = [
            item for item in extra.get('disabled_subject_ids', []) if item != subject_id
        ]
        preferences.extra_config = json.dumps(extra)
    db.session.commit()
    return jsonify({'status': 'success', 'subject': subject.to_dict()})


@admin_bp.route('/subjects/<subject_id>', methods=['DELETE'])
@login_required
def delete_subject(subject_id):
    subject = UserSubject.query.filter_by(user_id=current_user.id, subject_id=subject_id).first()
    is_shared_subject = any(
        item.get('id') == subject_id for item in current_app.config['APP_CONFIG'].get('subjects', [])
    )
    if not subject and not is_shared_subject:
        return jsonify({'error': 'Subject not found'}), 404
    if len(get_effective_subjects_for_user(current_user)) <= 1:
        return jsonify({'error': 'Keep at least one subject in your curriculum'}), 409
    if subject:
        db.session.delete(subject)
    preferences = UserConfig.query.filter_by(user_id=current_user.id).first()
    if is_shared_subject:
        extra = preferences.get_extra_config() if preferences else {}
        disabled = set(extra.get('disabled_subject_ids', []))
        disabled.add(subject_id)
        update_user_extra_config(current_user, disabled_subject_ids=sorted(disabled))
    db.session.commit()
    return jsonify({'status': 'success'})


@admin_bp.route('/schedule', methods=['GET'])
@login_required
def get_schedule():
    return jsonify({'daily_blocks': get_effective_config_for_user(current_user)['schedule']['daily_blocks']})


@admin_bp.route('/schedule', methods=['POST'])
@login_required
def update_schedule():
    data = request.get_json(silent=True)
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
    db.session.commit()
    return jsonify({'status': 'success', 'daily_blocks': blocks})


@admin_bp.route('/config', methods=['POST'])
@login_required
def update_config():
    admin_token = os.environ.get('ADMIN_API_TOKEN') or ''
    supplied_token = request.headers.get('X-Admin-Token', '')
    if not admin_token or not hmac.compare_digest(supplied_token, admin_token):
        return jsonify({'error': 'Administrator access required'}), 403
    data = request.get_json(silent=True)
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
