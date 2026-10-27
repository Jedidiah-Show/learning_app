"""Course pages and learner preferences."""

from datetime import date
import hmac
import json
import os

from flask import Blueprint, abort, current_app, jsonify, render_template
from flask_login import current_user, login_required

from app import db
from app.curriculum import all_lessons, all_modules, curriculum, get_lesson
from app.learning import course_progress, lesson_is_available
from app.google_calendar import GoogleAuthorizationError, GoogleCalendarError
from app.integrations import database_status
from app.models import CalendarEvent
from app.user_preferences import get_effective_config_for_user, get_user_preferences, set_user_preferences
from app.request_data import get_json_object

main_bp = Blueprint('main', __name__)


def admin_required(f):
    from functools import wraps

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@main_bp.route('/healthz')
def healthz():
    database = database_status()
    commit = (os.environ.get('VERCEL_GIT_COMMIT_SHA') or '')[:7] or None
    response = jsonify({
        'status': 'ok' if database['ok'] else 'degraded',
        'commit': commit,
        'database': {
            'ok': database['ok'],
            'revision': database['current_revision'],
            'missing_tables': database['missing_tables'],
            'missing_columns': database.get('missing_columns', []),
        },
    })
    response.headers['Cache-Control'] = 'no-store'
    return response, 200 if database['ok'] else 503


@main_bp.route('/')
@login_required
def index():
    progress = course_progress(current_user)
    config = get_effective_config_for_user(current_user)
    next_lesson = get_lesson(progress['next_lesson_id']) if progress['next_lesson_id'] else None
    next_project = progress['next_action'] if progress['next_action'] and progress['next_action']['type'] == 'project' else None
    return render_template('dashboard.html', config=config, user=current_user,
                           course=curriculum(),
                           progress=progress, next_lesson=next_lesson,
                           next_project=next_project)


@main_bp.route('/lessons')
@login_required
def lessons():
    from app.learning import completed_lesson_ids
    return render_template('lessons.html', config=get_effective_config_for_user(current_user),
                           user=current_user, modules=all_modules(),
                           completed_ids=completed_lesson_ids(current_user),
                           next_lesson_id=course_progress(current_user)['next_lesson_id'])


@main_bp.route('/quizzes')
@login_required
def quizzes():
    return render_template('quizzes.html', config=get_effective_config_for_user(current_user),
                           user=current_user, modules=all_modules())


@main_bp.route('/schedule')
@login_required
def schedule():
    progress = course_progress(current_user)
    return render_template('schedule.html', config=get_effective_config_for_user(current_user),
                           user=current_user, modules=all_modules(), progress=progress,
                           next_action=progress['next_action'],
                           next_lesson=get_lesson(progress['next_lesson_id'])
                           if progress['next_lesson_id'] else None)


@main_bp.route('/progress')
@login_required
def progress():
    return render_template('progress.html', config=get_effective_config_for_user(current_user),
                           user=current_user, progress=course_progress(current_user))


@main_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html', config=get_effective_config_for_user(current_user),
                           user=current_user,
                           gemini_configured=bool(current_app.config.get('GEMINI_API_KEY')))


@main_bp.route('/lesson/<lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = get_lesson(lesson_id)
    if not lesson:
        abort(404)
    if not lesson_is_available(current_user, lesson_id):
        abort(403)
    from app.learning import completed_lesson_ids
    from app.practice import practice_exercises_for_lesson
    from app.models import VideoProgress
    video_progress = None
    if lesson.get('video'):
        video_progress = VideoProgress.query.filter_by(
            user_id=current_user.id, lesson_id=lesson_id
        ).first()
        if video_progress and video_progress.video_id != lesson['video']['id']:
            video_progress = None
    lessons = all_lessons()
    ordinal = lesson['_ordinal'] - 1
    previous_lesson = lessons[ordinal - 1] if ordinal > 0 else None
    next_lesson = lessons[ordinal + 1] if ordinal + 1 < len(lessons) else None
    completed = lesson_id in completed_lesson_ids(current_user)
    return render_template('lessons/detail.html', lesson=lesson, module=lesson['_module'],
                           completed=completed,
                           practice_exercises=practice_exercises_for_lesson(lesson_id),
                           next_lesson_id=course_progress(current_user)['next_lesson_id'],
                           video_progress=video_progress,
                           previous_lesson=previous_lesson,
                           next_lesson=next_lesson,
                           next_lesson_available=(
                               next_lesson is not None
                               and lesson_is_available(current_user, next_lesson['id'])
                           ),
                           config=get_effective_config_for_user(current_user), user=current_user)


@main_bp.route('/api/settings/preferences', methods=['POST'])
@login_required
def update_preferences():
    data = get_json_object()
    if not isinstance(data, dict) or set(data) - {'ai', 'progress', 'google_calendar'}:
        return jsonify({'error': 'Only AI model, progress, and calendar preferences are editable'}), 400
    allowed = {'ai': {'model_tier'}, 'progress': {'track_streaks', 'track_time_spent'},
               'google_calendar': {'enabled', 'calendar_id', 'event_prefix', 'reminder_minutes'}}
    for section, values in data.items():
        if not isinstance(values, dict) or set(values) - allowed[section]:
            return jsonify({'error': f'Invalid {section} preferences'}), 400
    if 'ai' in data and data['ai'].get('model_tier') not in {'flash', 'pro'}:
        return jsonify({'error': 'model_tier must be flash or pro'}), 400
    if 'progress' in data and any(
        not isinstance(value, bool)
        for value in data['progress'].values()
    ):
        return jsonify({'error': 'Progress preferences must be boolean'}), 400
    if 'google_calendar' in data:
        calendar = data['google_calendar']
        for field in ('calendar_id', 'event_prefix'):
            if field in calendar and (
                not isinstance(calendar[field], str)
                or not calendar[field].strip()
                or len(calendar[field]) > 200
                or any(character in calendar[field] for character in '\r\n')
            ):
                return jsonify({'error': f'{field} must be a non-empty single-line string of at most 200 characters'}), 400
            if isinstance(calendar.get(field), str):
                calendar[field] = calendar[field].strip()
        if 'enabled' in calendar and not isinstance(calendar['enabled'], bool):
            return jsonify({'error': 'enabled must be true or false'}), 400
        if 'reminder_minutes' in calendar and (
            not isinstance(calendar['reminder_minutes'], int)
            or isinstance(calendar['reminder_minutes'], bool)
            or not 0 <= calendar['reminder_minutes'] <= 10080
        ):
            return jsonify({'error': 'reminder_minutes must be an integer between 0 and 10080'}), 400
        previous_config = get_effective_config_for_user(current_user)
        if (
            'calendar_id' in calendar
            and calendar['calendar_id'] != previous_config['google_calendar']['calendar_id']
            and CalendarEvent.query.filter_by(
                user_id=current_user.id, synced_to_google=True
            ).count()
        ):
            return jsonify({'error': 'Remove existing app-managed Google Calendar events before changing the calendar ID'}), 409
    prefs = get_user_preferences(current_user)
    for section, values in data.items():
        prefs.setdefault(section, {}).update(values)
    set_user_preferences(current_user, prefs)
    db.session.commit()
    if (
        'google_calendar' in data
        and CalendarEvent.query.filter_by(user_id=current_user.id).count()
    ):
        try:
            from app.routes.calendar import reconcile_calendar_schedule
            reconcile_calendar_schedule(
                current_user,
                get_effective_config_for_user(current_user)['schedule']['daily_blocks'],
            )
        except GoogleAuthorizationError:
            return jsonify({'error': 'Preferences saved, but Google Calendar needs to be reconnected.'}), 401
        except GoogleCalendarError as error:
            current_app.logger.warning(
                'Calendar preference reconciliation failed for user %s: %s',
                current_user.id, error,
            )
            return jsonify({
                'error': f'Preferences saved, but {error}',
            }), 502
        except Exception:
            current_app.logger.exception('Could not reconcile Calendar preferences for user %s', current_user.id)
            return jsonify({'error': 'Preferences saved, but Calendar sync is incomplete. Retry to finish syncing.'}), 502
    return jsonify({'status': 'success'})


@main_bp.route('/admin')
@admin_required
def admin_dashboard():
    from app.models import User, LessonCompletion, CourseProject, StudySession
    from app.curriculum import all_lessons, all_modules
    from sqlalchemy import func
    from datetime import datetime, timedelta
    total_users = User.query.count()
    active_users = User.query.filter(
        User.last_active >= datetime.utcnow() - timedelta(days=30)
    ).count()
    total_completions = LessonCompletion.query.filter_by(completed=True).count()
    total_projects = CourseProject.query.filter_by(completed=True).count()
    total_lessons = len(all_lessons())
    total_modules = len(all_modules())
    recent_completions = LessonCompletion.query.filter_by(
        completed=True
    ).order_by(LessonCompletion.completed_at.desc()).limit(10).all()
    return render_template(
        'admin/dashboard.html',
        config=get_effective_config_for_user(current_user),
        user=current_user,
        total_users=total_users,
        active_users=active_users,
        total_completions=total_completions,
        total_projects=total_projects,
        total_lessons=total_lessons,
        total_modules=total_modules,
        recent_completions=recent_completions,
    )


@main_bp.route('/admin/users')
@admin_required
def admin_users():
    from app.models import User, LessonCompletion
    from sqlalchemy import func
    from app.curriculum import all_lessons
    total_lessons = len(all_lessons())
    users = User.query.order_by(User.created_at.desc()).all()
    progress_by_user = dict(
        db.session.query(
            LessonCompletion.user_id,
            func.count(LessonCompletion.id),
        ).filter(
            LessonCompletion.completed.is_(True)
        ).group_by(LessonCompletion.user_id).all()
    )
    return render_template(
        'admin/users.html',
        config=get_effective_config_for_user(current_user),
        user=current_user,
        users=users,
        total_lessons=total_lessons,
        progress_by_user=progress_by_user,
    )


@main_bp.route('/admin/analytics')
@admin_required
def admin_analytics():
    from app.models import User, LessonCompletion, CourseProject
    from sqlalchemy import func
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=30)
    completions = db.session.query(
        func.date(LessonCompletion.completed_at).label('date'),
        func.count(LessonCompletion.id).label('count')
    ).filter(
        LessonCompletion.completed.is_(True),
        LessonCompletion.completed_at >= since,
    ).group_by(func.date(LessonCompletion.completed_at)).order_by(
        func.date(LessonCompletion.completed_at)
    ).all()
    module_counts = db.session.query(
        LessonCompletion.subject_id,
        func.count(LessonCompletion.id),
    ).filter(
        LessonCompletion.completed.is_(True)
    ).group_by(LessonCompletion.subject_id).all()
    return render_template(
        'admin/analytics.html',
        config=get_effective_config_for_user(current_user),
        user=current_user,
        completions=completions,
        module_counts=module_counts,
        since=since.date(),
    )


@main_bp.route('/admin/users/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    from app.models import User, LessonCompletion, CourseProject, StudySession
    from sqlalchemy import func
    from app.curriculum import all_lessons
    from app.learning import course_progress
    account = User.query.get_or_404(user_id)
    progress = course_progress(account)
    total_minutes = db.session.query(
        func.coalesce(func.sum(StudySession.duration_minutes), 0)
    ).filter(StudySession.user_id == account.id).scalar()
    return render_template(
        'admin/user_detail.html',
        config=get_effective_config_for_user(current_user),
        user=current_user,
        account=account,
        progress=progress,
        total_minutes=int(total_minutes or 0),
    )


@main_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@admin_required
def admin_set_role(user_id):
    from app.models import User
    account = User.query.get_or_404(user_id)
    if account.id == current_user.id:
        return jsonify({'error': 'You cannot change your own admin access'}), 400
    account.is_admin = not account.is_admin
    db.session.commit()
    return jsonify({'status': 'success', 'is_admin': account.is_admin})
