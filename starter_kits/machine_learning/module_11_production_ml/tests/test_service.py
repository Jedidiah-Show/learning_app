import pandas as pd
from fastapi.testclient import TestClient
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from monitoring import CanaryRelease, InputShiftMonitor
from project_report import build_report
from service import create_app


def fitted_model():
    data = pd.read_csv('data/train.csv')
    model = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(max_iter=1000, random_state=7)),
    ])
    model.fit(data[['support_tickets', 'tenure_months']], data['churn_within_30_days'])
    return model


def test_health_and_batch_prediction_contract():
    client = TestClient(create_app(fitted_model()))
    assert client.get('/healthz').json() == {'status': 'ok', 'model_version': '1.0.0'}
    payload = {'records': [
        {'support_tickets': 0, 'tenure_months': 12},
        {'support_tickets': 4, 'tenure_months': 12},
    ]}
    response = client.post('/predict/batch', json=payload)
    assert response.status_code == 200
    assert len(response.json()['predictions']) == 2
    assert all(item['model_version'] == '1.0.0' for item in response.json()['predictions'])


def test_input_contract_rejects_unknown_and_invalid_features():
    client = TestClient(create_app(fitted_model()))
    assert client.post('/predict', json={
        'support_tickets': -1, 'tenure_months': 12,
    }).status_code == 422
    assert client.post('/predict', json={
        'support_tickets': 2, 'tenure_months': 12, 'cancelled_after_snapshot': 1,
    }).status_code == 422


def test_drift_alert_and_canary_rollback_are_distinct_controls():
    monitor = InputShiftMonitor()
    shift = monitor.inspect([8, 9, 10, 11])
    assert shift['drift_detected'] is True
    assert shift['model_quality_failed'] is False

    release = CanaryRelease(current_version='1.0.0', error_rate_limit=0.10)
    decision = release.evaluate_candidate('1.1.0', observed_error_rate=0.25)
    assert decision['promoted'] is False
    assert decision['active_version'] == '1.0.0'
    assert decision['rolled_back'] is True


def test_project_report_matches_submission_contract():
    report = build_report(fitted_model())
    assert report == {
        'health_status': 200,
        'model_version': '1.0.0',
        'batch_prediction_count': 2,
        'invalid_feature_rejected': True,
        'extra_feature_rejected': True,
        'input_drift_detected': True,
        'drift_proves_quality_failure': False,
        'canary_promoted': False,
        'rollback_active_version': '1.0.0',
        'rollback_triggered': True,
    }
