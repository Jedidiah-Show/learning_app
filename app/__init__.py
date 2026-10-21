from flask import Flask, jsonify, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import date, time
import hmac
import os
import re
import secrets
from copy import deepcopy
import yaml

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def validate_app_config(config):
    if not isinstance(config, dict):
        raise ValueError('Application configuration must be a YAML object')
    app_config = config.get('app')
    if not isinstance(app_config, dict):
        raise ValueError('Configuration must contain an app object')
    days = app_config.get('curriculum_days')
    if not isinstance(days, int) or isinstance(days, bool) or days != 90:
        raise ValueError('app.curriculum_days is fixed at 90')
    assessment_date = app_config.get('assessment_date')
    try:
        date.fromisoformat(str(assessment_date))
    except (TypeError, ValueError) as error:
        raise ValueError('app.assessment_date must be a valid ISO date') from error
    subjects = config.get('subjects')
    if not isinstance(subjects, list) or not subjects:
        raise ValueError('Configuration must contain at least one subject')
    subject_ids = set()
    for subject in subjects:
        if not isinstance(subject, dict):
            raise ValueError('Every subject must be an object')
        subject_id = subject.get('id')
        if not isinstance(subject_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,49}', subject_id):
            raise ValueError('Subject IDs must use lowercase letters, numbers, underscores, or hyphens')
        if subject_id in subject_ids:
            raise ValueError(f'Duplicate subject ID: {subject_id}')
        subject_ids.add(subject_id)
        if not isinstance(subject.get('name'), str) or not subject['name'].strip():
            raise ValueError(f'Subject {subject_id} must have a name')
        color = subject.get('color', '#6366f1')
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError(f'Subject {subject_id} color must be a six-digit hex value')
        if not isinstance(subject.get('icon', ''), str) or len(subject.get('icon', '')) > 10:
            raise ValueError(f'Subject {subject_id} icon must be a short string')
        topics = subject.get('topics', [])
        if not isinstance(topics, list) or any(not isinstance(topic, str) for topic in topics):
            raise ValueError(f'Subject {subject_id} topics must be a list')
    schedule = config.get('schedule')
    if (
        not isinstance(schedule, dict)
        or not isinstance(schedule.get('daily_blocks'), list)
        or not isinstance(schedule.get('unlock_rules'), dict)
        or not isinstance(schedule['unlock_rules'].get('require_all_subjects_complete'), bool)
        or not isinstance(schedule['unlock_rules'].get('allow_continue_after_day_complete'), bool)
    ):
        raise ValueError('schedule must contain daily_blocks and valid unlock_rules')
    if schedule.get('start_date') is not None:
        try:
            date.fromisoformat(schedule['start_date'])
        except (TypeError, ValueError) as error:
            raise ValueError('schedule.start_date must be a valid ISO date') from error
    for block in schedule['daily_blocks']:
        if not isinstance(block, dict) or not isinstance(block.get('name'), str) or not block['name'].strip():
            raise ValueError('Every schedule block must have a name')
        try:
            start = time.fromisoformat(block['start_time'])
            time.fromisoformat(block['end_time'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Schedule block times must be valid') from error
        if len(block['name']) > 120 or start.hour > 23:
            raise ValueError('Schedule block names must be 120 characters or fewer')
    quizzes = config.get('quizzes')
    if not isinstance(quizzes, dict):
        raise ValueError('Configuration must contain quiz settings')
    for quiz_name in ('end_of_day_quiz', 'end_of_week_quiz'):
        quiz = quizzes.get(quiz_name)
        if not isinstance(quiz, dict) or not isinstance(quiz.get('enabled'), bool):
            raise ValueError(f'quizzes.{quiz_name} must be an object')
        count = quiz.get('questions_per_subject')
        threshold = quiz.get('passing_threshold')
        if not isinstance(count, int) or isinstance(count, bool) or count < 1 or count > 100:
            raise ValueError(f'quizzes.{quiz_name}.questions_per_subject must be between 1 and 100')
        if not isinstance(threshold, int) or isinstance(threshold, bool) or not 0 <= threshold <= 100:
            raise ValueError(f'quizzes.{quiz_name}.passing_threshold must be between 0 and 100')
    calendar_config = config.get('google_calendar')
    if (
        not isinstance(calendar_config, dict)
        or not isinstance(calendar_config.get('enabled'), bool)
    ):
        raise ValueError('google_calendar must be an object')
    for key in ('calendar_id', 'event_prefix'):
        if not isinstance(calendar_config.get(key), str) or not calendar_config[key]:
            raise ValueError(f'google_calendar.{key} must be a non-empty string')
    reminders = calendar_config.get('reminder_minutes', [])
    if not isinstance(reminders, list) or any(
        not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 40320
        for value in reminders
    ):
        raise ValueError('google_calendar.reminder_minutes must contain valid minute values')
    generation = config.get('lesson_generation')
    if not isinstance(generation, dict):
        raise ValueError('lesson_generation must be an object')
    minutes = generation.get('estimated_minutes')
    if not isinstance(minutes, int) or isinstance(minutes, bool) or not 5 <= minutes <= 480:
        raise ValueError('lesson_generation.estimated_minutes must be between 5 and 480')
    for key in ('include_code_examples', 'include_pitfalls', 'include_self_checks', 'difficulty_progression'):
        if key in generation and not isinstance(generation[key], bool):
            raise ValueError(f'lesson_generation.{key} must be a boolean')
    progress = config.get('progress')
    if not isinstance(progress, dict) or any(
        not isinstance(progress.get(key), bool)
        for key in ('track_streaks', 'track_time_spent')
    ):
        raise ValueError('progress must contain boolean tracking preferences')
    ai = config.get('ai')
    if not isinstance(ai, dict):
        raise ValueError('ai must be an object')
    if ai.get('model_tier') not in {'flash', 'pro'}:
        raise ValueError('ai.model_tier must be flash or pro')
    for key in ('flash_model', 'pro_model'):
        if not isinstance(ai.get(key), str) or not re.fullmatch(
            r'[A-Za-z0-9._-]+', ai[key]
        ):
            raise ValueError(f'ai.{key} must be a valid Gemini model name')
    learning = config.get('learning')
    if (
        not isinstance(learning, dict)
        or learning.get('target_proficiency') not in {
            'Novice', 'Beginner', 'Intermediate', 'Advanced', 'Expert'
        }
    ):
        raise ValueError('learning.target_proficiency must be a proficiency level')
    assessment = config.get('proficiency_assessment')
    question_count = assessment.get('questions_per_subject') if isinstance(assessment, dict) else None
    if (
        not isinstance(question_count, int) or isinstance(question_count, bool)
        or not 5 <= question_count <= 100 or question_count % 5
    ):
        raise ValueError(
            'proficiency_assessment.questions_per_subject must be a multiple of 5 between 5 and 100'
        )
    thresholds = assessment.get('proficiency_thresholds', {})
    if (
        not isinstance(thresholds, dict)
        or set(thresholds) != {'Beginner', 'Intermediate', 'Advanced', 'Expert'}
        or any(
            not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100
            for value in thresholds.values()
        )
        or not (
            thresholds['Beginner'] < thresholds['Intermediate']
            < thresholds['Advanced'] < thresholds['Expert']
        )
    ):
        raise ValueError('proficiency_assessment thresholds must increase from 0 to 100')
    return config


def merge_config(base, overrides):
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'default_config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return validate_app_config(config)

def create_app(config_override=None):
    flask_options = {
        'template_folder': '../templates',
        'static_folder': '../static',
    }
    if (
        os.environ.get('VERCEL')
        or os.environ.get('VERCEL_ENV')
        or os.path.isdir('/var/task')
    ):
        # Vercel's deployment bundle is read-only; Flask-SQLAlchemy creates
        # the instance directory during initialization, so keep it in /tmp.
        flask_options['instance_path'] = os.environ.get(
            'FLASK_INSTANCE_PATH', '/tmp/learning_app_instance'
        )
    app = Flask(__name__, **flask_options)
    
    # Config
    # Never use a public, hard-coded Flask signing key for account sessions.
    # Set SECRET_KEY in the environment to keep sessions valid across restarts.
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace(
                'postgres://', 'postgresql+psycopg://', 1
            )
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace(
                'postgresql://', 'postgresql+psycopg://', 1
            )
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        database_url or 'sqlite:///../data/learning_app.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['GEMINI_API_KEY'] = (
        os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    )
    app.config['GEMINI_FLASH_MODEL'] = os.environ.get(
        'GEMINI_FLASH_MODEL', 'gemini-3.8-flash'
    )
    app.config['GEMINI_PRO_MODEL'] = os.environ.get(
        'GEMINI_PRO_MODEL', 'gemini-3.1-pro-preview'
    )
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Authentication required'}), 401
        return redirect(url_for('auth.login', next=request.url))
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return User.query.get(int(user_id))
    
    # Load app config
    app.config['APP_CONFIG'] = load_config()
    if config_override is not None:
        if not isinstance(config_override, dict):
            raise ValueError('config_override must be an object')
        app.config['APP_CONFIG'] = merge_config(app.config['APP_CONFIG'], config_override)
        validate_app_config(app.config['APP_CONFIG'])
    app.config['GEMINI_FLASH_MODEL'] = os.environ.get(
        'GEMINI_FLASH_MODEL',
        app.config['APP_CONFIG'].get('ai', {}).get(
            'flash_model', 'gemini-3.8-flash'
        ),
    )
    app.config['GEMINI_PRO_MODEL'] = os.environ.get(
        'GEMINI_PRO_MODEL',
        app.config['APP_CONFIG'].get('ai', {}).get(
            'pro_model', 'gemini-3.1-pro-preview'
        ),
    )
    # Load Google OAuth credentials from env or config
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID') or app.config['APP_CONFIG'].get('google_client_id') or app.config['APP_CONFIG'].get('GOOGLE_CLIENT_ID') or (app.config['APP_CONFIG'].get('google_calendar') or {}).get('client_id')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET') or app.config['APP_CONFIG'].get('google_client_secret') or app.config['APP_CONFIG'].get('GOOGLE_CLIENT_SECRET') or (app.config['APP_CONFIG'].get('google_calendar') or {}).get('client_secret')
    app.config['GOOGLE_REDIRECT_URI'] = os.environ.get('GOOGLE_REDIRECT_URI') or app.config['APP_CONFIG'].get('google_redirect_uri') or app.config['APP_CONFIG'].get('GOOGLE_REDIRECT_URI') or (app.config['APP_CONFIG'].get('google_calendar') or {}).get('redirect_uri')
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.progress import progress_bp
    from app.routes.lessons import lessons_bp
    from app.routes.quizzes import quizzes_bp
    from app.routes.calendar import calendar_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    app.register_blueprint(lessons_bp, url_prefix='/api/lessons')
    app.register_blueprint(quizzes_bp, url_prefix='/api/quizzes')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(projects_bp)

    @app.before_request
    def require_subject_setup():
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and not app.testing:
            token = session.get('_csrf_token')
            supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not token or not supplied or not hmac.compare_digest(token, supplied):
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'CSRF validation failed'}), 400
                return 'CSRF validation failed', 400
        from flask_login import current_user
        if not current_user.is_authenticated:
            return None
        endpoint = request.endpoint or ''
        setup_endpoints = {
            'main.subject_configuration',
            'main.proficiency_test_selection',
            'main.take_proficiency_test',
        }
        if endpoint.startswith('auth.') or endpoint in setup_endpoints or endpoint == 'static':
            return None

        from app.models import UserSubjectConfig
        from app.user_subjects import get_effective_subjects_for_user
        subjects = get_effective_subjects_for_user(current_user)
        configs = {
            item.subject_id: item
            for item in UserSubjectConfig.query.filter_by(user_id=current_user.id).all()
        }
        setup_complete = current_user.subjects_configured and all(
            subject['id'] in configs for subject in subjects
        )
        if setup_complete:
            setup_complete = all(
                config.proficiency == 'Novice' or config.tested
                for config in (configs[subject['id']] for subject in subjects)
            )
        if setup_complete:
            return None
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Complete subject configuration and proficiency assessments first',
                'next': url_for(
                    'main.proficiency_test_selection'
                    if current_user.subjects_configured
                    else 'main.subject_configuration'
                ),
            }), 403
        return redirect(url_for(
            'main.proficiency_test_selection'
            if current_user.subjects_configured
            else 'main.subject_configuration'
        ))
    
    # Make config available to all templates
    @app.context_processor
    def inject_config():
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return {
            'config': app.config.get('APP_CONFIG', {}),
            'csrf_token': token,
            'google_calendar_oauth_configured': bool(
                app.config.get('GOOGLE_CLIENT_ID')
                and app.config.get('GOOGLE_CLIENT_SECRET')
            ),
        }
    
    return app
