"""Configuration loading and validation for the RUACH modular monolith.

All environment/YAML wiring used to live inside ``create_app``.  It is kept
here so the application factory only initialises infrastructure and registers
components.  Legacy helper names are preserved because existing modules import
them from :mod:`app`; ``app/__init__.py`` re-exports them.
"""

from copy import deepcopy
from datetime import date, time, timedelta
from functools import lru_cache
from urllib.parse import urlsplit
import json
import os
import re

import yaml
from werkzeug.middleware.proxy_fix import ProxyFix

from app.version import APP_VERSION  # noqa: F401  (re-exported via app)


@lru_cache(maxsize=1)
def _bundled_lesson_count():
    """Count lessons from the bundled manifest without importing curriculum code.

    Configuration is cross-cutting infrastructure; reading the immutable source
    data here keeps ``app.core`` independent of the curriculum domain.
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'dynamoai_curriculum.json',
    )
    with open(path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    return sum(len(module.get('lessons') or []) for module in data.get('modules') or [])


def validate_app_config(config):
    if not isinstance(config, dict):
        raise ValueError('Application configuration must be a YAML object')
    app_config = config.get('app')
    if not isinstance(app_config, dict):
        raise ValueError('Configuration must contain an app object')
    days = app_config.get('curriculum_days')
    expected_days = _bundled_lesson_count()
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
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'config',
        'default_config.yaml',
    )
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return validate_app_config(config)


def running_on_vercel():
    return bool(
        os.environ.get('VERCEL')
        or os.environ.get('VERCEL_ENV')
        or os.path.isdir('/var/task')
    )


def is_production():
    """Return True for Vercel, Render, or an explicit production environment."""
    return bool(
        os.environ.get('APP_ENV', '').lower() == 'production'
        or os.environ.get('FLASK_ENV', '').lower() == 'production'
        or os.environ.get('RENDER')
        or running_on_vercel()
    )


def normalize_database_url(database_url, production):
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


# Historical private names, kept for compatibility with existing imports.
_running_on_vercel = running_on_vercel
_is_production = is_production
_normalize_database_url = normalize_database_url


def configure_app(app, config_override=None):
    """Populate ``app.config`` from environment and the bundled YAML config.

    Returns ``(production, running_on_vercel)`` so the factory can decide
    whether to install the reverse-proxy middleware before configuration.
    """
    production = is_production()
    on_vercel = running_on_vercel()
    if production:
        # Vercel terminates TLS and forwards the original scheme in
        # X-Forwarded-Proto. Without ProxyFix, url_for(_external=True) can
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
    app.config['SECRET_KEY'] = secret_key or os.urandom(32)
    app.config['TOKEN_ENCRYPTION_KEY'] = os.environ.get('TOKEN_ENCRYPTION_KEY')
    # A web deployment must opt in only after its separate judge worker and
    # container sandbox have been provisioned.
    app.config['JUDGE_SUBMISSIONS_ENABLED'] = (
        os.environ.get('JUDGE_SUBMISSIONS_ENABLED', '').strip().lower()
        in {'1', 'true', 'yes'}
    )
    # M3 execution controls. A pinned tag is the default; operators may supply
    # a digest-pinned value such as ruach-python-sandbox@sha256:...
    app.config['SANDBOX_IMAGE'] = (
        os.environ.get('SANDBOX_IMAGE') or 'ruach-python-sandbox:3.12-v1'
    )
    for name, default in (
        ('SANDBOX_MAX_CONCURRENCY_PER_USER', 2),
        ('SANDBOX_SUBMISSION_LIMIT_PER_MINUTE', 10),
    ):
        try:
            value = int(os.environ.get(name, str(default)))
        except (TypeError, ValueError):
            value = default
        app.config[name] = value if value > 0 else default
    app.config['ARTIFACT_STORAGE_DIR'] = (
        os.environ.get('ARTIFACT_STORAGE_DIR') or os.path.join(app.instance_path, 'artifacts')
    )
    app.config['ARTIFACT_MAX_BYTES'] = 25 * 1024 * 1024
    app.config['MLFLOW_TRACKING_URI'] = os.environ.get('MLFLOW_TRACKING_URI') or ''
    app.config['MLFLOW_EXPERIMENT_PREFIX'] = (
        os.environ.get('MLFLOW_EXPERIMENT_PREFIX') or 'ruach'
    )
    if production and not app.config['TOKEN_ENCRYPTION_KEY']:
        # Deriving the Fernet key from SECRET_KEY would silently invalidate
        # stored OAuth refresh tokens whenever SECRET_KEY rotates.
        raise RuntimeError(
            'TOKEN_ENCRYPTION_KEY must be configured in production'
        )

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
    database_url = normalize_database_url(database_url, production)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        database_url or 'sqlite:///../data/learning_app.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if database_url and database_url.startswith('postgresql+psycopg://'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '300')),
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
        'OPENROUTER_APP_NAME', 'RUACH AI & ML Engineering'
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
    app.config['AI_CACHE_ENABLED'] = os.environ.get(
        'AI_CACHE_ENABLED', 'false'
    ).strip().lower() in {'1', 'true', 'yes'}
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL', '').strip()

    def _json_config(name):
        raw = os.environ.get(name)
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    # M2: central task routing and operator-supplied model prices. Model names
    # and prices are never hardcoded in routes or the gateway.
    app.config['AI_TASK_ROUTES'] = _json_config('AI_TASK_ROUTES')
    app.config['AI_MODEL_COSTS'] = _json_config('AI_MODEL_COSTS')
    app.config['AI_PROMPT_VERSION_OVERRIDES'] = _json_config(
        'AI_PROMPT_VERSION_OVERRIDES'
    )

    app.config['APP_CONFIG'] = load_config()
    if config_override is not None:
        if not isinstance(config_override, dict):
            raise ValueError('config_override must be an object')
        app.config['APP_CONFIG'] = merge_config(
            app.config['APP_CONFIG'], config_override
        )
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
    app_config = app.config['APP_CONFIG']
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID') or app_config.get('google_client_id') or app_config.get('GOOGLE_CLIENT_ID') or (app_config.get('google_calendar') or {}).get('client_id')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET') or app_config.get('google_client_secret') or app_config.get('GOOGLE_CLIENT_SECRET') or (app_config.get('google_calendar') or {}).get('client_secret')
    app.config['GOOGLE_REDIRECT_URI'] = os.environ.get('GOOGLE_REDIRECT_URI') or app_config.get('google_redirect_uri') or app_config.get('GOOGLE_REDIRECT_URI') or (app_config.get('google_calendar') or {}).get('redirect_uri')

    if production and app.config['STORAGE_BACKEND'] != 's3':
        app.logger.warning(
            'STORAGE_BACKEND is %r; production uploads should use the S3 '
            'backend because Render disk is ephemeral.',
            app.config['STORAGE_BACKEND'],
        )
    # Log configuration *presence*, never keys or secrets.
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
    return production, on_vercel
