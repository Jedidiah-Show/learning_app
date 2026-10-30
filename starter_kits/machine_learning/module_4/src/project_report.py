"""Build the fixed service and operations evidence report."""

from fastapi.testclient import TestClient

from monitoring import CanaryRelease, InputShiftMonitor
from service import create_app


def build_report(model):
    """Exercise the service and operations controls used by the CI checks."""
    client = TestClient(create_app(model))
    health = client.get('/healthz')
    batch = client.post('/predict/batch', json={'records': [
        {'support_tickets': 0, 'tenure_months': 12},
        {'support_tickets': 4, 'tenure_months': 12},
    ]})
    invalid_feature = client.post('/predict', json={
        'support_tickets': -1, 'tenure_months': 12,
    })
    extra_feature = client.post('/predict', json={
        'support_tickets': 2, 'tenure_months': 12,
        'cancelled_after_snapshot': 1,
    })
    drift = InputShiftMonitor().inspect([8, 9, 10, 11])
    canary = CanaryRelease().evaluate_candidate('1.1.0', .25)
    return {
        'health_status': health.status_code,
        'model_version': health.json().get('model_version'),
        'batch_prediction_count': len(batch.json().get('predictions', [])),
        'invalid_feature_rejected': invalid_feature.status_code == 422,
        'extra_feature_rejected': extra_feature.status_code == 422,
        'input_drift_detected': drift.get('drift_detected') is True,
        'drift_proves_quality_failure': drift.get('model_quality_failed') is True,
        'canary_promoted': canary.get('promoted') is True,
        'rollback_active_version': canary.get('active_version'),
        'rollback_triggered': canary.get('rolled_back') is True,
    }
