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
from app.pathway_scope import destination_for


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
    # The AI Engineering credential stays gated on the full AI course: a
    # learner on the ML pathway must never claim it after the shared
    # foundation alone, so the scope is pinned rather than pathway-derived.
    # The eligibility snapshot uses the AI course scope; the numbers shown to
    # the learner use their own destination so ML learners never see AI course
    # denominators (all 213 lessons and 13 modules) for their credential.
    eligibility = course_progress(current_user, destination='ai')
    progress = course_progress(
        current_user, destination=destination_for(current_user),
    )
    credential = _active_credential(current_user.id)
    return render_template(
        'credential.html', progress=progress, eligibility=eligibility,
        credential=credential, course=curriculum(),
    )


@credentials_bp.route('/api/credentials/issue', methods=['POST'])
@login_required
def issue():
    # Pinned to the full AI course, matching index(): the credential must not
    # be issuable to an ML learner who finished only the shared foundation.
    progress = course_progress(current_user, destination='ai')
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


@credentials_bp.route('/.well-known/jwks.json')
def jwks_public():
    """Publish the Ed25519 public verification key for W3C credentials."""
    from app.services.w3c_credentials import jwks, W3CCredentialError

    try:
        payload = jwks()
    except W3CCredentialError as error:
        return jsonify({'error': str(error)}), 503
    response = jsonify(payload)
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@credentials_bp.route('/api/credentials/<public_id>/status')
def credential_status(public_id):
    """Public revocation status check for verifiers and registries."""
    credential = Credential.query.filter_by(public_id=public_id).first()
    if credential is None:
        return jsonify({'error': 'Unknown credential'}), 404
    return jsonify({
        'public_id': credential.public_id,
        'status': 'revoked' if credential.revoked_at else 'active',
        'revoked_at': credential.revoked_at.isoformat() if credential.revoked_at else None,
    })


@credentials_bp.route('/api/credentials/<public_id>/vc.json')
@login_required
def credential_vc_download(public_id):
    """Download the owner's signed W3C Verifiable Credential document."""
    from flask import Response
    import json as _json

    credential = Credential.query.filter_by(
        public_id=public_id, user_id=current_user.id,
    ).first()
    if credential is None:
        abort(404)
    if credential.revoked_at is not None:
        return jsonify({'error': 'This credential has been revoked and cannot be exported.'}), 409
    from app.services.w3c_credentials import vc_for_course_credential, W3CCredentialError

    try:
        vc = vc_for_course_credential(credential, _issuer())
    except W3CCredentialError as error:
        return jsonify({'error': str(error)}), 503
    body = _json.dumps(vc, indent=2, ensure_ascii=False)
    response = Response(body, mimetype='application/vc+ld+json')
    response.headers['Content-Disposition'] = (
        f'attachment; filename="ruach-credential-{credential.public_id}.vc.json"'
    )
    response.headers['Cache-Control'] = 'no-store'
    return response


@credentials_bp.route('/api/credentials/verify-vc', methods=['POST'])
def verify_vc_route():
    """Verify a submitted W3C Verifiable Credential document against the issuer key."""
    from app.rate_limit import enforce_rate_limit
    from app.request_data import get_json_object

    enforce_rate_limit('credentials-verify-vc')
    payload = get_json_object()
    if not isinstance(payload, dict):
        return jsonify({'error': 'Send the credential JSON document'}), 400
    from app.services.w3c_credentials import verify_vc, W3CCredentialError

    try:
        ok, reason = verify_vc(payload)
    except W3CCredentialError as error:
        return jsonify({'valid': False, 'reason': str(error)}), 503
    result = {'valid': ok, 'reason': reason}
    # Best-effort revocation lookup by the credential's RUACH id, if present.
    vid = payload.get('id') if isinstance(payload.get('id', None), str) else ''
    marker = '/credentials/'
    if marker in vid:
        public_id = vid.rsplit(marker, 1)[-1].strip()
        credential = Credential.query.filter_by(public_id=public_id).first()
        if credential is None:
            from app.models import MLSpecializationCredential
            credential = MLSpecializationCredential.query.filter_by(public_id=public_id).first()
        if credential is not None:
            result['status'] = 'revoked' if credential.revoked_at else 'active'
    return jsonify(result)


def _issuer() -> str:
    """Canonical issuer URL for verifiable credentials."""
    configured = (current_app.config.get('PUBLIC_APP_URL') or '').strip().rstrip('/')
    if configured:
        return configured
    try:
        return request.host_url.rstrip('/')
    except Exception:
        return 'https://localhost'
