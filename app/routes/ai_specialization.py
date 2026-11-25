"""AI Engineering specialization flows, independent of the ML pathway.

AI Engineering has its own project records, prompt versions, retrieval
configurations, agent execution traces, and evaluation records. AI evidence
is scoped to this pathway and never credits Machine Learning competencies,
and vice versa.
"""

import json

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db
from app.ai_pathway import (
    PATHWAY_ID, ai_engineering_pathway, ai_engineering_project_module_ids,
)
from app.core.exceptions import EntityNotFoundError
from app.domains.ai_engineering.service import (
    get_ai_project_record, get_ai_project_records, get_or_create_ai_project,
)
from app.models import (
    AIPromptVersion, AIRetrievalConfiguration,
    AIAgentExecutionRecord, AIEvaluationRecord,
)
from app.request_data import get_json_object

ai_specialization_bp = Blueprint('ai_specialization', __name__)

_JSON_LIMIT = 12000
_REFLECTION_LIMITS = (80, 12000)
# AI Engineering project submission schema (M2.2). Prompt versions, model
# configuration, retrieval configuration, agent traces and evaluation records
# are captured through their own learner-scoped artefact endpoints; the
# project submission anchors the problem, the architecture, the API surface,
# deployment evidence and the reflection.
_SUBMISSION_FIELDS = (
    'problem_statement', 'reflection', 'architecture_decisions',
    'api_contracts', 'deployment_evidence',
)
_FIELD_LIMITS = {
    'problem_statement': (40, 12000),
    'reflection': _REFLECTION_LIMITS,
    'architecture_decisions': (0, 12000),
    'api_contracts': (0, _JSON_LIMIT),
    'deployment_evidence': (0, 12000),
}


def _bounded_int(value, field_name, minimum=0):
    """Return the int or (None, error message). None value means absent."""
    if value is None:
        return None, None
    if isinstance(value, bool) or not isinstance(value, int):
        return None, f'{field_name} must be an integer'
    if value < minimum:
        return None, f'{field_name} must be at least {minimum}'
    return value, None


def _module(module_id):
    from app.domains.ai_engineering.service import get_ai_module

    try:
        return get_ai_module(module_id)
    except EntityNotFoundError:
        return None


def _project(module_id, create=False):
    """Route helper around the AI domain's pathway-scoped project getter."""
    if create:
        record = get_or_create_ai_project(current_user.id, module_id)
        db.session.commit()
        return record
    return get_ai_project_record(current_user.id, module_id)


def _bounded_string(value, minimum, maximum, field_name):
    if not isinstance(value, str):
        return None, f'{field_name} must be a string'
    stripped = value.strip()
    if not minimum <= len(stripped) <= maximum:
        return None, f'{field_name} must be between {minimum} and {maximum} characters'
    return stripped, None


def _json_text(value, field_name):
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, f'{field_name} must be a string'
    if len(value.encode('utf-8')) > _JSON_LIMIT:
        return None, f'{field_name} is too large'
    return value, None


def _artefact_model(model_class, json_fields, int_fields=None, id_field=None,
                    auto_version=False):
    """Create or update a learner-scoped pathway artefact row.

    ``json_fields`` are stored as text (JSON strings), ``int_fields`` as
    integers. When ``auto_version`` is set, a missing ``version`` is filled
    with the next version for this learner/module.
    """
    int_fields = int_fields or {}
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    module_id = data.get('module_id')
    if module_id not in ai_engineering_project_module_ids():
        return jsonify({'error': 'Unknown or unavailable AI Engineering module'}), 404
    payload = {}
    for field in json_fields:
        value, error = _json_text(data.get(field), field)
        if error:
            return jsonify({'error': error}), 400
        if value is not None:
            payload[field] = value
    for field, minimum in int_fields.items():
        value, error = _bounded_int(data.get(field), field, minimum)
        if error:
            return jsonify({'error': error}), 400
        if value is not None:
            payload[field] = value
    if auto_version and 'version' not in payload:
        latest = model_class.query.filter_by(
            user_id=current_user.id, pathway_id=PATHWAY_ID, module_id=module_id,
        ).order_by(model_class.version.desc()).first()
        payload['version'] = (latest.version + 1) if latest else 1
    filters = dict(user_id=current_user.id, pathway_id=PATHWAY_ID, module_id=module_id)
    if id_field and id_field in payload:
        filters[id_field] = payload[id_field]
    record = model_class.query.filter_by(**filters).first()
    if record is None:
        record = model_class(**filters)
        db.session.add(record)
    for field, value in payload.items():
        setattr(record, field, value)
    db.session.commit()
    return jsonify({'ok': True, 'id': record.id})


@ai_specialization_bp.route('/specializations/ai-engineering')
@login_required
def dashboard():
    pathway = ai_engineering_pathway()
    # Fetch all project records in one query instead of one per module (N+1).
    records = get_ai_project_records(current_user.id)
    record_by_module = {r.module_id: r for r in records}
    modules = []
    for module in pathway['modules']:
        record = record_by_module.get(module['id'])
        modules.append({
            'module': module,
            'project_completed': bool(record and record.completed),
            'has_submission': bool(record and record.submission),
        })
    return render_template(
        'specializations/ai_engineering.html',
        pathway=pathway, modules=modules,
    )


@ai_specialization_bp.route('/specializations/ai-engineering/projects/<module_id>')
@login_required
def project(module_id):
    module = _module(module_id)
    if module is None or module_id not in ai_engineering_project_module_ids():
        abort(404)
    record = _project(module_id, create=True)
    try:
        submission = json.loads(record.submission) if record.submission else {}
    except (TypeError, ValueError):
        submission = {}
    try:
        evaluation = json.loads(record.evaluation) if record.evaluation else None
    except (TypeError, ValueError):
        evaluation = None
    return render_template(
        'specializations/ai_engineering_project.html',
        module=module, record=record, submission=submission,
        evaluation=evaluation,
    )


@ai_specialization_bp.route(
    '/specializations/ai-engineering/projects/<module_id>/submit', methods=['POST']
)
@login_required
def submit_project(module_id):
    module = _module(module_id)
    if module is None or module_id not in ai_engineering_project_module_ids():
        return jsonify({'error': 'Unknown or unavailable AI project'}), 404
    data = get_json_object()
    if not isinstance(data, dict):
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    unknown = sorted(set(data) - set(_SUBMISSION_FIELDS))
    if unknown:
        return jsonify({
            'error': f'Unknown submission fields: {", ".join(unknown)}. '
                     f'Allowed fields: {", ".join(_SUBMISSION_FIELDS)}.',
        }), 400
    submission = {}
    for field in _SUBMISSION_FIELDS:
        minimum, maximum = _FIELD_LIMITS[field]
        value, error = _bounded_string(data.get(field, ''), minimum, maximum, field)
        if error:
            return jsonify({'error': error}), 400
        if value:
            submission[field] = value
    for required in ('problem_statement', 'reflection'):
        if required not in submission:
            return jsonify({'error': f'{required} is required'}), 400
    record = _project(module_id, create=True)
    record.submission = json.dumps(submission, ensure_ascii=False)
    record.completed = False
    record.evaluation = None
    record.failure_stage = None
    record.failure_detail = None
    from app.services.project_lifecycle import LifecycleError, record_transition
    try:
        record_transition(current_user.id, 'ai-engineering', module_id,
                          'submitted', actor=current_user)
    except LifecycleError as error:
        return jsonify({'error': str(error)}), 409
    db.session.commit()
    return jsonify({'ok': True, 'draft_saved': True})


@ai_specialization_bp.route('/api/ai-engineering/prompt-versions', methods=['GET', 'POST'])
@login_required
def prompt_versions():
    if request.method == 'POST':
        return _artefact_model(
            AIPromptVersion, ['prompt_content', 'model_configuration'],
            int_fields={'version': 1}, id_field='version', auto_version=True,
        )
    rows = AIPromptVersion.query.filter_by(
        user_id=current_user.id, pathway_id=PATHWAY_ID,
    ).order_by(AIPromptVersion.module_id, AIPromptVersion.version).all()
    return jsonify([
        {
            'id': r.id, 'module_id': r.module_id, 'version': r.version,
            'prompt_content': r.prompt_content,
            'model_configuration': r.model_configuration,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in rows
    ])


@ai_specialization_bp.route('/api/ai-engineering/retrieval-configs', methods=['GET', 'POST'])
@login_required
def retrieval_configs():
    if request.method == 'POST':
        return _artefact_model(
            AIRetrievalConfiguration,
            ['chunking_configuration', 'embedding_configuration', 'retrieval_parameters'],
        )
    rows = AIRetrievalConfiguration.query.filter_by(
        user_id=current_user.id, pathway_id=PATHWAY_ID,
    ).order_by(AIRetrievalConfiguration.created_at.desc()).all()
    return jsonify([
        {
            'id': r.id, 'module_id': r.module_id,
            'chunking_configuration': r.chunking_configuration,
            'embedding_configuration': r.embedding_configuration,
            'retrieval_parameters': r.retrieval_parameters,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in rows
    ])


@ai_specialization_bp.route('/api/ai-engineering/agent-executions', methods=['GET', 'POST'])
@login_required
def agent_executions():
    if request.method == 'POST':
        return _artefact_model(
            AIAgentExecutionRecord,
            ['execution_id', 'status', 'tool_calls', 'error_summary'],
            int_fields={'duration': 0}, id_field='execution_id',
        )
    rows = AIAgentExecutionRecord.query.filter_by(
        user_id=current_user.id, pathway_id=PATHWAY_ID,
    ).order_by(AIAgentExecutionRecord.created_at.desc()).all()
    return jsonify([
        {
            'id': r.id, 'module_id': r.module_id, 'execution_id': r.execution_id,
            'status': r.status, 'tool_calls': r.tool_calls,
            'duration': r.duration, 'error_summary': r.error_summary,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in rows
    ])


@ai_specialization_bp.route('/api/ai-engineering/evaluations', methods=['GET', 'POST'])
@login_required
def evaluations():
    if request.method == 'POST':
        return _artefact_model(
            AIEvaluationRecord,
            ['evaluation_dataset', 'evaluation_results', 'metric_summary'],
        )
    rows = AIEvaluationRecord.query.filter_by(
        user_id=current_user.id, pathway_id=PATHWAY_ID,
    ).order_by(AIEvaluationRecord.created_at.desc()).all()
    return jsonify([
        {
            'id': r.id, 'module_id': r.module_id,
            'evaluation_dataset': r.evaluation_dataset,
            'evaluation_results': r.evaluation_results,
            'metric_summary': r.metric_summary,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in rows
    ])
