import hashlib
from pathlib import Path

from train_nn import train_and_evaluate


DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


def test_dataset_is_unchanged():
    digest = hashlib.sha256(
        (DATA_DIR / 'train.csv').read_bytes()
        + (DATA_DIR / 'evaluation.csv').read_bytes()
    ).hexdigest()
    assert train_and_evaluate()['dataset_sha256'] == digest


def test_report_contract_and_baseline_comparison():
    report = train_and_evaluate()
    assert report['train_rows'] == 24
    assert report['evaluation_rows'] == 12
    assert report['feature_columns'] == ['support_tickets', 'tenure_months']
    assert abs(report['baseline_accuracy'] - 8 / 12) < 1e-9
    assert report['model_family'] == 'pytorch_mlp'
    assert report['experiment_tracking'] is True
    assert report['beats_baseline'] is True
    assert report['evaluation_set_used_for_fitting'] is False
    assert report['data_split'] == 'fixed_holdout'


def test_metrics_meet_the_fixed_thresholds():
    report = train_and_evaluate()
    assert report['accuracy'] >= .90
    assert report['precision'] >= .80
    assert report['recall'] >= .80
    assert report['f1'] >= .80
