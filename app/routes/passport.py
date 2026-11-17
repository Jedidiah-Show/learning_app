import csv
from io import StringIO

from flask import Blueprint, Response, current_app, jsonify, render_template
from flask_login import current_user, login_required

from app import db
from app.integrations import database_status
from app.models import SkillNode, SkillVerification, UserSkillProgress, utcnow
from app.request_data import get_json_object
from app.services.skill_passport import (
    CURRICULUM_SKILLS, ML_COMPETENCIES, get_user_all_skill_states,
)


passport_bp = Blueprint('passport', __name__)

VERIFICATION_STATUSES = {
    'UNVERIFIED', 'SUBMITTED', 'ASSESSED', 'VERIFIED', 'REJECTED',
    'NEEDS_REVISION', 'REVOKED',
}


def _record_verification(user_id, skill_id, from_status, to_status, note=None, assessed_by=None):
    record = SkillVerification(
        user_id=user_id, skill_id=skill_id,
        from_status=from_status, to_status=to_status,
        requested_by_user_id=user_id,
        assessed_by_user_id=assessed_by,
        note=note,
    )
    db.session.add(record)


def _skill_or_404(skill_id):
    skill = db.session.get(SkillNode, skill_id)
    if skill is None:
        return None
    return skill


def _progress_or_404(user_id, skill_id):
    progress = UserSkillProgress.query.filter_by(
        user_id=user_id, skill_id=skill_id,
    ).first()
    if progress is None:
        return None
    return progress


def _skill_domain(skill):
    sid = (skill.get('id') or '').lower()
    category = (skill.get('category') or '').lower()
    title = (skill.get('title') or '').lower()
    if sid in ML_COMPETENCIES or sid.startswith(('ml-', 'mle.')) or 'machine learning' in category:
        return 'machine-learning'
    if sid in CURRICULUM_SKILLS or sid.startswith(('curriculum-', 'lesson-', 'project-studio')):
        return 'ai-engineering'
    if category in {'projects', 'curriculum'}:
        return 'ai-engineering'
    if category in {'shared-foundations', 'foundations'} or 'foundation' in title:
        return 'shared-foundations'
    # Practice arena/problem skills can span tracks; keep explicit when possible.
    return 'shared-foundations'


def _skills():
    states = get_user_all_skill_states(current_user.id)
    user_progresses = {
        row.skill_id: row
        for row in UserSkillProgress.query.filter_by(user_id=current_user.id).all()
    }
    skills = []
    for skill_id, state in sorted(states.items()):
        item = {'id': skill_id, **state}
        item['domain'] = _skill_domain(item)
        progress = user_progresses.get(skill_id)
        if progress is not None:
            item['verification_status'] = progress.verification_status
            item['verified_at'] = (
                progress.verified_at.isoformat() if progress.verified_at else None
            )
            item['verification_note'] = progress.verification_note
        else:
            item['verification_status'] = 'UNVERIFIED'
            item['verified_at'] = None
            item['verification_note'] = None
        skills.append(item)
    return skills


def _skills_by_domain(skills):
    grouped = {
        'shared-foundations': [],
        'ai-engineering': [],
        'machine-learning': [],
    }
    for skill in skills:
        grouped.setdefault(skill.get('domain') or 'shared-foundations', []).append(skill)
    return grouped


def _passport_schema_ready():
    status = database_status()
    required_tables = {'skill_node', 'user_skill_progress'}
    missing_tables = required_tables.intersection(status['missing_tables'])
    missing_columns = {
        column for column in status['missing_columns']
        if column.startswith(('skill_node.', 'user_skill_progress.'))
    }
    if not status['ok'] or missing_tables or missing_columns:
        current_app.logger.error(
            'Skill Passport unavailable: database readiness failed '
            '(missing tables: %s; missing columns: %s)',
            sorted(missing_tables), sorted(missing_columns),
        )
        return False
    return True


@passport_bp.route('/passport')
@login_required
def passport():
    if not _passport_schema_ready():
        return render_template(
            'passport.html', skills=[], skills_by_domain={},
            passport_unavailable=True,
        ), 503
    skills = _skills()
    from app.pathway_scope import destination_for
    return render_template(
        'passport.html', skills=skills, skills_by_domain=_skills_by_domain(skills),
        active_pathway=destination_for(current_user),
    )


@passport_bp.route('/api/passport')
@login_required
def passport_api():
    if not _passport_schema_ready():
        return jsonify({
            'error': 'Skill Passport is temporarily unavailable while the application database is being updated.',
        }), 503
    skills = _skills()
    return jsonify({
        'skills': skills,
        'skills_by_domain': _skills_by_domain(skills),
    })


@passport_bp.route('/passport/download')
@login_required
def download_passport():
    if not _passport_schema_ready():
        return jsonify({
            'error': 'Skill Passport is temporarily unavailable while the application database is being updated.',
        }), 503
    content = StringIO()
    writer = csv.writer(content)
    writer.writerow([
        'skill_id', 'title', 'category', 'status',
        'evidence_type', 'evidence_id', 'verification_status',
        'verified_at', 'updated_at',
    ])
    for skill in _skills():
        writer.writerow([
            skill['id'], skill.get('title', ''), skill.get('category', ''),
            skill['status'], skill.get('evidence_type') or '',
            skill.get('evidence_id') or '',
            skill.get('verification_status') or 'UNVERIFIED',
            skill.get('verified_at') or '',
            skill.get('updated_at') or '',
        ])
    return Response(
        content.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename="ruach-skill-passport.csv"',
            'Cache-Control': 'private, no-store',
        },
    )


def _require_verified_schema():
    if not _passport_schema_ready():
        return jsonify({
            'error': 'Skill Passport is temporarily unavailable while the application database is being updated.',
        }), 503
    return None


@passport_bp.route('/api/passport/skills/<skill_id>/verify', methods=['POST'])
@login_required
def submit_verification(skill_id):
    """Request verification for a competency evidence (UNVERIFIED -> SUBMITTED)."""
    error = _require_verified_schema()
    if error:
        return error
    progress = _progress_or_404(current_user.id, skill_id)
    if progress is None:
        return jsonify({'error': 'No progress record for this skill'}), 404
    if progress.verification_status not in ('UNVERIFIED', 'REJECTED', 'REVOKED'):
        return jsonify({
            'error': f'Cannot submit verification from {progress.verification_status}',
        }), 409
    from_status = progress.verification_status
    progress.verification_status = 'SUBMITTED'
    progress.verified_at = None
    progress.verified_by_user_id = None
    progress.verification_note = None
    progress.updated_at = utcnow()
    _record_verification(current_user.id, skill_id, from_status, 'SUBMITTED',
                         note='Learner submitted evidence for verification')
    db.session.commit()
    return jsonify({
        'ok': True, 'skill_id': skill_id,
        'verification_status': 'SUBMITTED',
    })


@passport_bp.route('/api/passport/skills/<skill_id>/assess', methods=['POST'])
@login_required
def assess_verification(skill_id):
    """Assess submitted evidence (SUBMITTED -> VERIFIED / REJECTED / NEEDS_REVISION)."""
    error = _require_verified_schema()
    if error:
        return error
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    to_status = data.get('verification_status')
    if to_status not in ('VERIFIED', 'REJECTED', 'NEEDS_REVISION'):
        return jsonify({'error': 'verification_status must be VERIFIED, REJECTED, or NEEDS_REVISION'}), 400
    progress = _progress_or_404(current_user.id, skill_id)
    if progress is None:
        return jsonify({'error': 'No progress record for this skill'}), 404
    if progress.verification_status != 'SUBMITTED':
        return jsonify({
            'error': f'No evidence submitted for assessment (current: {progress.verification_status})',
        }), 409
    from_status = progress.verification_status
    progress.verification_status = to_status
    progress.verified_at = utcnow() if to_status == 'VERIFIED' else None
    progress.verified_by_user_id = current_user.id if to_status == 'VERIFIED' else None
    progress.verification_note = data.get('note') or ''
    progress.updated_at = utcnow()
    _record_verification(
        current_user.id, skill_id, from_status, to_status,
        note=progress.verification_note, assessed_by=current_user.id,
    )
    db.session.commit()
    return jsonify({
        'ok': True, 'skill_id': skill_id,
        'verification_status': to_status,
    })


@passport_bp.route('/api/passport/skills/<skill_id>/reassess', methods=['POST'])
@login_required
def reassess_verification(skill_id):
    """Reassess an already-verified competency (VERIFIED -> SUBMITTED for re-check)."""
    error = _require_verified_schema()
    if error:
        return error
    progress = _progress_or_404(current_user.id, skill_id)
    if progress is None:
        return jsonify({'error': 'No progress record for this skill'}), 404
    if progress.verification_status not in ('VERIFIED', 'REJECTED', 'NEEDS_REVISION'):
        return jsonify({
            'error': f'Cannot reassess from {progress.verification_status}',
        }), 409
    from_status = progress.verification_status
    progress.verification_status = 'SUBMITTED'
    progress.verified_at = None
    progress.verified_by_user_id = None
    progress.updated_at = utcnow()
    _record_verification(
        current_user.id, skill_id, from_status, 'SUBMITTED',
        note='Learner requested reassessment',
    )
    db.session.commit()
    return jsonify({
        'ok': True, 'skill_id': skill_id,
        'verification_status': 'SUBMITTED',
    })


@passport_bp.route('/api/passport/skills/<skill_id>/invalidate', methods=['POST'])
@login_required
def invalidate_verification(skill_id):
    """Invalidate verified evidence (VERIFIED -> REVOKED), preserving history."""
    error = _require_verified_schema()
    if error:
        return error
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    reason = data.get('reason') or ''
    if not isinstance(reason, str) or not reason.strip():
        return jsonify({'error': 'invalidation reason is required'}), 400
    progress = _progress_or_404(current_user.id, skill_id)
    if progress is None:
        return jsonify({'error': 'No progress record for this skill'}), 404
    if progress.verification_status != 'VERIFIED':
        return jsonify({
            'error': f'Only verified evidence can be invalidated (current: {progress.verification_status})',
        }), 409
    from_status = progress.verification_status
    progress.verification_status = 'REVOKED'
    progress.verified_at = None
    progress.verified_by_user_id = None
    progress.verification_note = f'REVOKED: {reason.strip()}'
    progress.updated_at = utcnow()
    _record_verification(
        current_user.id, skill_id, from_status, 'REVOKED',
        note=f'Invalidated: {reason.strip()}',
    )
    db.session.commit()
    return jsonify({
        'ok': True, 'skill_id': skill_id,
        'verification_status': 'REVOKED',
    })


@passport_bp.route('/api/passport/skills/<skill_id>/history', methods=['GET'])
@login_required
def verification_history(skill_id):
    """Return the verification transition history for a skill (traceability)."""
    error = _require_verified_schema()
    if error:
        return error
    rows = SkillVerification.query.filter_by(
        user_id=current_user.id, skill_id=skill_id,
    ).order_by(SkillVerification.created_at.asc()).all()
    return jsonify({
        'skill_id': skill_id,
        'history': [
            {
                'from_status': r.from_status,
                'to_status': r.to_status,
                'requested_by_user_id': r.requested_by_user_id,
                'assessed_by_user_id': r.assessed_by_user_id,
                'note': r.note,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            } for r in rows
        ],
    })
