"""RUACH application factory.

The factory initialises shared infrastructure, registers blueprints and hooks,
then returns the app. It intentionally contains no domain business logic:
configuration, logging, errors, security and response handling live in
``app.core``; domain rules live in ``app.domains`` / ``app.services``.
"""

from datetime import timedelta
import secrets

from flask import Flask, current_app, g, session

from app.core.config import (
    _is_production, _normalize_database_url, _running_on_vercel,
    configure_app, load_config, merge_config, validate_app_config,
)
from app.core.errors import register_error_handlers
from app.core.extensions import db, login_manager, migrate
from app.core.logging import configure_logging
from app.core.responses import register_response_hooks
from app.core.security import (
    is_api_path as _is_api_path,
    register_authentication,
    register_security_hooks,
)
from app.version import APP_VERSION

# Historical imports: existing modules import these helpers from :mod:`app`.
__all__ = [
    'APP_VERSION', 'db', 'login_manager', 'migrate',
    'create_app', 'validate_app_config', 'merge_config', 'load_config',
    '_is_api_path', '_is_production', '_normalize_database_url',
    '_running_on_vercel', 'hours_range', 'active_pathway_enrolments',
]


def hours_range(value):
    """Render an hour estimate as a friendly, rounded range.

    Course estimates are stored with one decimal place so pacing calculations
    stay precise, but learners should read "about 20–25 hours" rather than
    "22.6 hours". The bucket widens as the estimate grows.
    """
    if value in (None, ''):
        return '—'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number <= 0:
        return '0'
    step = 5 if number < 100 else 25 if number < 500 else 50
    low = int(number // step) * step
    high = low + step
    if low == number and high - low > 1:
        low = max(0, low - step)
    return f'{low:,}–{high:,}'


def active_pathway_enrolments():
    """Return active pathway enrolments for the signed-in learner.

    Thin compatibility wrapper around
    :func:`app.pathway_scope.active_pathway_enrolments`; the scope module owns
    the query, per-request cache, and ``User``/id normalisation.
    """
    from app.pathway_scope import active_pathway_enrolments as _enrolments

    return _enrolments()


def _signed_in_user_id():
    from flask_login import current_user

    if getattr(current_user, 'is_authenticated', False):
        return current_user.id
    return None


def _pathway_enrolments_for_templates():
    """Active enrolment rows for the signed-in learner (safe outside requests)."""
    if not _signed_in_user_id():
        return []
    try:
        return active_pathway_enrolments()
    except Exception:  # pragma: no cover - never let the shell fail on this
        current_app.logger.exception('Pathway enrolment lookup failed')
        return []


def _pathway_ids_for_templates():
    """Explicit pathway ids the learner can study, including legacy plans."""
    uid = _signed_in_user_id()
    if not uid:
        return set()
    try:
        from app.pathway_scope import pathway_ids_for
        return pathway_ids_for(uid)
    except Exception:  # pragma: no cover
        current_app.logger.exception('Pathway id lookup failed')
        return set()


def _pathway_destination_for_templates():
    uid = _signed_in_user_id()
    if not uid:
        return None
    try:
        from app.pathway_scope import destination_for
        return destination_for(uid)
    except Exception:  # pragma: no cover
        return None


def _foundation_evidence_for_templates():
    uid = _signed_in_user_id()
    if not uid:
        return {}

    def _lookup(user_id):
        from app.pathway_scope import foundation_evidence
        return foundation_evidence(user_id)

    return _lookup


def current_review_due_count():
    """Count of spaced-review items due now, cached per request.

    Feeds the Review Center badge in the shared shell. Hidden from admins,
    who do not see learner streaks either; failure-tolerant like the pathway
    read above so a hiccup never takes the shell down.
    """
    if hasattr(g, 'review_due_count'):
        return g.review_due_count
    count = 0
    from flask_login import current_user
    if getattr(current_user, 'is_authenticated', False) and not getattr(current_user, 'is_admin', False):
        try:
            from datetime import datetime, timezone
            from app.models import ReviewItem
            count = ReviewItem.query.filter_by(
                user_id=current_user.id, active=True
            ).filter(ReviewItem.due_at <= datetime.now(timezone.utc)).count()
        except Exception:
            current_app.logger.exception('Could not read review-due count')
            count = 0
    g.review_due_count = count
    return count


def current_notifications():
    """Derived shell notifications, cached per request like the review badge.

    Admins see none (matching the streak/review badge behaviour), and any
    failure yields an empty list so the shell never breaks over a badge.
    """
    if hasattr(g, 'notifications'):
        return g.notifications
    try:
        from app.services.notifications import build_notifications
        from flask_login import current_user
        g.notifications = build_notifications(current_user)
    except Exception:
        current_app.logger.exception('Could not build notifications')
        g.notifications = []
    return g.notifications


def _register_blueprints(app):
    """Register feature blueprints; HTTP ownership stays with each domain."""
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
    from app.leaderboard import rebuild_leaderboard_scores
    from app.routes.integrations import integrations_bp
    from app.routes.credentials import credentials_bp
    from app.routes.practice_arena import practice_arena_bp
    from app.routes.workspace import workspace_bp
    from app.routes.passport import passport_bp
    from app.routes.ml_specialization import ml_specialization_bp
    from app.routes.ai_specialization import ai_specialization_bp
    from app.routes.cloud_ai_infrastructure import cloud_ai_infrastructure_bp
    from app.routes.pathway_practice import pathway_practice_bp
    from app.routes.ai_jobs import ai_jobs_bp
    from app.routes.artifacts import artifacts_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_portal_bp, url_prefix='/admin')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    app.register_blueprint(lessons_bp, url_prefix='/api/lessons')
    app.register_blueprint(pathway_practice_bp, url_prefix='/api/pathways')
    app.register_blueprint(ai_jobs_bp, url_prefix='/api/ai')
    app.register_blueprint(artifacts_bp, url_prefix='/api/artifacts')
    app.register_blueprint(quizzes_bp, url_prefix='/api/quizzes')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(projects_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(leaderboard_bp)
    app.cli.add_command(rebuild_leaderboard_scores)
    from app.workers.ai_worker import register_ai_job_cli
    register_ai_job_cli(app)
    from app.services.judge_worker import register_judge_worker_cli
    register_judge_worker_cli(app)
    app.register_blueprint(integrations_bp, url_prefix='/api/integrations')
    app.register_blueprint(credentials_bp)
    app.register_blueprint(ml_specialization_bp)
    app.register_blueprint(ai_specialization_bp)
    app.register_blueprint(cloud_ai_infrastructure_bp)
    app.register_blueprint(practice_arena_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(passport_bp)


def create_app(config_override=None):
    """Build a configured RUACH Flask application."""
    flask_options = {
        'template_folder': '../templates',
        'static_folder': '../static',
    }
    import os
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

    configure_logging(app)
    configure_app(app, config_override)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    register_authentication(app, login_manager)

    _register_blueprints(app)
    register_security_hooks(app)
    register_error_handlers(app)
    register_response_hooks(app)

    app.jinja_env.filters['hours_range'] = hours_range
    from app.videos import format_duration
    from app.curriculum import readable_paragraphs
    app.jinja_env.filters['duration'] = format_duration
    app.jinja_env.filters['readable'] = readable_paragraphs

    @app.context_processor
    def inject_config():
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return {
            'config': app.config.get('APP_CONFIG', {}),
            'csrf_token': token,
            # Templates branch on enrolments, with legacy plan destinations
            # folded in so old accounts stay scoped.
            'pathway_enrolments': _pathway_enrolments_for_templates(),
            'pathway_ids': _pathway_ids_for_templates(),
            'pathway_destination': _pathway_destination_for_templates(),
            'foundation_evidence': _foundation_evidence_for_templates(),
            'review_due_count': current_review_due_count(),
            'notifications': current_notifications(),
            'google_calendar_oauth_configured': bool(
                app.config.get('GOOGLE_CLIENT_ID')
                and app.config.get('GOOGLE_CLIENT_SECRET')
            ),
            'app_version': APP_VERSION,
        }

    return app
