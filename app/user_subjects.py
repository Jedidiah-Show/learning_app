"""Resolve the shared curriculum and account-specific learning preferences."""

from copy import deepcopy

from flask import current_app
from flask_login import current_user

from app.models import UserSchedule, UserSubject, UserConfig, UserSubjectConfig


def _user_config(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return UserConfig.query.filter_by(user_id=user.id).first()


def get_effective_subjects_for_user(user=None):
    if user is None:
        user = current_user
    config = current_app.config.get('APP_CONFIG', {}) or {}
    user_config = _user_config(user)
    extra = user_config.get_extra_config() if user_config else {}
    disabled_ids = {
        item for item in extra.get('disabled_subject_ids', [])
        if isinstance(item, str)
    } if isinstance(extra.get('disabled_subject_ids', []), list) else set()

    custom = UserSubject.query.filter_by(user_id=user.id).all() if getattr(user, 'is_authenticated', False) else []
    subjects_by_id = {subject.subject_id: subject.to_dict() for subject in custom}
    for subject in config.get('subjects', []) or []:
        if subject.get('id') not in subjects_by_id and subject.get('id') not in disabled_ids:
            subjects_by_id[subject['id']] = deepcopy(subject)
    if getattr(user, 'is_authenticated', False):
        subject_configs = {
            item.subject_id: item
            for item in UserSubjectConfig.query.filter_by(user_id=user.id).all()
        }
        for subject in subjects_by_id.values():
            subject_config = subject_configs.get(subject['id'])
            stated = subject_config.proficiency if subject_config else 'Novice'
            subject['stated_proficiency'] = stated
            subject['proficiency'] = (
                subject_config.acquired_proficiency
                if subject_config and subject_config.tested and subject_config.acquired_proficiency
                else stated
            )
    return sorted(subjects_by_id.values(), key=lambda subject: subject.get('priority', 999))


def get_effective_schedule_for_user(user=None):
    if user is None:
        user = current_user
    if getattr(user, 'is_authenticated', False):
        schedule = UserSchedule.query.filter_by(user_id=user.id).first()
        if schedule:
            blocks = schedule.get_daily_blocks()
            if blocks is not None:
                return blocks
    config = current_app.config.get('APP_CONFIG', {}) or {}
    return deepcopy((config.get('schedule') or {}).get('daily_blocks', []))


def get_effective_config_for_user(user=None):
    if user is None:
        user = current_user
    config = deepcopy(current_app.config.get('APP_CONFIG', {}) or {})
    user_config = _user_config(user)
    extra = user_config.get_extra_config() if user_config else {}
    preferences = extra.get('preferences', {})
    if isinstance(preferences, dict):
        for section in (
            'ai', 'learning', 'proficiency_assessment', 'quizzes',
            'lesson_generation', 'progress', 'google_calendar',
        ):
            overrides = preferences.get(section)
            if isinstance(overrides, dict):
                config.setdefault(section, {}).update(deepcopy(overrides))
        schedule_preferences = preferences.get('schedule', {})
        if isinstance(schedule_preferences, dict):
            config.setdefault('schedule', {}).update(deepcopy(schedule_preferences))
    config['subjects'] = get_effective_subjects_for_user(user)
    config.setdefault('schedule', {})['daily_blocks'] = get_effective_schedule_for_user(user)
    if user_config and user_config.assessment_date:
        config.setdefault('app', {})['assessment_date'] = user_config.assessment_date
    for key in ('google_client_secret', 'GOOGLE_CLIENT_SECRET'):
        config.pop(key, None)
    calendar_config = config.get('google_calendar') or {}
    calendar_config.pop('client_secret', None)
    return config


def update_user_extra_config(user, **updates):
    config = _user_config(user)
    if config is None:
        config = UserConfig(user_id=user.id)
        from app import db
        db.session.add(config)
    extra = config.get_extra_config()
    extra.update(updates)
    import json
    config.extra_config = json.dumps(extra)
    return config


def get_user_preferences(user):
    user_config = _user_config(user)
    extra = user_config.get_extra_config() if user_config else {}
    preferences = extra.get('preferences', {})
    return preferences if isinstance(preferences, dict) else {}


def set_user_preferences(user, preferences):
    config = _user_config(user)
    if config is None:
        config = UserConfig(user_id=user.id)
        from app import db
        db.session.add(config)
    extra = config.get_extra_config()
    extra['preferences'] = preferences
    import json
    config.extra_config = json.dumps(extra)
    return config
