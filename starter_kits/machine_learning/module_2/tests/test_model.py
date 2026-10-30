from model import evaluate


def test_baseline_is_reported_on_the_fixed_evaluation_set():
    report = evaluate()
    assert report['train_rows'] == 24
    assert report['evaluation_rows'] == 12
    assert report['baseline_accuracy'] == 8 / 12


def test_candidate_meets_fixed_set_metric_thresholds():
    report = evaluate()
    assert report['accuracy'] >= 0.90
    assert report['precision'] >= 0.80
    assert report['recall'] >= 0.80
    assert report['f1'] >= 0.80
    assert report['cross_validation_f1_mean'] >= 0.80


def test_pipeline_excludes_post_outcome_leakage():
    report = evaluate()
    assert report['feature_columns'] == ['support_tickets', 'tenure_months']
    assert report['leakage_features'] == ['cancelled_after_snapshot']
    assert report['cross_validation_folds'] == 5
