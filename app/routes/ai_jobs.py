"""HTTP adapters for durable AI jobs and usage telemetry (M2.4/M2.8)."""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.ai.prompts.registry import active_version
from app.gemini import GeminiRateLimited
from app.models import CourseProject
from app.request_data import get_json_object
from app.services.ai_jobs import (
    cancel_job, enqueue_ai_job, get_job, job_status, list_jobs, retry_job,
)
from app.ai.observability import usage_summary
from app.workers.job_registry import registered_types

ai_jobs_bp = Blueprint('ai_jobs', __name__)


def _is_admin() -> bool:
    return bool(
        getattr(current_user, 'is_admin', False)
        or getattr(current_user, 'role', None) == 'administrator'
    )


def _require_json_object():
    data = get_json_object()
    return data if isinstance(data, dict) else {}


def _clip(value, length):
    if not isinstance(value, str):
        return None
    return value.strip()[:length] or None


def _rate_limit_response(error):
    response = jsonify({'error': str(error)})
    response.status_code = 429
    response.headers['Retry-After'] = str(getattr(error, 'retry_after', None) or 60)
    return response


@ai_jobs_bp.route('/jobs', methods=['POST'])
@login_required
def enqueue_generation():
    data = _require_json_object()
    prompt = data.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
        return jsonify({'error': 'A prompt of at most 8000 characters is required'}), 400
    task_type = data.get('task_type') or 'document_analysis'
    if task_type not in {'document_analysis', 'rag_generation', 'agent_execution', 'model_evaluation'}:
        return jsonify({'error': 'Unsupported asynchronous AI task'}), 400
    try:
        job = enqueue_ai_job(
            current_user.id,
            'ai_generation',
            {
                'prompt': prompt,
                'task_type': task_type,
                'model': data.get('model'),
                'prompt_version': (
                    _clip(data.get('prompt_version'), 40) or active_version(task_type)
                ),
            },
            correlation_id=_clip(request.headers.get('X-Correlation-ID'), 64),
            idempotency_nonce=data.get('idempotency_nonce'),
        )
    except GeminiRateLimited as error:
        return _rate_limit_response(error)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify({
        'job_id': job.id,
        'status': job.status,
        'status_url': f'/api/ai/jobs/{job.id}',
    }), 202


@ai_jobs_bp.route('/jobs/project-review/<int:project_id>', methods=['POST'])
@login_required
def enqueue_project_review(project_id):
    project = CourseProject.query.filter_by(
        id=project_id, user_id=current_user.id
    ).first()
    if project is None:
        return jsonify({'error': 'Project not found'}), 404
    if not project.submission:
        return jsonify({'error': 'Submit the project before requesting a review'}), 409
    try:
        job = enqueue_ai_job(
            current_user.id,
            'project_review',
            {
                'project_id': project_id,
                'prompt_version': active_version('project_review'),
            },
            correlation_id=_clip(request.headers.get('X-Correlation-ID'), 64),
        )
    except GeminiRateLimited as error:
        return _rate_limit_response(error)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify({
        'job_id': job.id,
        'status': job.status,
        'status_url': f'/api/ai/jobs/{job.id}',
    }), 202


@ai_jobs_bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
def job_detail(job_id):
    status = job_status(
        job_id, user_id=current_user.id, is_admin=_is_admin()
    )
    if status is None:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(status)


@ai_jobs_bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
@login_required
def cancel(job_id):
    job = get_job(job_id, user_id=current_user.id, is_admin=_is_admin())
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    if not cancel_job(job):
        return jsonify({'error': 'Job cannot be cancelled in its current state'}), 409
    return jsonify({'job_id': job.id, 'status': job.status, 'cancelled': True})


@ai_jobs_bp.route('/admin/jobs', methods=['GET'])
@login_required
def admin_jobs():
    if not _is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
    status = request.args.get('status') or None
    jobs = list_jobs(status=status)
    return jsonify({
        'jobs': [job_status(job.id, is_admin=True) for job in jobs],
        'registered_types': registered_types(),
    })


@ai_jobs_bp.route('/admin/jobs/<int:job_id>/retry', methods=['POST'])
@login_required
def admin_retry(job_id):
    if not _is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
    job = get_job(job_id, is_admin=True)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    if not retry_job(job):
        return jsonify({'error': 'Only terminal jobs can be retried'}), 409
    return jsonify({'job_id': job.id, 'status': job.status, 'retried': True})


@ai_jobs_bp.route('/admin/usage', methods=['GET'])
@login_required
def admin_usage():
    if not _is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
    try:
        days = int(request.args.get('days', 7))
    except (TypeError, ValueError):
        return jsonify({'error': 'days must be an integer'}), 400
    return jsonify(usage_summary(days))
