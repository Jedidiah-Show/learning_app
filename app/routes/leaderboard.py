"""Privacy-controlled course leaderboard participation."""

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from app import db
from app.leaderboard import (
    invalidate_leaderboard_cache, leaderboard_data, refresh_leaderboard_score,
)
from app.models import CoursePlan
from app.request_data import get_json_object


leaderboard_bp = Blueprint('leaderboard', __name__)


@leaderboard_bp.route('/leaderboard')
@login_required
def page():
    """The learner-facing board: top 20 opt-in learners plus your own rank."""
    board = leaderboard_data(current_user)
    return render_template('leaderboard.html', board=board)


@leaderboard_bp.route('/api/leaderboard/visibility', methods=['POST'])
@login_required
def set_leaderboard_visibility():
    data = get_json_object()
    if not isinstance(data, dict) or not isinstance(data.get('opt_in'), bool):
        return jsonify({'error': 'Choose whether to show your username on the leaderboard'}), 400
    plan = CoursePlan.query.filter_by(user_id=current_user.id).first()
    if plan is None:
        plan = CoursePlan(user_id=current_user.id)
        db.session.add(plan)
    plan.leaderboard_opt_in = data['opt_in']
    db.session.commit()
    refresh_leaderboard_score(current_user.id)
    invalidate_leaderboard_cache()
    return jsonify({'opted_in': plan.leaderboard_opt_in})


@leaderboard_bp.route('/api/leaderboard', methods=['GET'])
@login_required
def get_leaderboard():
    return jsonify(leaderboard_data(current_user))
