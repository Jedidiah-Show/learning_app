from flask import Blueprint, request, jsonify, current_app
from app import db
from app.user_subjects import get_effective_config_for_user, get_effective_subjects_for_user
from app.models import User, Progress, LessonCompletion, QuizResult
from flask_login import current_user, login_required
from app.user_subjects import get_effective_subjects_for_user
from app.learning import curriculum_days, next_unlocked_day, day_is_available
from app.request_data import get_json_object
from datetime import datetime, date, timezone
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    user = current_user
    
    config = get_effective_config_for_user(current_user)
    subjects = get_effective_subjects_for_user(current_user)
    
    # Calculate progress per subject
    dashboard_data = {
        'user_id': user.id,
        'assessment_date': config['app']['assessment_date'],
        'subjects': [],
        'overall_progress': 0,
        'days_completed': 0
    }
    dashboard_data['curriculum_days'] = curriculum_days(config)
    dashboard_data['next_unlocked_day'] = next_unlocked_day(user, config)
    
    total_completed = 0
    total_possible = 0
    days_completed = 0
    total_days = curriculum_days(config)
    
    # Batch fetch all progress for this user up to total_days
    all_progress = Progress.query.filter(
        Progress.user_id == user.id,
        Progress.day_number <= total_days
    ).all()
    progress_by_key = {(p.subject_id, p.day_number): p for p in all_progress}
    
    for subject in subjects:
        completed_count = sum(
            1 for day in range(1, total_days + 1)
            if progress_by_key.get((subject['id'], day)) and progress_by_key[(subject['id'], day)].completed
        )
        dashboard_data['subjects'].append({
            'id': subject['id'],
            'name': subject['name'],
            'icon': subject['icon'],
            'color': subject['color'],
            'completed': completed_count,
            'total_days': total_days,
            'percentage': round((completed_count / total_days * 100) if total_days > 0 else 0, 1),
            'starting_proficiency': subject.get('stated_proficiency', 'Novice'),
            'current_proficiency': subject.get('proficiency', 'Novice'),
            'target_proficiency': config.get('learning', {}).get(
                'target_proficiency', 'Advanced'
            ),
        })
        
        total_completed += completed_count
        total_possible += total_days

    for day in range(1, total_days + 1):
        if all(
            progress_by_key.get((s['id'], day)) is not None and progress_by_key[(s['id'], day)].completed
            for s in subjects
        ):
            days_completed += 1
    dashboard_data['days_completed'] = days_completed
    dashboard_data['study_streak_days'] = None
    if config.get('progress', {}).get('track_streaks', True):
        try:
            user_zone = ZoneInfo(request.headers.get('X-Timezone', 'UTC'))
        except (ZoneInfoNotFoundError, ValueError):
            user_zone = timezone.utc
        completion_dates = {
            (
                item.replace(tzinfo=timezone.utc)
                if item.tzinfo is None else item
            ).astimezone(user_zone).date()
            for (item,) in db.session.query(Progress.completion_date).filter(
                Progress.user_id == user.id,
                Progress.completed.is_(True),
                Progress.completion_date.isnot(None),
            ).distinct()
        }
        today = datetime.now(user_zone).date()
        current = today if today in completion_dates else today - timedelta(days=1)
        streak = 0
        while current in completion_dates:
            streak += 1
            current -= timedelta(days=1)
        dashboard_data['study_streak_days'] = streak
    
    if total_possible > 0:
        dashboard_data['overall_progress'] = round((total_completed / total_possible * 100), 1)
    
    return jsonify(dashboard_data)

@progress_bp.route('/update', methods=['POST'])
@login_required
def update_progress():
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    user = current_user
    
    subject_id = data.get('subject_id')
    day_number = data.get('day_number')
    completed = data.get('completed', False)
    config = get_effective_config_for_user(current_user)
    subject = next((s for s in get_effective_subjects_for_user(current_user) if s['id'] == subject_id), None)
    if not subject or not isinstance(day_number, int) or isinstance(day_number, bool) or day_number < 1 or day_number > curriculum_days(config):
        return jsonify({'error': 'Invalid subject or day'}), 400
    if not isinstance(completed, bool):
        return jsonify({'error': 'completed must be a boolean'}), 400
    if completed:
        return jsonify({'error': 'Complete lessons through the lesson page'}), 400
    if not day_is_available(user, config, day_number):
        return jsonify({'error': 'Day is locked', 'next_unlocked_day': next_unlocked_day(user, config)}), 403
    try:
        time_spent = int(data.get('time_spent_minutes', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'time_spent_minutes must be an integer'}), 400
    if time_spent < 0 or time_spent > 1440:
        return jsonify({'error': 'time_spent_minutes must be between 0 and 1440'}), 400
    if not config.get('progress', {}).get('track_time_spent', True):
        time_spent = 0
    
    progress = Progress.query.filter_by(
        user_id=user.id, 
        subject_id=subject_id, 
        day_number=day_number
    ).first()
    
    if not progress:
        progress = Progress(
            user_id=user.id,
            subject_id=subject_id,
            day_number=day_number
        )
        db.session.add(progress)
    
    # This endpoint records study time only. Lesson completion is authoritative
    # and can only be set by /api/lessons/complete.
    progress.time_spent_minutes = (progress.time_spent_minutes or 0) + time_spent
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'progress_id': progress.id})
