"""Consistent HTML/JSON error handling for the whole application."""

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    EntityNotFoundError,
    RuachDomainError,
    ValidationError,
    WorkloadExecutionError,
)
from app.core.responses import json_error
from app.core.security import is_api_path


def register_error_handlers(app):
    """Register all application error handlers once, during factory setup."""

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(error):
        if is_api_path(request.path):
            return json_error('File is too large. Maximum size is 2MB.', 413)
        flash('Profile photo is too large. Maximum size is 2MB.', 'error')
        return redirect(url_for('auth.profile'))

    # Imported lazily: provider modules re-export infrastructure helpers from
    # :mod:`app`, so importing them at module scope would create a cycle.
    from app.gemini import GeminiRateLimitExceeded
    from app.rate_limit import RateLimitExceeded, rate_limit_response

    @app.errorhandler(GeminiRateLimitExceeded)
    def gemini_rate_limit_exceeded(error):
        response = json_error(str(error), 429)
        response.headers['Retry-After'] = str(error.retry_after)
        response.headers['X-RateLimit-Remaining'] = '0'
        return response

    @app.errorhandler(RateLimitExceeded)
    def request_rate_limit_exceeded(error):
        return rate_limit_response(error)

    def error_page(status, title, message, next_url, next_label,
                   secondary_url=None, secondary_label=None):
        return render_template(
            f'error/{status}.html',
            blocker_title=title,
            blocker_message=message,
            next_url=next_url,
            next_label=next_label,
            secondary_url=secondary_url,
            secondary_label=secondary_label,
        ), status

    @app.errorhandler(EntityNotFoundError)
    def handle_entity_not_found(error):
        if is_api_path(request.path):
            return json_error(error.message, 404)
        return error_page(
            404, 'We could not find that item', error.message,
            url_for('main.index'), 'Go to your dashboard',
            url_for('main.lessons'), 'Browse all lessons',
        )

    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(error):
        if is_api_path(request.path):
            return json_error(error.message, 403)
        return error_page(
            403, 'Action not permitted', error.message,
            url_for('main.index'), 'Back to your dashboard',
            url_for('main.support'), 'Ask for help',
        )

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        if is_api_path(request.path):
            return json_error(error.message, 400)
        flash(error.message, 'error')
        return redirect(request.referrer or url_for('main.index'))

    @app.errorhandler(ConflictError)
    def handle_conflict_error(error):
        if is_api_path(request.path):
            return json_error(error.message, 409)
        flash(error.message, 'error')
        return redirect(request.referrer or url_for('main.index'))

    @app.errorhandler(WorkloadExecutionError)
    def handle_workload_execution_error(error):
        current_app.logger.warning('Workload execution error on %s: %s (profile: %s)',
                                   request.path, error.message, error.profile)
        if is_api_path(request.path):
            return json_error(error.message, 503)
        return error_page(
            500, 'Workload execution failed',
            error.message or 'The requested computational workload could not be completed. Please try again shortly.',
            url_for('main.index'), 'Back to your dashboard',
            url_for('main.support'), 'Tell support',
        )

    @app.errorhandler(RuachDomainError)
    def handle_generic_domain_error(error):
        current_app.logger.warning('Domain error on %s: %s', request.path, error.message)
        if is_api_path(request.path):
            return json_error(error.message, 400)
        flash(error.message, 'error')
        return redirect(request.referrer or url_for('main.index'))

    @app.errorhandler(403)
    def forbidden(error):
        if is_api_path(request.path):
            message = getattr(error, 'description', None) or (
                'You do not have access to this resource.'
            )
            return json_error(message, 403)
        message = getattr(error, 'description', None)
        if not message or message == 'You don\'t have the permission to access the requested resource. It is either read-protected or not readable by the server.':
            message = 'This page is locked for your account.'
        if request.path.startswith('/lesson/'):
            lesson_id = request.path.rstrip('/').rsplit('/', 1)[-1]
            from app.curriculum import get_lesson
            lesson = get_lesson(lesson_id)
            title = f'Lesson {lesson_id} is locked'
            message = (
                'Complete the earlier lessons and the module project before '
                'this lesson. Lessons unlock in course order, and module '
                'projects are never skipped.'
            )
            if lesson:
                title = f'“{lesson["title"]}” is locked'
            return error_page(
                403, title, message,
                url_for('main.lessons'), 'See the lesson order',
                url_for('projects.project_page'), 'Check module projects',
            )
        if request.path.startswith('/specializations/machine-learning/lessons/'):
            lesson_id = request.path.rstrip('/').rsplit('/', 1)[-1]
            from app.ml_pathway import get_machine_learning_lesson
            lesson = get_machine_learning_lesson(lesson_id)
            title = 'That pathway lesson is locked'
            message = (
                'Work through the earlier ML pathway lessons and module '
                'projects before this one opens. Pathway lessons unlock in '
                'order, and module projects are never skipped.'
            )
            if lesson:
                title = f'“{lesson["title"]}” is locked'
            return error_page(
                403, title, message,
                url_for('main.machine_learning_specialization'), 'See the pathway',
                url_for('projects.project_page'), 'Check module projects',
            )
        return error_page(
            403, 'This page is locked', message,
            url_for('main.index'), 'Back to your dashboard',
            url_for('main.support'), 'Ask for help',
        )

    @app.errorhandler(404)
    def not_found(error):
        if is_api_path(request.path):
            return json_error('Not found', 404)
        message = 'The page may have moved, or the link may be incomplete.'
        if request.path.startswith('/lesson/'):
            message = 'That lesson does not exist in the current curriculum.'
        return error_page(
            404, 'We could not find that page', message,
            url_for('main.index'), 'Go to your dashboard',
            url_for('main.lessons'), 'Browse all lessons',
        )

    @app.errorhandler(500)
    def internal_error(error):
        current_app.logger.error('Unhandled error on %s: %s', request.path, error)
        if is_api_path(request.path):
            return json_error(
                'Something went wrong on our side. Please try again.', 500
            )
        return error_page(
            500, 'Something broke on our side',
            'Your progress is safe — nothing has been lost. Try again in a moment; if it keeps happening, tell support and include the page you were on.',
            url_for('main.index'), 'Back to your dashboard',
            url_for('main.support'), 'Tell support',
        )
