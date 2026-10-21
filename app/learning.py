"""Shared curriculum access rules."""

from app.models import LearningProject, Progress
from datetime import datetime, date


def curriculum_days(config):
    app_cfg = config.get('app', {}) if isinstance(config, dict) else {}
    configured_days = app_cfg.get('curriculum_days', app_cfg.get('total_days'))
    if configured_days is not None:
        if not isinstance(configured_days, int) or isinstance(configured_days, bool) or configured_days < 1:
            raise ValueError('Configured curriculum_days must be a positive integer')
        return configured_days
    lesson_cfg = config.get('lesson_generation', {}) if isinstance(config, dict) else {}
    if lesson_cfg.get('total_days') is not None:
        if not isinstance(lesson_cfg['total_days'], int) or lesson_cfg['total_days'] < 1:
            raise ValueError('lesson_generation.total_days must be a positive integer')
        return lesson_cfg['total_days']
    schedule_cfg = config.get('schedule', {}) if isinstance(config, dict) else {}
    assessment_date = app_cfg.get('assessment_date')
    start_date = schedule_cfg.get('start_date') or date.today().isoformat()
    if assessment_date:
        try:
            assess = date.fromisoformat(str(assessment_date))
            start = date.fromisoformat(str(start_date))
        except (TypeError, ValueError) as error:
            raise ValueError('Curriculum dates must use YYYY-MM-DD') from error
        if assess < start:
            raise ValueError('Assessment date is before the course start; configure curriculum_days explicitly')
        return (assess - start).days + 1
    raise ValueError('Set app.curriculum_days or configure a valid course date range')


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
    for day in range(1, total_days + 1):
        if day > 1 and (day - 1) % 7 == 0:
            completed_project = LearningProject.query.filter_by(
                user_id=user.id,
                week_number=(day - 1) // 7,
                completed=True,
            ).first()
            if completed_project is None:
                return day - 1
        completed = all(
            (progress_map.get((subject['id'], day))) is not None and progress_map[(subject['id'], day)].completed
            for subject in subjects
        )
        if not completed:
            return day
    final_week = (total_days + 6) // 7
    final_project = LearningProject.query.filter_by(
        user_id=user.id,
        week_number=final_week,
        completed=True,
    ).first()
    return total_days + 1 if final_project else total_days


def day_is_available(user, config, day_number):
    return 1 <= day_number <= curriculum_days(config) and day_number <= next_unlocked_day(user, config)
