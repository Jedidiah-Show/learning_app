"""ML-only job API (M5). Enqueues work for the independent ML worker."""

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.access import json_admin_required
from app.models import MLBackgroundJob
from app.request_data import get_json_object
from app.services.ml_jobs import (
    MLJobError, cancel_job, enqueue_ml_job, job_status, queue_depth,
)

ml_jobs_bp = Blueprint('ml_jobs', __name__, url_prefix='/api/ml-jobs')


@ml_jobs_bp.route('/jobs', methods=['POST'])
@login_required
def submit_job():
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    job_key = data.get('job_key')
    payload = data.get('payload')
    module_id = data.get('module_id')
    if module_id is not None and (not isinstance(module_id, str) or len(module_id) > 100):
        return jsonify({'error': 'module_id must be at most 100 characters'}), 400
    try:
        job, existed = enqueue_ml_job(
            current_user.id, data.get('job_type'), job_key, payload, module_id,
        )
    except MLJobError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify({'job_id': job.id, 'existing': existed, 'status': job.status}), 202


@ml_jobs_bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    MLBackgroundJob.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    return jsonify(job_status(job_id, current_user.id)), 200


@ml_jobs_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
@login_required
def cancel(job_id):
    return jsonify(cancel_job(job_id, current_user.id)), 200


@ml_jobs_bp.route('/admin/queue', methods=['GET'])
@json_admin_required
def admin_queue():
    return jsonify({'depth': queue_depth()}), 200
