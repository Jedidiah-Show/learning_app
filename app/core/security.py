"""Request-level security hooks: onboarding gate, CSRF and response headers.

These hooks are deliberately infrastructure-only: they never import a route
module or a domain service.  ``is_api_path`` is re-exported from :mod:`app`
because older infrastructure modules import the historical private name.
"""

import hmac
import os
import secrets

from flask import g, redirect, request, session, url_for

from app.core.responses import json_error

# Routes the first-run onboarding gate must never redirect: a learner can always
# reach their own account, security, support, and credential pages before they
# have finished first-run setup. Everything else is gated once.
NEVER_GATED_ENDPOINTS = frozenset({
    'static', 'main.healthz', 'main.readyz', 'main.version',
    'auth.onboarding', 'auth.onboarding_pathway', 'auth.login', 'auth.logout',
    'auth.register',
    'auth.profile', 'auth.profile_photo', 'auth.update_account',
    'auth.delete_account', 'auth.reset_account', 'auth.forgot_password',
    'auth.reset_password', 'auth.verify_phone', 'auth.resend_phone_verification',
    'main.settings', 'main.support',
    'credentials.index', 'credentials.issue', 'credentials.verify',
})


def is_api_path(path):
    """True for JSON API routes, including the Arena API under /arena/api."""
    return path.startswith('/api/') or path.startswith('/arena/api/')


_is_api_path = is_api_path


def admin_header_token_valid():
    supplied = request.headers.get('X-Admin-Token', '')
    if not supplied:
        return False
    for env_key in ('ADMIN_API_TOKEN', 'LESSON_EXTRAS_TOKEN'):
        expected = os.environ.get(env_key) or ''
        if expected and hmac.compare_digest(supplied, expected):
            return True
    return False


def register_authentication(app, login_manager):
    """Configure Flask-Login and the session-version-aware user loader."""
    from flask import session

    from app.core.extensions import db

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.unauthorized_handler
    def unauthorized():
        if is_api_path(request.path):
            return json_error('Authentication required', 401)
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


def register_security_hooks(app):
    """Install onboarding, CSRF and security-header request hooks."""

    @app.before_request
    def ensure_csp_nonce():
        if not getattr(g, 'csp_nonce', None):
            g.csp_nonce = secrets.token_urlsafe(16)
        return None

    @app.before_request
    def gate_post_setup():
        # First-run onboarding: every new learner sees the setup questions
        # and the pathway fit check once before they start learning. Account,
        # security, support, and credential routes stay reachable so a learner
        # can always manage their own account even before they have answered.
        from flask_login import current_user

        if (
            current_user.is_authenticated
            and request.endpoint not in NEVER_GATED_ENDPOINTS
            and not is_api_path(request.path)
            and session.get('_post_setup_next')
            and not session.get('_onboarding_done')
        ):
            return redirect(url_for('auth.onboarding'))
        return None

    @app.before_request
    def enforce_csrf_protection():
        if (
            request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}
            and app.config.get('CSRF_ENABLED', not app.testing)
        ):
            # A custom header cannot be set by a cross-site form post, so
            # requests already proven by X-Admin-Token are CSRF-immune.
            if request.path.startswith('/api/admin/') and admin_header_token_valid():
                return None
            # GitHub cannot send a session CSRF token; the webhook authenticates
            # itself with an HMAC-SHA256 signature over the raw body instead.
            if request.path == '/api/webhooks/github':
                return None
            token = session.get('_csrf_token')
            supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not token or not supplied or not hmac.compare_digest(token, supplied):
                if is_api_path(request.path):
                    return json_error('CSRF validation failed', 400)
                return 'CSRF validation failed', 400
        return None

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
            response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
            response.headers.setdefault('Cache-Control', 'public, max-age=86400')
        elif request.path.startswith('/static/'):
            response.headers.setdefault('Cache-Control', 'public, max-age=86400')
        # Enforced CSP: per-request nonce for scripts and styles.
        # Inline style attributes have been migrated to data-* + JS initializer.
        nonce = getattr(g, 'csp_nonce', '')
        script_src = f"'self' 'nonce-{nonce}'" if nonce else "'self'"
        style_src = f"'self' 'nonce-{nonce}'" if nonce else "'self'"
        csp = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'self'; "
            "form-action 'self'; "
            f"script-src {script_src} "
            "https://www.youtube.com https://www.youtube-nocookie.com "
            "https://www.gstatic.com; "
            f"style-src {style_src}; "
            "img-src 'self' data: https://i.ytimg.com https://*.ytimg.com; "
            "font-src 'self' data:; "
            "frame-src 'self' https://www.youtube.com "
            "https://www.youtube-nocookie.com; "
            "connect-src 'self';"
        )
        response.headers.setdefault('Content-Security-Policy', csp)
        return response
