import csv
from io import StringIO

from flask import Blueprint, Response, jsonify, render_template
from flask_login import current_user, login_required

from app.services.skill_passport import get_user_all_skill_states


passport_bp = Blueprint('passport', __name__)


def _skills():
    states = get_user_all_skill_states(current_user.id)
    return [
        {'id': skill_id, **state}
        for skill_id, state in sorted(states.items())
    ]


@passport_bp.route('/passport')
@login_required
def passport():
    return render_template('passport.html', skills=_skills())


@passport_bp.route('/api/passport')
@login_required
def passport_api():
    return jsonify({'skills': _skills()})


@passport_bp.route('/passport/download')
@login_required
def download_passport():
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
