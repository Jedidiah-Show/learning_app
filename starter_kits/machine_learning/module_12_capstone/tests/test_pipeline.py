import hashlib
from pathlib import Path

from pipeline import build_report


DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


def test_dataset_is_unchanged():
    digest = hashlib.sha256(
        (DATA_DIR / 'train.csv').read_bytes()
        + (DATA_DIR / 'evaluation.csv').read_bytes()
    ).hexdigest()
    assert build_report()['dataset_sha256'] == digest


def test_pipeline_stages_and_monitoring_contract():
    report = build_report()
    assert report['train_rows'] == 24
    assert report['evaluation_rows'] == 12
    assert report['feature_columns'] == ['support_tickets', 'tenure_months']
    assert abs(report['baseline_accuracy'] - 8 / 12) < 1e-9
    assert report['stages'] == [
        'data_audit', 'classical_baseline', 'reproducible_training',
        'production_service', 'pytorch_model', 'integration_test',
    ]
    assert report['monitoring_signals'] == [
        'error_rate', 'latency', 'input_drift', 'prediction_drift',
    ]
    assert report['canary_rollback_defined'] is True
    assert report['evaluation_set_used_for_fitting'] is False
    assert report['data_split'] == 'fixed_holdout'


def test_model_comparison_and_selection():
    report = build_report()
    assert report['classical_accuracy'] >= .90
    assert report['pytorch_accuracy'] >= .80
    assert report['selected_model'] in {'classical_baseline', 'pytorch_mlp'}
