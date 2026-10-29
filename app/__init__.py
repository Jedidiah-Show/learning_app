from flask import Flask, jsonify, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from datetime import date, time, timedelta
import hmac
import os
import re
import secrets
from copy import deepcopy
from urllib.parse import urlsplit
import yaml
from werkzeug.middleware.proxy_fix import ProxyFix

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
    from app.curriculum import all_lessons
    expected_days = len(all_lessons())
    if not isinstance(days, int) or isinstance(days, bool) or days != expected_days:
        raise ValueError(
            'app.curriculum_days must match the bundled '
            f'{expected_days}-lesson RUACH engineering course'
        )
    schedule = config.get('schedule')
    if not isinstance(schedule, dict) or not isinstance(schedule.get('daily_blocks'), list):
        raise ValueError('schedule must contain daily_blocks')
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
    count = quizzes.get('questions_per_quiz')
    threshold = quizzes.get('passing_threshold')
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 30:
        raise ValueError('quizzes.questions_per_quiz must be between 1 and 30')
    if not isinstance(threshold, int) or isinstance(threshold, bool) or not 0 <= threshold <= 100:
        raise ValueError('quizzes.passing_threshold must be between 0 and 100')
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


def _running_on_vercel():
    return bool(
        os.environ.get('VERCEL')
        or os.environ.get('VERCEL_ENV')
        or os.path.isdir('/var/task')
    )


def _is_production():
    """Return True for Vercel, Render, or an explicit production environment."""
    return bool(
        os.environ.get('APP_ENV', '').lower() == 'production'
        or os.environ.get('FLASK_ENV', '').lower() == 'production'
        or os.environ.get('RENDER')
        or _running_on_vercel()
    )


def _normalize_database_url(database_url, production):
    """Use Psycopg 3 and require TLS for external Postgres in production."""
    if not database_url:
        return database_url
    parsed = urlsplit(database_url)
    host = (parsed.hostname or '').lower()
    if database_url.startswith('postgres://'):
        database_url = 'postgresql+psycopg://' + database_url[len('postgres://'):]
    elif database_url.startswith('postgresql://'):
        database_url = 'postgresql+psycopg://' + database_url[len('postgresql://'):]
    local_host = host in {'localhost', '127.0.0.1', '::1'}
    if (
        production
        and database_url.startswith('postgresql+psycopg://')
        and not local_host
        and 'sslmode=' not in database_url
    ):
        database_url += ('&' if '?' in database_url else '?') + 'sslmode=require'
    return database_url


def create_app(config_override=None):
    flask_options = {
        'template_folder': '../templates',
        'static_folder': '../static',
    }
    running_on_vercel = _running_on_vercel()
    if running_on_vercel:
        # Vercel's deployment bundle is read-only; Flask-SQLAlchemy creates
        # the instance directory during initialization, so keep it in /tmp.
        flask_options['instance_path'] = os.environ.get(
            'FLASK_INSTANCE_PATH', '/tmp/learning_app_instance'
        )
    app = Flask(__name__, **flask_options)
    
    # Config
    production = _is_production()
    if production:
        # Vercel terminates TLS and forwards the original scheme in
        # X-Forwarded-Proto.  Without ProxyFix, url_for(_external=True) can
        # generate an http:// OAuth callback even though the app is served
        # over HTTPS.
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
        )
        app.config['PREFERRED_URL_SCHEME'] = os.environ.get(
            'PREFERRED_URL_SCHEME', 'https'
        )
    secret_key = os.environ.get('SECRET_KEY')
    if production and not secret_key:
        raise RuntimeError('SECRET_KEY must be configured in production')
    # Never use a public, hard-coded Flask signing key for account sessions.
    # Set SECRET_KEY in the environment to keep sessions valid across restarts.
    app.config['SECRET_KEY'] = secret_key or os.urandom(32)
    app.config['TOKEN_ENCRYPTION_KEY'] = os.environ.get('TOKEN_ENCRYPTION_KEY')
    # Allow multipart framing around the separately enforced 2 MiB photo cap.
    app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=production,
        SESSION_COOKIE_SAMESITE='Lax',
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=production,
        REMEMBER_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    )
    from werkzeug.exceptions import RequestEntityTooLarge

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'File is too large. Maximum size is 2MB.'}), 413
        flash('Profile photo is too large. Maximum size is 2MB.', 'error')
        return redirect(url_for('auth.profile'))
    database_url = next((
        os.environ.get(key)
        for key in (
            'DATABASE_URL',
            'POSTGRES_URL',
            'POSTGRES_URL_NON_POOLING',
            'DATABASE_URL_UNPOOLED',
        )
        if os.environ.get(key)
    ), None)
    if production and not database_url:
        raise RuntimeError(
            'A persistent PostgreSQL URL is required in production. Configure '
            'DATABASE_URL (or POSTGRES_URL) in the Render environment. The '
            'SQLite fallback is for local development only.'
        )
    database_url = _normalize_database_url(database_url, production)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        database_url or 'sqlite:///../data/learning_app.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if database_url and database_url.startswith('postgresql+psycopg://'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '300')),
            # Each of Render's two gunicorn workers can open a pool of
            # pool_size + max_overflow connections (four by default), for up
            # to eight app connections total. Keep this budget explicit so
            # Neon connection limits stay healthy.
            'pool_size': int(os.environ.get('DB_POOL_SIZE', '2')),
            'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '2')),
            'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', '30')),
            'connect_args': {
                'connect_timeout': int(os.environ.get('DB_CONNECT_TIMEOUT', '10')),
                'application_name': os.environ.get(
                    'DB_APPLICATION_NAME', 'ruach-learning-app'
                ),
            },
        }
    elif database_url and database_url.startswith('sqlite'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {'timeout': 30},
        }
    app.config['GEMINI_API_KEY'] = (
        os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    )
    app.config['GEMINI_FLASH_MODEL'] = os.environ.get(
        'GEMINI_FLASH_MODEL', 'gemini-3.8-flash'
    )
    app.config['GEMINI_PRO_MODEL'] = os.environ.get(
        'GEMINI_PRO_MODEL', 'gemini-3.1-pro-preview'
    )
    app.config['OPENROUTER_API_KEY'] = os.environ.get('OPENROUTER_API_KEY')
    app.config['OPENROUTER_BASE_URL'] = (
        os.environ.get('OPENROUTER_BASE_URL')
        or 'https://openrouter.ai/api/v1'
    )
    app.config['OPENROUTER_FLASH_MODEL'] = (
        os.environ.get('OPENROUTER_FLASH_MODEL')
        or os.environ.get('OPENROUTER_MODEL')
        or 'openrouter/auto'
    )
    app.config['OPENROUTER_PRO_MODEL'] = (
        os.environ.get('OPENROUTER_PRO_MODEL')
        or os.environ.get('OPENROUTER_MODEL')
        or 'openrouter/auto'
    )
    app.config['OPENROUTER_APP_NAME'] = os.environ.get(
        'OPENROUTER_APP_NAME', 'RUACH AI Engineering'
    )
    app.config['OPENROUTER_SITE_URL'] = os.environ.get('OPENROUTER_SITE_URL')
    app.config['STORAGE_BACKEND'] = (
        os.environ.get('STORAGE_BACKEND', 'local').strip().lower() or 'local'
    )
    app.config['S3_ENDPOINT_URL'] = os.environ.get('S3_ENDPOINT_URL')
    app.config['S3_BUCKET'] = os.environ.get('S3_BUCKET')
    app.config['S3_REGION'] = os.environ.get('S3_REGION', 'auto')
    app.config['S3_ACCESS_KEY_ID'] = os.environ.get('S3_ACCESS_KEY_ID')
    app.config['S3_SECRET_ACCESS_KEY'] = os.environ.get('S3_SECRET_ACCESS_KEY')
    app.config['S3_PUBLIC_BASE_URL'] = (
        os.environ.get('S3_PUBLIC_BASE_URL') or ''
    ).rstrip('/')
    if production and app.config['STORAGE_BACKEND'] != 's3':
        app.logger.warning(
            'STORAGE_BACKEND is %r; production uploads should use the S3 '
            'backend because Render disk is ephemeral.',
            app.config['STORAGE_BACKEND'],
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
            try:
                user = db.session.get(User, int(user_id))
            except (ValueError, TypeError):
                try:
                    user = db.session.execute(
                        db.select(User).filter_by(id=int(user_id))
                    ).scalar_one_or_none()
                except Exception:
                    user = None
        except Exception:
            try:
                session.clear()
            except Exception:
                pass
            return None
        if user is None:
            return None
        if not getattr(user, 'is_active', True):
            try:
                session.clear()
            except Exception:
                pass
            return None
        try:
            session_version = int(session.get('auth_version'))
        except (TypeError, ValueError):
            session_version = None
        try:
            if session_version is None or session_version != int(user.auth_version or 0):
                session.clear()
                return None
        except Exception:
            try:
                session.clear()
            except Exception:
                pass
            return None
        return user
    
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
    app.logger.info(
        'Integration config: Gemini=%s (%s / %s), OpenRouter=%s (%s / %s), '
        'Google OAuth=%s, Calendar redirect URI=%s',
        bool(app.config.get('GEMINI_API_KEY')),
        app.config.get('GEMINI_FLASH_MODEL'),
        app.config.get('GEMINI_PRO_MODEL'),
        bool(app.config.get('OPENROUTER_API_KEY')),
        app.config.get('OPENROUTER_FLASH_MODEL'),
        app.config.get('OPENROUTER_PRO_MODEL'),
        bool(app.config.get('GOOGLE_CLIENT_ID')
             and app.config.get('GOOGLE_CLIENT_SECRET')),
        app.config.get('GOOGLE_REDIRECT_URI') or 'derived from request',
    )
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.progress import progress_bp
    from app.routes.lessons import lessons_bp
    from app.routes.quizzes import quizzes_bp
    from app.routes.calendar import calendar_bp
    from app.routes.admin import admin_bp
    from app.routes.admin_portal import admin_portal_bp
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.community import community_bp
    from app.routes.leaderboard import leaderboard_bp
    from app.routes.integrations import integrations_bp
    from app.routes.credentials import credentials_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_portal_bp, url_prefix='/admin')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    app.register_blueprint(lessons_bp, url_prefix='/api/lessons')
    app.register_blueprint(quizzes_bp, url_prefix='/api/quizzes')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(projects_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(integrations_bp, url_prefix='/api/integrations')
    app.register_blueprint(credentials_bp)
    @app.before_request
    def enforce_csrf_protection():
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and not app.testing:
            token = session.get('_csrf_token')
            supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not token or not supplied or not hmac.compare_digest(token, supplied):
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'CSRF validation failed'}), 400
                return 'CSRF validation failed', 400
        # Learners enter the fixed course immediately; the old subject and
        # proficiency setup tables remain available for legacy records only.
        return None

    from app.gemini import GeminiRateLimitExceeded
    from app.rate_limit import RateLimitExceeded, rate_limit_response

    @app.errorhandler(GeminiRateLimitExceeded)
    def gemini_rate_limit_exceeded(error):
        response = jsonify({'error': str(error)})
        response.status_code = 429
        response.headers['Retry-After'] = str(error.retry_after)
        response.headers['X-RateLimit-Remaining'] = '0'
        return response

    @app.errorhandler(RateLimitExceeded)
    def request_rate_limit_exceeded(error):
        return rate_limit_response(error)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault(
            'Referrer-Policy', 'strict-origin-when-cross-origin'
        )
        response.headers.setdefault(
            'Permissions-Policy',
            'camera=(), microphone=(), geolocation=(), payment=()',
        )
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault(
            'Cross-Origin-Resource-Policy', 'same-origin'
        )
        response.headers.setdefault('X-Powered-By', 'RUACH')
        if request.path.startswith('/static/pyodide/'):
            # The practice iframe is sandboxed to an opaque origin. Permit its
            # worker to import the self-hosted Pyodide runtime and WebAssembly.
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
            response.headers['Cache-Control'] = (
                'public, max-age=31536000, immutable'
            )
        elif request.path == '/static/js/practice-sandbox.js':
            # The sandboxed iframe has an opaque origin, so its public runner
            # script must be embeddable despite the app-wide same-origin policy.
            response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        # Keep the policy report-only until the remaining inline scripts and
        # styles are migrated to nonces/hashed files.  Report-only still makes
        # violations visible without breaking existing lessons or YouTube.
        response.headers.setdefault(
            'Content-Security-Policy-Report-Only',
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'self'; "
            "form-action 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://www.youtube.com https://www.youtube-nocookie.com "
            "https://www.gstatic.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https://i.ytimg.com https://*.ytimg.com; "
            "font-src 'self' data:; "
            "frame-src 'self' https://www.youtube.com "
            "https://www.youtube-nocookie.com; "
            "connect-src 'self';",
        )
        return response

    from app.videos import format_duration
    from app.curriculum import readable_paragraphs
    app.jinja_env.filters['duration'] = format_duration
    app.jinja_env.filters['readable'] = readable_paragraphs

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
            'app_version': '1.0.0',
        }
    
    return app
