"""Account-specific schedule and preferences for the RuachAI engineering course."""

from copy import deepcopy
import json

from flask import current_app

from app import merge_config
from app.models import UserConfig, UserSchedule


def _user_config(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return UserConfig.query.filter_by(user_id=user.id).first()


def get_effective_schedule_for_user(user):
    if user and getattr(user, 'is_authenticated', False):
        schedule = UserSchedule.query.filter_by(user_id=user.id).first()
        if schedule:
            blocks = schedule.get_daily_blocks()
            if blocks is not None:
                return blocks
    config = current_app.config.get('APP_CONFIG', {}) or {}
    return deepcopy((config.get('schedule') or {}).get('daily_blocks', []))


def get_effective_config_for_user(user=None):
    config = deepcopy(current_app.config.get('APP_CONFIG', {}) or {})
    user_config = _user_config(user)
    extra = user_config.get_extra_config() if user_config else {}
    preferences = extra.get('preferences', {})
    if isinstance(preferences, dict):
        for section in ('ai', 'progress', 'google_calendar'):
            overrides = preferences.get(section)
            if isinstance(overrides, dict):
                config[section] = merge_config(config.get(section, {}), overrides)
    config.setdefault('schedule', {})['daily_blocks'] = get_effective_schedule_for_user(user)
    for key in ('google_client_secret', 'GOOGLE_CLIENT_SECRET'):
        config.pop(key, None)
    calendar_config = config.get('google_calendar') or {}
    calendar_config.pop('client_secret', None)
    return config


def get_user_preferences(user):
    user_config = _user_config(user)
    extra = user_config.get_extra_config() if user_config else {}
    preferences = extra.get('preferences', {})
    return preferences if isinstance(preferences, dict) else {}


def set_user_preferences(user, preferences):
    from app import db
    config = _user_config(user)
    if config is None:
        config = UserConfig(user_id=user.id)
        db.session.add(config)
    extra = config.get_extra_config()
    extra['preferences'] = preferences
    config.extra_config = json.dumps(extra)
    return config
