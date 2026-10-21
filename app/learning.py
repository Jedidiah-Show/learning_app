"""Shared curriculum access rules."""

from app.models import LearningProject, Progress
from datetime import datetime, date


def curriculum_days(config):
    if not isinstance(config, dict) or config.get('app', {}).get('curriculum_days') != 90:
        raise ValueError('The curriculum duration is fixed at 90 days')
    return 90


def next_unlocked_day(user, config):
    """Return the first day not fully completed by this user."""
    subjects = config['subjects']
    total_days = curriculum_days(config)
    if total_days == 0:
        return 1
    # Batch fetch all progress for this user
    all_progress = Progress.query.filter(
        Progress.user_id == user.id,
        Progress.day_number <= total_days
    ).all()
    progress_map = {(p.subject_id, p.day_number): p for p in all_progress}
    completed_weeks = {
        week_number for (week_number,) in LearningProject.query.with_entities(
            LearningProject.week_number
        ).filter_by(user_id=user.id, completed=True).all()
    }
    unlock_rules = config['schedule']['unlock_rules']
    for day in range(1, total_days + 1):
        if (
            day > 1 and (day - 1) % 7 == 0
            and not unlock_rules.get('allow_continue_after_day_complete', True)
        ):
            if (day - 1) // 7 not in completed_weeks:
                return day - 1
        day_completed = [
            bool(
                progress_map.get((subject['id'], day))
                and progress_map[(subject['id'], day)].completed
            )
            for subject in subjects
        ]
        completed = (
            all(day_completed)
            if unlock_rules.get('require_all_subjects_complete', True)
            else any(day_completed)
        )
        if not completed:
            return day
    if not unlock_rules.get('allow_continue_after_day_complete', True):
        final_week = (total_days + 6) // 7
        if final_week not in completed_weeks:
            return total_days
    return total_days + 1


def day_is_available(user, config, day_number):
    return 1 <= day_number <= curriculum_days(config) and day_number <= next_unlocked_day(user, config)
