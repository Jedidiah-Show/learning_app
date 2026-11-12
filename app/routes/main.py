"""Course pages and learner preferences."""

import os
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urlsplit

from flask import (Blueprint, Response, abort, current_app, flash, g, jsonify,
                   redirect, render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.curriculum import all_lessons, all_modules, curriculum, get_lesson
from app.ml_pathway import machine_learning_pathway
from app.ml_pathway import get_machine_learning_lesson, machine_learning_lessons
from app.ml_pathway import machine_learning_lesson_is_open, ml_pathway_overview
from app.ml_pathway import ml_module_progress
from app.ml_pathway import ml_pathway_pacing, record_pathway_review
from app.learning import (
    completed_lesson_ids, completed_project_modules, course_progress,
    lesson_is_available, monthly_milestone_progress,
    pathway_dashboard_progress, user_track,
)
from app.course_data import SETUP_CHECKS, TRACKS, track_label
from app.google_calendar import GoogleAuthorizationError, GoogleCalendarError
from app.integrations import database_status
from app.models import (CalendarEvent, LessonBookmark, LessonNote, LessonCompletion,
                        CoursePlan, CourseProject, MLSpecializationLessonCompletion,
                        MLSpecializationProject, Quiz, QuizResult, ReviewItem,
                        StudySession, SupportRequest)
from app.user_preferences import get_effective_config_for_user, get_user_preferences, set_user_preferences
from app.request_data import get_json_object
from app.services.lesson_state import learner_today, stored_setup_checks

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


@lru_cache(maxsize=1)
def _pathway_search_index():
    """Index the ML manifest separately: it ships as its own file.

    Entries are read out of ``pathway_lessons`` so they arrive already carrying
    their scoped ordinal and module, exactly like the AI rows beside them.
    """
    from app.pathway_scope import pathway_lessons

    indexed = []
    for lesson in pathway_lessons('ml'):
        if lesson.get('source') != 'ml':
            continue
        sections = ' '.join(
            ' '.join([section.get('heading', ''), ' '.join(section.get('body') or [])])
            for section in lesson.get('sections') or []
        )
        text = ' '.join([
            lesson.get('title', ''), lesson.get('goal', ''),
            lesson.get('task', ''), sections,
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
            'head_revision': database.get('head_revision'),
            'migration_current': database.get('migration_current', True),
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
    from app.pathway_scope import destination_for, is_ml, pathway_modules
    query = request.args.get('q', '').strip().lower()[:100]
    module_filter = request.args.get('module', '').strip()
    bookmarked_only = request.args.get('bookmarked') == '1'
    destination = destination_for(current_user)
    # Both the module filter and the index follow the pathway: an ML learner
    # searches the foundation plus their pathway, never the AI continuation.
    modules = pathway_modules(destination)
    index = list(_lesson_search_index())
    if is_ml(destination):
        index.extend(_pathway_search_index())
    bookmarked_ids = None
    if bookmarked_only:
        from app.models import LessonBookmark
        bookmarked_ids = {
            lesson_id for (lesson_id,) in db.session.query(
                LessonBookmark.lesson_id
            ).filter_by(user_id=current_user.id).all()
        }
        index = [
            entry for entry in index if entry[0]['id'] in bookmarked_ids
        ]
    if not query:
        # A bookmarked-only filter with no query lists the saved lessons.
        if bookmarked_only:
            results = []
            for lesson, text, searchable in index:
                if module_filter and lesson.get('module_id') != module_filter:
                    continue
                results.append({
                    'id': lesson['id'],
                    'title': lesson['title'],
                    'module': lesson.get('_module', {}).get('title') or lesson.get('module_title'),
                    'module_number': lesson.get('_module', {}).get('number') or lesson.get('module_number'),
                    'ordinal': lesson.get('_ordinal'),
                    'module_id': lesson.get('module_id'),
                    'source': lesson.get('source'),
                    'snippet': ' '.join(str(lesson.get('goal') or '').split()),
                })
                if len(results) >= 50:
                    break
            return render_template('search.html', query='', results=results,
                                   modules=modules, module_filter=module_filter,
                                   bookmarked_only=True)
        return render_template('search.html', query='', results=[],
                               modules=modules, module_filter=module_filter,
                               bookmarked_only=False)
    results = []
    for lesson, text, searchable in index:
        if module_filter and lesson.get('module_id') != module_filter:
            continue
        if query in searchable:
            match_at = searchable.find(query)
            snippet_text = ' '.join(text[max(0, match_at - 65):match_at + len(query) + 100].split())
            results.append({
                'id': lesson['id'],
                'title': lesson['title'],
                'module': lesson.get('_module', {}).get('title') or lesson.get('module_title'),
                'module_number': lesson.get('_module', {}).get('number') or lesson.get('module_number'),
                'ordinal': lesson.get('_ordinal'),
                'module_id': lesson.get('module_id'),
                'source': lesson.get('source'),
                'snippet': ('…' if match_at > 65 else '') + snippet_text + ('…' if match_at + len(query) + 100 < len(text) else ''),
            })
        if len(results) >= 50:
            break
    return render_template('search.html', query=query, results=results,
                           modules=modules, module_filter=module_filter,
                           bookmarked_only=bookmarked_only)


@main_bp.route('/api/search')
@login_required
def search_api():
    """JSON counterpart to /search: powers the ⌘/Ctrl+K command palette."""
    from app.pathway_scope import destination_for, is_ml
    from flask import url_for
    query = request.args.get('q', '').strip().lower()[:100]
    try:
        limit = min(max(int(request.args.get('limit', 8)), 1), 12)
    except (TypeError, ValueError):
        limit = 8
    if len(query) < 2:
        return jsonify({'results': []})
    destination = destination_for(current_user)
    index = list(_lesson_search_index())
    if is_ml(destination):
        index.extend(_pathway_search_index())
    results = []
    for lesson, text, searchable in index:
        if query in searchable:
            module = lesson.get('_module') or {}
            source = lesson.get('source')
            if source == 'ml':
                url = url_for('main.machine_learning_lesson', lesson_id=lesson['id'])
            else:
                url = url_for('main.lesson_detail', lesson_id=lesson['id'])
            results.append({
                'id': lesson['id'],
                'title': lesson['title'],
                'module_number': module.get('number') or lesson.get('module_number'),
                'ordinal': lesson.get('_ordinal'),
                'badge': module.get('badge') or lesson.get('badge'),
                'source': source,
                'url': url,
            })
        if len(results) >= limit:
            break
    return jsonify({'results': results})


@main_bp.route('/')
@login_required
def index():
    try:
        # Read each completion set once and share it with every consumer below;
        # the dashboard previously re-ran the same queries several times over.
        completed_ids = completed_lesson_ids(current_user)
        completed_project_ids = completed_project_modules(current_user)
        progress = course_progress(
            current_user, completed=completed_ids,
            completed_projects=completed_project_ids,
        )
        config = get_effective_config_for_user(current_user)
        setup_checks = SETUP_CHECKS
        setup_states = stored_setup_checks(current_user)
        setup_done = sum(1 for check in setup_checks if setup_states.get(check['id']))
        plan = CoursePlan.query.filter_by(user_id=current_user.id).first()
        onboarding_complete = bool(
            plan and plan.skill_level and plan.weekly_hours
        )
        # Stage D: the confirmed pathway destination decides which section the
        # dashboard leads with; unset keeps today's shared-foundation layout.
        pathway_destination = plan.pathway_destination if plan else None
        # Seed the per-request cache the nav shell reads, so rendering the
        # dashboard does not fetch the same plan a second time.
        g.pathway_destination = pathway_destination
        # An ML destination's curriculum is fully independent; AI Engineering
        # modules never appear in its grid, totals, or completion claims.
        progress = pathway_dashboard_progress(
            current_user, pathway_destination, progress,
            completed=completed_ids, completed_projects=completed_project_ids,
        )
        # Derived after the swap above: an ML learner's "continue" pointers must
        # come from their own curriculum, never from a module 03-12 lesson.
        next_lesson = get_lesson(progress['next_lesson_id']) if progress['next_lesson_id'] else None
        next_project = progress['next_action'] if progress['next_action'] and progress['next_action']['type'] == 'project' else None
        next_module_id = None
        if progress.get('next_action'):
            action = progress['next_action']
            if action['type'] == 'project':
                next_module_id = action.get('module_id')
            elif action.get('lesson_id'):
                focused = get_lesson(action['lesson_id'])
                next_module_id = focused.get('module_id') if focused else None
        due_reviews = ReviewItem.query.filter_by(
            user_id=current_user.id, active=True
        ).filter(ReviewItem.due_at <= datetime.now(timezone.utc)).count()
        module_states = {}
        for module in progress['modules']:
            if (
                module['project_completed']
                and module['completed_lessons'] == module['total_lessons']
            ):
                module_states[module['id']] = 'complete'
            elif module['id'] == next_module_id:
                module_states[module['id']] = (
                    'project'
                    if module['completed_lessons'] == module['total_lessons']
                    else 'current'
                )
            else:
                module_states[module['id']] = 'locked'
        # A failure in the optional pathway summary must not blank the whole
        # dashboard; the course card simply hides when the data is absent.
        try:
            ml_overview = ml_pathway_overview(current_user.id)
        except Exception:
            current_app.logger.exception('ML pathway overview failed')
            ml_overview = None
        pathway_comparison = None
        if ml_overview:
            ai_lessons = all_lessons()
            pathway_comparison = {
                'ai': {
                    'completed': sum(
                        lesson['id'] in completed_ids for lesson in ai_lessons
                    ),
                    'total': len(ai_lessons),
                },
                'ml': {
                    'completed': ml_overview['completed_lessons'],
                    'total': ml_overview['total_lessons'],
                },
            }
        # Lean read for the streak-triggered leaderboard nudge: just the flag.
        # Assumed opted in when the plan row is unreadable so we never nag
        # someone who already shared their rank.
        leaderboard_opted_in = bool(plan.leaderboard_opt_in) if plan else True
        return render_template('dashboard.html', config=config, user=current_user,
                               course=curriculum(),
                               progress=progress, next_lesson=next_lesson,
                               next_project=next_project, setup_checks=setup_checks,
                               setup_states=setup_states, setup_done=setup_done,
                               onboarding_complete=onboarding_complete,
                               next_module_id=next_module_id,
                               due_reviews=due_reviews,
                               ml_overview=ml_overview,
                               pathway_comparison=pathway_comparison,
                               pathway_destination=pathway_destination,
                               leaderboard_opted_in=leaderboard_opted_in)
    except Exception:
        current_app.logger.exception('Dashboard error')
        # The template dereferences progress even in the error branch, so the
        # 503 fallback must render with an explicitly empty progress payload
        # rather than omitting it (omitting it raised a second exception).
        return render_template('dashboard.html', course=curriculum(),
                               user=current_user, config={},
                               progress={
                                   'total_lessons': 0, 'completed_lessons': 0,
                                   'total_projects': 0, 'completed_projects': 0,
                                   'course_complete': False, 'modules': [],
                                   'next_lesson_id': None, 'next_action': None,
                               },
                               next_lesson=None, next_project=None,
                               onboarding_complete=True, next_module_id=None,
                               due_reviews=0, ml_overview=None,
                               pathway_comparison=None,
                               pathway_destination=None,
                               progress_error=True), 503


@main_bp.route('/lessons')
@login_required
def lessons():
    from app.pathway_scope import (
        destination_for, is_ml, pathway_header, pathway_modules,
    )
    completions = LessonCompletion.query.filter_by(
        user_id=current_user.id, completed=True
    ).all()
    completed_ids = {item.lesson_id for item in completions}
    plan = CoursePlan.query.filter_by(user_id=current_user.id).first()
    # The destination decides which modules this page lists at all: an ML
    # learner's catalog is the shared foundation plus their pathway, never the
    # AI continuation, and progress is scoped to match so the totals, the
    # "start here" pointer, and the rows agree.
    destination = destination_for(current_user)
    if is_ml(destination):
        from app.pathway_scope import ml_completion_state
        completed_ids |= ml_completion_state(current_user.id)[0]
    modules = pathway_modules(destination)
    progress = course_progress(
        current_user, completed=completed_ids, destination=destination
    )
    current_module_id = None
    if progress.get('next_lesson_id'):
        current = get_lesson(progress['next_lesson_id'])
        current_module_id = current.get('module_id') if current else None
    elif progress.get('next_action', {}).get('type') == 'project':
        current_module_id = progress['next_action'].get('module_id')
    # The "second pathway" strip is for learners who are not on the pathway;
    # an ML learner instead gets a card pointing at their own pathway home.
    try:
        ml_overview = None if is_ml(destination) else ml_pathway_overview(current_user.id)
    except Exception:
        current_app.logger.exception('ML pathway overview failed on lessons page')
        ml_overview = None
    return render_template('lessons.html', config=get_effective_config_for_user(current_user),
                           user=current_user, course=curriculum(), modules=modules,
                           completed_ids=completed_ids,
                           completion_sources={
                               item.lesson_id: item.completion_source for item in completions
                           },
                           next_lesson_id=progress['next_lesson_id'],
                           current_module_id=current_module_id,
                           header=pathway_header(destination),
                           ml_overview=ml_overview,
                           pathway_destination=destination,
                           skill_level=(plan.skill_level if plan else '') or '')


@main_bp.route('/practice')
@login_required
def practice_catalog():
    from app.practice import all_practice_exercises
    from app.pathway_scope import destination_for, pathway_lessons

    destination = destination_for(current_user)
    lessons_by_id = {
        lesson['id']: lesson for lesson in pathway_lessons(destination)
    }
    exercise_by_id = all_practice_exercises()
    scoped_exercises = [
        exercise for exercise in exercise_by_id.values()
        if exercise['lesson_id'] in lessons_by_id
    ]
    difficulty = request.args.get('difficulty', '').strip().lower()
    skill = request.args.get('skill', '').strip().lower()
    difficulties = sorted({item['difficulty'] for item in scoped_exercises})
    skills = sorted({
        item_skill for item in scoped_exercises
        for item_skill in item['skills']
    })
    if difficulty not in difficulties:
        difficulty = ''
    if skill not in skills:
        skill = ''

    exercises = []
    for exercise in scoped_exercises:
        lesson = lessons_by_id[exercise['lesson_id']]
        if difficulty and exercise['difficulty'] != difficulty:
            continue
        if skill and skill not in exercise['skills']:
            continue
        exercises.append({
            **exercise,
            'lesson_title': lesson['title'],
            'available': lesson_is_available(current_user, lesson['id']),
            'prerequisite_titles': [
                exercise_by_id[item]['title']
                for item in exercise['prerequisites']
                if item in exercise_by_id
            ],
        })
    return render_template(
        'practice.html',
        user=current_user,
        exercises=exercises,
        difficulties=difficulties,
        skills=skills,
        selected_difficulty=difficulty,
        selected_skill=skill,
    )



@main_bp.route('/specializations/machine-learning')
@login_required
def machine_learning_specialization():
    """Show the optional ML pathway without adding it to the shared course."""
    pathway = machine_learning_pathway()
    completions = MLSpecializationLessonCompletion.query.filter_by(
        user_id=current_user.id, pathway_id=pathway['id']
    ).all()
    completed = {item.lesson_id for item in completions}
    projects = {
        item.module_id: item for item in MLSpecializationProject.query.filter_by(
            user_id=current_user.id, pathway_id=pathway['id']
        ).all()
    }
    # ML starts with its own foundation module, so a learner can choose it
    # directly. Shared AI projects remain useful preparation but do not gate it.
    prerequisites_met = True
    ml_project_ids = {
        item.module_id for item in MLSpecializationProject.query.filter_by(
            user_id=current_user.id, pathway_id=pathway['id'], completed=True
        ).all()
    }
    ready_lessons = [
        lesson for lesson in machine_learning_lessons()
        if lesson.get('status') == 'ready'
    ]
    next_lesson_id = None
    if prerequisites_met:
        for lesson in ready_lessons:
            prior_modules = [
                module for module in pathway['modules']
                if module['number'] < lesson['module_number']
                and all(item.get('status') == 'ready' for item in module['lessons'])
            ]
            if any(module['id'] not in ml_project_ids for module in prior_modules):
                break
            if lesson['id'] not in completed:
                next_lesson_id = lesson['id']
                break
    module_progress = ml_module_progress(
        current_user.id, completed=completed, projects=projects
    )
    project_unlocked = {}
    for module in pathway['modules']:
        module_lessons = [lesson['id'] for lesson in module['lessons']]
        prior_modules = [
            item for item in pathway['modules']
            if item['number'] < module['number']
            and all(lesson.get('status') == 'ready' for lesson in item['lessons'])
        ]
        project_unlocked[module['id']] = bool(
            prerequisites_met
            and all(lesson.get('status') == 'ready' for lesson in module['lessons'])
            and set(module_lessons).issubset(completed)
            and all(item['id'] in ml_project_ids for item in prior_modules)
        )
    return render_template(
        'specializations/machine_learning.html',
        pathway=pathway, completed_ids=completed, prerequisites_met=prerequisites_met,
        module_progress=module_progress, project_unlocked=project_unlocked,
        next_lesson_id=next_lesson_id,
        pacing=ml_pathway_pacing(current_user.id),
    )


@main_bp.route('/specializations/machine-learning/lessons/<lesson_id>', methods=['GET', 'POST'])
@login_required
def machine_learning_lesson(lesson_id):
    pathway = machine_learning_pathway()
    lesson = get_machine_learning_lesson(lesson_id)
    if not lesson or lesson.get('status') != 'ready':
        abort(404)
    # One gate for the whole pathway: prior module projects and every earlier
    # published lesson in order.
    if not machine_learning_lesson_is_open(current_user.id, lesson_id):
        abort(403)

    completions = MLSpecializationLessonCompletion.query.filter_by(
        user_id=current_user.id, pathway_id=pathway['id']
    ).all()
    completed = {item.lesson_id for item in completions}

    if request.method == 'POST':
        try:
            selected = int(request.form.get('answer', '-1'))
        except (TypeError, ValueError):
            selected = -1
        existing = MLSpecializationLessonCompletion.query.filter_by(
            user_id=current_user.id, pathway_id=pathway['id'], lesson_id=lesson_id
        ).first()
        if selected != lesson['quiz']['answer']:
            # A miss here is the pathway equivalent of a failed course quiz
            # question: it returns through the spaced-review queue.
            record_pathway_review(current_user.id, lesson)
            flash('That answer needs another look. It has been added to your review queue.', 'error')
        else:
            if not existing:
                db.session.add(MLSpecializationLessonCompletion(
                    user_id=current_user.id, pathway_id=pathway['id'], lesson_id=lesson_id,
                ))
            from app.services.skill_passport import update_skill_progress_from_ml_lesson
            update_skill_progress_from_ml_lesson(
                current_user.id, lesson_id, commit=False,
            )
            db.session.commit()
            flash('Lesson complete. Your specialization progress has been saved.', 'success')
            return redirect(url_for('main.machine_learning_specialization'))

    existing = lesson_id in completed
    from app.models import LessonBookmark, LessonNote
    bookmark = LessonBookmark.query.filter_by(
        user_id=current_user.id, lesson_id=lesson_id
    ).first()
    note = LessonNote.query.filter_by(
        user_id=current_user.id, lesson_id=lesson_id
    ).first()
    from app.practice import pathway_exercises_for_lesson
    return render_template(
        'specializations/machine_learning_lesson.html',
        lesson=lesson, completed=existing,
        bookmarked=bookmark is not None,
        lesson_note=note.content if note else '',
        practice_exercises=pathway_exercises_for_lesson(lesson_id),
    )


@main_bp.route('/quizzes')
@login_required
def quizzes():
    from app.pathway_scope import destination_for, pathway_modules
    existing = {
        quiz.quiz_id: quiz
        for quiz in Quiz.query.filter(
            Quiz.quiz_id.like('dynamoai_lesson_%')
            | Quiz.quiz_id.like('dynamoai_module_%')
        ).all()
    }
    last_scores = {}
    for result in QuizResult.query.filter_by(user_id=current_user.id).order_by(
        QuizResult.taken_at.desc()
    ).limit(100).all():
        last_scores.setdefault(result.quiz_id, result.score)
    return render_template(
        'quizzes.html', config=get_effective_config_for_user(current_user),
        user=current_user, modules=pathway_modules(destination_for(current_user)),
        existing_quizzes=existing,
        last_scores=last_scores,
    )


@main_bp.route('/schedule')
@login_required
def schedule():
    from app.pathway_scope import (
        destination_for, lesson_by_id, pathway_modules,
    )
    destination = destination_for(current_user)
    progress = course_progress(current_user, destination=destination)
    upcoming_events = CalendarEvent.query.filter(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time >= datetime.now(timezone.utc),
        CalendarEvent.delete_pending.is_(False),
    ).order_by(CalendarEvent.start_time).limit(20).all()
    from app.google_calendar import resolve_timezone, stored_utc
    scheduled_events = [{
        'event': event,
        'start_local': stored_utc(event.start_time).astimezone(resolve_timezone(event.time_zone)),
        'end_local': stored_utc(event.end_time).astimezone(resolve_timezone(event.time_zone)),
    } for event in upcoming_events]
    # Resolved through the scoped catalog so an ML learner's next step can be a
    # pathway lesson, which has no ordinal in the AI curriculum.
    next_lesson = lesson_by_id(destination, progress['next_lesson_id'])
    return render_template('schedule.html', config=get_effective_config_for_user(current_user),
                           user=current_user, modules=pathway_modules(destination),
                           progress=progress,
                           upcoming_events=upcoming_events, scheduled_events=scheduled_events,
                           next_action=progress['next_action'],
                           next_lesson=next_lesson)


@main_bp.route('/progress')
@login_required
def progress():
    from datetime import datetime, timedelta, timezone
    from app.pathway_scope import (
        destination_for, is_ml, pathway_lessons, pathway_pace,
    )
    config = get_effective_config_for_user(current_user)
    completions = LessonCompletion.query.filter_by(
        user_id=current_user.id, completed=True
    ).all()
    dates = {item.completed_at.date() for item in completions if item.completed_at}
    streak = 0
    cursor = learner_today()
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
    recent_completions = sorted(
        completions, key=lambda item: item.completed_at or datetime.now(timezone.utc), reverse=True
    )[:8]
    completed = {item.lesson_id for item in completions}
    projects = CourseProject.query.filter_by(
        user_id=current_user.id, completed=True
    ).all()
    completed_project_ids = {item.module_id for item in projects}
    # The destination decides what this page counts: an ML learner's course is
    # the shared foundation plus their pathway, so the denominators, the module
    # grid, and the lesson titles beside recent activity all come from the
    # scoped catalog rather than the full AI course.
    destination = destination_for(current_user)
    if is_ml(destination):
        from app.pathway_scope import ml_completion_state
        ml_lessons, ml_projects = ml_completion_state(current_user.id)
        completed |= ml_lessons
        completed_project_ids |= ml_projects
    progress_data = course_progress(
        current_user, completed=completed,
        completed_projects=completed_project_ids, destination=destination
    )
    track = user_track(current_user)
    from app.leaderboard import leaderboard_data
    leaderboard_info = leaderboard_data(current_user)
    lesson_map = {
        lesson['id']: lesson for lesson in pathway_lessons(destination)
    }
    # A confirmed ML destination replaces the AI course's 12/10/5-month plan:
    # its course spans two manifests, so pace is derived from weekly hours over
    # the whole pathway instead of monthly milestones over modules 00-12.
    pace = pathway_pace(current_user.id, destination)
    milestones = (
        [] if pace else monthly_milestone_progress(
            progress_data, completed_project_ids, track
        )
    )
    return render_template('progress.html', config=config,
                           user=current_user, progress=progress_data,
                           analytics=analytics,
                           milestones=milestones,
                           pace=pace,
                           tracks=TRACKS, selected_track=track,
                           track_label=track_label(track),
                           leaderboard=leaderboard_info,
                           leaderboard_opted_in=leaderboard_info['opted_in'],
                           recent_completions=recent_completions,
                           recent_lessons={
                               item.lesson_id: lesson_map.get(item.lesson_id)
                               for item in recent_completions
                           },
                           pathway_destination=destination,
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


@main_bp.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    """Let learners privately report a bug or suggest an improvement."""
    if request.method == 'POST':
        category = (request.form.get('category') or '').strip()
        subject = (request.form.get('subject') or '').strip()
        message = (request.form.get('message') or '').strip()
        allowed_categories = {'bug', 'feature', 'content', 'other'}
        if category not in allowed_categories:
            flash('Choose a valid request type.', 'error')
        elif not 4 <= len(subject) <= 160:
            flash('Add a short subject (4–160 characters).', 'error')
        elif not 20 <= len(message) <= 5000:
            flash('Describe the issue or idea in 20–5,000 characters.', 'error')
        else:
            from app.rate_limit import enforce_rate_limit
            enforce_rate_limit('support-request-user', str(current_user.id))
            referrer = urlsplit(request.referrer or '')
            request_host = urlsplit(request.host_url).netloc
            page_path = (
                referrer.path[:500]
                if referrer.netloc == request_host and referrer.path.startswith('/')
                else None
            )
            report = SupportRequest(
                user_id=current_user.id,
                category=category,
                subject=subject,
                message=message,
                page_url=page_path,
            )
            db.session.add(report)
            db.session.commit()
            flash('Thanks for helping improve RUACH. Your request was sent to the support team.', 'success')
            return redirect(url_for('main.support'))
    reports = SupportRequest.query.filter_by(user_id=current_user.id).order_by(
        SupportRequest.created_at.desc()
    ).limit(10).all()
    return render_template('support.html', user=current_user, reports=reports)


@main_bp.route('/lesson/<lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = get_lesson(lesson_id)
    if not lesson:
        abort(404)
    from app.learning import completed_lesson_ids, completed_project_modules
    from app.practice import practice_exercises_for_lesson
    from app.pathway_scope import (
        destination_for, is_ml, lesson_by_id, pathway_lessons,
    )
    from app.models import VideoProgress, LessonBookmark, LessonNote
    completed = completed_lesson_ids(current_user)
    completed_projects = completed_project_modules(current_user)
    if not lesson_is_available(
        current_user, lesson_id, completed=completed, completed_projects=completed_projects
    ):
        abort(403)
    destination = destination_for(current_user)
    if is_ml(destination):
        from app.pathway_scope import ml_completion_state
        ml_lessons, ml_projects = ml_completion_state(current_user.id)
        completed |= ml_lessons
        completed_projects |= ml_projects
    video_progress = None
    if lesson.get('video'):
        video_progress = VideoProgress.query.filter_by(
            user_id=current_user.id, lesson_id=lesson_id
        ).first()
        if video_progress and video_progress.video_id != lesson['video']['id']:
            video_progress = None
    # Prev/next walk the scoped catalog, so the learner after the last
    # foundation lesson is offered the pathway's first lesson rather than a
    # module 03 lesson they cannot open.
    scoped = pathway_lessons(destination)
    position = next(
        (index for index, item in enumerate(scoped) if item['id'] == lesson_id),
        None,
    )
    previous_lesson = (
        scoped[position - 1] if position and position > 0 else None
    )
    next_lesson = (
        scoped[position + 1]
        if position is not None and position + 1 < len(scoped) else None
    )
    progress = course_progress(
        current_user, completed=completed, completed_projects=completed_projects,
        destination=destination
    )
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
                           setup_checks=SETUP_CHECKS,
                           setup_states=stored_setup_checks(current_user),
                           practice_exercises=practice_exercises_for_lesson(lesson_id),
                           next_lesson_id=progress['next_lesson_id'],
                           next_action=progress['next_action'],
                           projects_url=url_for('projects.project_page'),
                           video_progress=video_progress,
                           previous_lesson=previous_lesson,
                           next_lesson=next_lesson,
                           next_lesson_available=(
                               next_lesson is not None
                               and (
                                   next_lesson['id'] in completed
                                   or next_lesson['id'] == progress['next_lesson_id']
                               )
                           ),
                           total_lessons=len(scoped),
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
        if 'reminder_minutes' in calendar:
            reminders = calendar['reminder_minutes']
            # Consumers (app.google_calendar) expect a list of minute offsets;
            # Google allows at most five overrides per event.
            if (not isinstance(reminders, list) or len(reminders) > 5
                    or any(not isinstance(value, int) or isinstance(value, bool)
                           or not 0 <= value <= 40320 for value in reminders)):
                return jsonify({
                    'error': 'reminder_minutes must be a list of at most five '
                             'integers between 0 and 40320'
                }), 400
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
