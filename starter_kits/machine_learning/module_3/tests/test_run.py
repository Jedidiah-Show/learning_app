from run import run_training


def test_manifest_identifies_fixed_inputs_and_run_controls():
    report = run_training()
    assert report['train_rows'] == 24
    assert report['evaluation_rows'] == 12
    assert report['seed'] == 7
    assert len(report['dataset_sha256']) == 64
    assert report['feature_columns'] == ['support_tickets', 'tenure_months']
    assert report['artifact_version'] == '1.0.0'
    assert report['run_manifest_fields'] == [
        'artifact_version', 'dataset_sha256', 'feature_columns', 'fixed_metrics',
        'parameters', 'package_versions', 'source_revision', 'training_seed',
        'validation_f1_mean',
    ]


def test_repeated_run_and_fixed_evaluation_are_reproducible():
    report = run_training()
    assert report['repeated_run_predictions_match'] is True
    assert report['evaluation_set_used_for_fitting'] is False
    assert report['accuracy'] >= 0.90
    assert report['f1'] >= 0.80
    assert report['validation_f1_mean'] >= 0.80
