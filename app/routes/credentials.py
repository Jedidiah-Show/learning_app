"""Course credential eligibility, issuance, and public verification."""

import hashlib
import hmac
import secrets

from flask import (
    Blueprint, abort, current_app, jsonify, render_template, request, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.curriculum import curriculum
from app.learning import course_progress
from app.models import Credential


credentials_bp = Blueprint('credentials', __name__)

SIGNATURE_PREFIX = 'ruach-credential-v1:'


def signing_secret():
    secret = (
        current_app.config.get('TOKEN_ENCRYPTION_KEY')
        or current_app.config.get('SECRET_KEY')
        or b''
    )
    if isinstance(secret, str):
        secret = secret.encode('utf-8')
    return secret


def credential_signature(public_id):
    """Deterministic issuer signature a verifier can check server-side."""
    return hmac.new(
        signing_secret(),
        (SIGNATURE_PREFIX + public_id).encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()[:20]


def verify_signature(public_id, supplied):
    if not isinstance(supplied, str) or not supplied:
        return False
    return hmac.compare_digest(credential_signature(public_id), supplied)


def _active_credential(user_id):
    return Credential.query.filter_by(
        user_id=user_id, revoked_at=None
    ).order_by(Credential.issued_at.desc()).first()


@credentials_bp.route('/credential')
@login_required
def index():
    progress = course_progress(current_user)
    credential = _active_credential(current_user.id)
    return render_template(
        'credential.html', progress=progress, credential=credential,
        course=curriculum(),
    )


@credentials_bp.route('/api/credentials/issue', methods=['POST'])
@login_required
def issue():
    progress = course_progress(current_user)
    if not progress['course_complete']:
        return jsonify({
            'error': (
                'Complete every lesson and every module project before '
                'claiming the course credential.'
            ),
            'completed_lessons': progress['completed_lessons'],
            'total_lessons': progress['total_lessons'],
            'completed_projects': progress['completed_projects'],
            'total_projects': progress['total_projects'],
        }), 409
    existing = _active_credential(current_user.id)
    if existing:
        return jsonify({'credential': _payload(existing), 'existing': True})
    recipient = (
        current_user.full_name or current_user.username or current_user.email
        or f'Learner {current_user.id}'
    )
    credential = Credential(
        user_id=current_user.id,
        public_id=secrets.token_urlsafe(18),
        course_title=curriculum()['course']['title'],
        recipient_name=recipient[:160],
    )
    db.session.add(credential)
    db.session.commit()
    return jsonify({'credential': _payload(credential), 'existing': False}), 201


def _payload(credential):
    return {
        'public_id': credential.public_id,
        'course_title': credential.course_title,
        'recipient_name': credential.recipient_name,
        'issued_at': credential.issued_at.isoformat(),
        'status': 'revoked' if credential.revoked_at else 'active',
        'signature': credential_signature(credential.public_id),
        'verify_url': url_for(
            'credentials.verify',
            public_id=credential.public_id,
            sig=credential_signature(credential.public_id),
            _external=True,
        ),
    }


@credentials_bp.route('/credentials/<public_id>')
def verify(public_id):
    credential = Credential.query.filter_by(public_id=public_id).first()
    if credential is None:
        abort(404)
    signature_ok = verify_signature(public_id, request.args.get('sig', ''))
    return render_template(
        'credential_verify.html', credential=credential,
        signature_ok=signature_ok,
    )
