import csv
from io import StringIO

from flask import Blueprint, Response, current_app, jsonify, render_template
from flask_login import current_user, login_required

from app.integrations import database_status
from app.services.skill_passport import get_user_all_skill_states


passport_bp = Blueprint('passport', __name__)


def _skills():
    states = get_user_all_skill_states(current_user.id)
    return [
        {'id': skill_id, **state}
        for skill_id, state in sorted(states.items())
    ]


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
            'passport.html', skills=[], passport_unavailable=True,
        ), 503
    return render_template('passport.html', skills=_skills())


@passport_bp.route('/api/passport')
@login_required
def passport_api():
    if not _passport_schema_ready():
        return jsonify({
            'error': 'Skill Passport is temporarily unavailable while the application database is being updated.',
        }), 503
    return jsonify({'skills': _skills()})


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
        'evidence_type', 'evidence_id', 'updated_at',
    ])
    for skill in _skills():
        writer.writerow([
            skill['id'], skill.get('title', ''), skill.get('category', ''),
            skill['status'], skill.get('evidence_type') or '',
            skill.get('evidence_id') or '', skill.get('updated_at') or '',
        ])
    return Response(
        content.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename="ruach-skill-passport.csv"',
            'Cache-Control': 'private, no-store',
        },
    )
