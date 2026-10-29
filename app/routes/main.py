"""Course pages and learner preferences."""

import os
from datetime import datetime, timezone
from functools import lru_cache

from flask import (Blueprint, Response, abort, current_app, flash, jsonify,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.curriculum import all_lessons, all_modules, curriculum, get_lesson
from app.learning import (
    course_progress, lesson_is_available, monthly_milestone_progress,
)
from app.google_calendar import GoogleAuthorizationError, GoogleCalendarError
from app.integrations import database_status
from app.models import (CalendarEvent, LessonBookmark, LessonNote, LessonCompletion,
                        CourseProject, QuizResult, ReviewItem, StudySession)
from app.user_preferences import get_effective_config_for_user, get_user_preferences, set_user_preferences
from app.request_data import get_json_object

main_bp = Blueprint('main', __name__)


@lru_cache(maxsize=1)
def _lesson_search_index():
    indexed = []
    for lesson in all_lessons():
        body = ' '.join(str(page) for page in lesson.get('pages') or [])
        text = ' '.join([
            lesson.get('title', ''), lesson.get('goal', ''),
            ' '.join(lesson.get('outcomes') or []),
            ' '.join(lesson.get('tasks') or []), body,
        ])
        indexed.append((lesson, text, text.lower()))
    return indexed


@main_bp.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    from app.storage import StorageError, get_storage
    try:
        data, content_type = get_storage().read(filename)
    except FileNotFoundError:
        abort(404)
    except StorageError:
        current_app.logger.exception('Could not read stored upload')
        abort(404)
    response = Response(data, mimetype=content_type)
    response.headers['Cache-Control'] = 'private, no-cache, max-age=0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def _deployment_commit():
    return (
        os.environ.get('RENDER_GIT_COMMIT')
        or os.environ.get('GIT_COMMIT_SHA')
        or os.environ.get('VERCEL_GIT_COMMIT_SHA')
        or ''
    )[:7] or None


@main_bp.route('/healthz')
def healthz():
    """Liveness check: no database or external calls."""
    response = jsonify({
        'status': 'ok',
        'commit': _deployment_commit(),
        'version': '1.0.0',
    })
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Health-Status'] = 'ok'
    return response, 200


@main_bp.route('/readyz')
def readyz():
    """Readiness check: verifies the database schema is usable."""
    database = database_status()
    response = jsonify({
        'status': 'ok' if database['ok'] else 'degraded',
        'commit': _deployment_commit(),
        'version': '1.0.0',
        'database': {
            'ok': database['ok'],
            'revision': database['current_revision'],
            'missing_tables': database['missing_tables'],
            'missing_columns': database.get('missing_columns', []),
        },
    })
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Health-Status'] = 'ok' if database['ok'] else 'degraded'
    return response, 200 if database['ok'] else 503


@main_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip().lower()[:100]
    module_filter = request.args.get('module', '').strip()
    if not query:
        return render_template('search.html', query='', results=[],
                               modules=all_modules(), module_filter=module_filter)
    results = []
    for lesson, text, searchable in _lesson_search_index():
        if module_filter and lesson.get('module_id') != module_filter:
            continue
        if query in searchable:
            match_at = searchable.find(query)
            snippet_text = ' '.join(text[max(0, match_at - 65):match_at + len(query) + 100].split())
            results.append({
                'id': lesson['id'],
                'title': lesson['title'],
                'module': lesson.get('_module', {}).get('title'),
                'module_number': lesson.get('_module', {}).get('number'),
                'ordinal': lesson.get('_ordinal'),
                'module_id': lesson.get('module_id'),
                'snippet': ('…' if match_at > 65 else '') + snippet_text + ('…' if match_at + len(query) + 100 < len(text) else ''),
            })
        if len(results) >= 50:
            break
    return render_template('search.html', query=query, results=results,
                           modules=all_modules(), module_filter=module_filter)


@main_bp.route('/')
@login_required
def index():
    try:
        progress = course_progress(current_user)
        config = get_effective_config_for_user(current_user)
        next_lesson = get_lesson(progress['next_lesson_id']) if progress['next_lesson_id'] else None
        next_project = progress['next_action'] if progress['next_action'] and progress['next_action']['type'] == 'project' else None
        streak = getattr(current_user, 'streak', 0) or 0
        longest_streak = getattr(current_user, 'longest_streak', 0) or 0
        return render_template('dashboard.html', config=config, user=current_user,
                               course=curriculum(),
                               progress=progress, next_lesson=next_lesson,
                               next_project=next_project, streak=streak,
                               longest_streak=longest_streak)
    except Exception:
        current_app.logger.exception('Dashboard error')
        return render_template('dashboard.html', course=curriculum(),
                               progress_error=True), 503


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
    upcoming_events = CalendarEvent.query.filter(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time >= datetime.now(timezone.utc).replace(tzinfo=None),
        CalendarEvent.delete_pending.is_(False),
    ).order_by(CalendarEvent.start_time).limit(20).all()
    from app.google_calendar import resolve_timezone, stored_utc
    scheduled_events = [{
        'event': event,
        'start_local': stored_utc(event.start_time).astimezone(resolve_timezone(event.time_zone)),
        'end_local': stored_utc(event.end_time).astimezone(resolve_timezone(event.time_zone)),
    } for event in upcoming_events]
    return render_template('schedule.html', config=get_effective_config_for_user(current_user),
                           user=current_user, modules=all_modules(), progress=progress,
                           upcoming_events=upcoming_events, scheduled_events=scheduled_events,
                           next_action=progress['next_action'],
                           next_lesson=get_lesson(progress['next_lesson_id'])
                           if progress['next_lesson_id'] else None)


@main_bp.route('/progress')
@login_required
def progress():
    from datetime import date, datetime, timedelta, timezone
    config = get_effective_config_for_user(current_user)
    completions = LessonCompletion.query.filter_by(
        user_id=current_user.id, completed=True
    ).all()
    dates = {item.completed_at.date() for item in completions if item.completed_at}
    streak = 0
    cursor = date.today()
    if cursor not in dates:
        cursor -= timedelta(days=1)
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    if not config.get('progress', {}).get('track_streaks', True):
        streak = 0
    quizzes = QuizResult.query.filter_by(user_id=current_user.id).order_by(
        QuizResult.taken_at.desc()
    ).limit(10).all()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    track_time = config.get('progress', {}).get('track_time_spent', True)
    minutes = 0
    if track_time:
        minutes = db.session.query(db.func.coalesce(db.func.sum(StudySession.duration_minutes), 0)).filter(
            StudySession.user_id == current_user.id, StudySession.date >= cutoff.date()
        ).scalar() or 0
    due_reviews = ReviewItem.query.filter_by(user_id=current_user.id, active=True).filter(
        ReviewItem.due_at <= now
    ).count()
    analytics = {
        'streak': streak, 'minutes_30d': minutes, 'due_reviews': due_reviews,
        'quiz_results': quizzes,
    }
    recent_completions = LessonCompletion.query.filter_by(
        user_id=current_user.id, completed=True
    ).order_by(LessonCompletion.completed_at.desc()).limit(8).all()
    projects = CourseProject.query.filter_by(
        user_id=current_user.id, completed=True
    ).all()
    progress_data = course_progress(current_user)
    completed_project_ids = {item.module_id for item in projects}
    from app.leaderboard import leaderboard_data
    leaderboard_info = leaderboard_data(current_user)
    return render_template('progress.html', config=config,
                           user=current_user, progress=progress_data,
                           analytics=analytics,
                           milestones=monthly_milestone_progress(
                               progress_data, completed_project_ids
                           ),
                           leaderboard=leaderboard_info,
                           leaderboard_opted_in=leaderboard_info['opted_in'],
                           recent_completions=recent_completions,
                           recent_lessons={item.lesson_id: get_lesson(item.lesson_id)
                                           for item in recent_completions},
                           completed_project_ids=completed_project_ids)


@main_bp.route('/review')
@login_required
def review():
    return render_template('review.html', user=current_user)


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
    from app.models import VideoProgress, LessonBookmark, LessonNote
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
    progress = course_progress(current_user)
    try:
        bookmarked = LessonBookmark.query.filter_by(
            user_id=current_user.id, lesson_id=lesson_id
        ).first() is not None
        note = LessonNote.query.filter_by(
            user_id=current_user.id, lesson_id=lesson_id
        ).first()
    except SQLAlchemyError:
        # Older deployments may not have applied the notes/bookmarks migration.
        # Keep course content readable while logging the schema issue.
        db.session.rollback()
        current_app.logger.exception(
            'Lesson notes/bookmarks unavailable for user %s, lesson %s',
            current_user.id, lesson_id,
        )
        bookmarked, note = False, None
        flash('Lesson loaded, but saved notes and bookmarks are unavailable until the database update is applied.', 'info')
    return render_template('lessons/detail.html', lesson=lesson, module=lesson['_module'],
                           completed=completed,
                           practice_exercises=practice_exercises_for_lesson(lesson_id),
                           next_lesson_id=progress['next_lesson_id'],
                           next_action=progress['next_action'],
                           projects_url=url_for('projects.project_page'),
                           video_progress=video_progress,
                           previous_lesson=previous_lesson,
                           next_lesson=next_lesson,
                           next_lesson_available=(
                               next_lesson is not None
                               and lesson_is_available(current_user, next_lesson['id'])
                           ),
                           bookmarked=bookmarked,
                           lesson_note=note.content if note else '',
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
