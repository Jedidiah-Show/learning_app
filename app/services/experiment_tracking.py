"""MLflow-compatible traceability mapping for ML experiments (M3.8).

The LMS `MLProjectExperiment` row remains the source of truth. This service
builds an MLflow-shaped run payload and records returned identifiers on that
row; it does not install or start an MLflow tracking server.
"""

from __future__ import annotations

import json

from flask import current_app

from app import db
from app.models import MLProjectExperiment, ProjectArtifact


RUN_STATUSES = frozenset({'queued', 'running', 'finished', 'failed', 'killed'})


class TrackingError(ValueError):
    pass


def _load_json(value, field_name):
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError) as error:
        raise TrackingError(f'{field_name} must contain valid JSON') from error
    if not isinstance(parsed, dict):
        raise TrackingError(f'{field_name} must contain a JSON object')
    return parsed


def build_run_payload(experiment: MLProjectExperiment) -> dict:
    """Map one LMS experiment to an MLflow run payload."""
    if not isinstance(experiment, MLProjectExperiment):
        raise TrackingError('An MLProjectExperiment is required')
    params = _load_json(experiment.hyperparameters, 'hyperparameters')
    metrics = _load_json(experiment.evaluation_metrics, 'evaluation_metrics')
    environment = _load_json(experiment.environment_json, 'environment_json')
    artifacts = ProjectArtifact.query.filter_by(
        project_type='ml', project_id=experiment.id
    ).order_by(ProjectArtifact.id).all()
    tags = {
        'ruach.user_id': str(experiment.user_id),
        'ruach.pathway_id': experiment.pathway_id,
        'ruach.module_id': experiment.module_id,
        'ruach.experiment_id': str(experiment.id),
        'dataset.version': experiment.dataset_version or '',
        'model.type': experiment.model_type or '',
        'execution.profile': 'container_data_science',
    }
    prefix = current_app.config.get('MLFLOW_EXPERIMENT_PREFIX', 'ruach')
    return {
        'experiment_name': (
            f'{prefix}-{experiment.pathway_id}-{experiment.module_id}'
        ),
        'run_name': experiment.experiment_name,
        'run_id': experiment.mlflow_run_id,
        'experiment_id': experiment.mlflow_experiment_id,
        'status': experiment.run_status or 'queued',
        'params': params,
        'metrics': metrics,
        'tags': {key: value for key, value in tags.items() if value},
        'artifacts': [item.storage_key for item in artifacts],
        'environment': environment,
        'tracking_uri': experiment.tracking_uri,
    }


def record_mlflow_run(
    experiment: MLProjectExperiment,
    *,
    experiment_id,
    run_id,
    tracking_uri,
    status='finished',
    environment=None,
) -> dict:
    """Persist MLflow identifiers on the existing experiment record."""
    if status not in RUN_STATUSES:
        raise TrackingError(f'Unsupported run status: {status}')
    if not experiment_id or not run_id:
        raise TrackingError('MLflow experiment_id and run_id are required')
    experiment.mlflow_experiment_id = str(experiment_id)[:80]
    experiment.mlflow_run_id = str(run_id)[:80]
    experiment.tracking_uri = str(tracking_uri or '')[:500]
    experiment.run_status = status
    if environment is not None:
        if not isinstance(environment, dict):
            raise TrackingError('environment must be a dictionary')
        experiment.environment_json = json.dumps(environment)
    db.session.commit()
    return build_run_payload(experiment)


def get_tracking_config() -> dict:
    """Return non-secret tracking configuration for health output."""
    return {
        'tracking_uri': current_app.config.get('MLFLOW_TRACKING_URI') or '',
        'experiment_name_prefix': current_app.config.get(
            'MLFLOW_EXPERIMENT_PREFIX', 'ruach'
        ),
        'enabled': bool(current_app.config.get('MLFLOW_TRACKING_URI')),
    }
