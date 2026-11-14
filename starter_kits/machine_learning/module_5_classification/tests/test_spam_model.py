from pathlib import Path

from spam_model import build_report, load_emails, train_and_predict

ROOT = Path(__file__).resolve().parents[1]


def test_dataset_split_is_fixed():
    training, evaluation = load_emails()
    assert len(training) == 24
    assert len(evaluation) == 12
    assert [row['email_id'][0] for row in training] == ['E'] * 24
    assert [row['email_id'][0] for row in evaluation] == ['T'] * 12


def test_predictions_cover_every_evaluation_email():
    train_and_predict()
    lines = (ROOT / 'artifacts' / 'predictions.csv').read_text().strip().splitlines()
    assert len(lines) == 13  # header + 12 evaluation rows


def test_candidate_meets_fixed_set_thresholds():
    report = build_report()
    assert report['train_rows'] == 24
    assert report['test_rows'] == 12
    assert report['baseline_accuracy'] == 0.5
    assert report['accuracy'] >= 0.85
    assert report['precision'] >= 0.80
    assert report['recall'] >= 0.80
    assert report['f1'] >= 0.80
    assert report['true_positives'] >= 5
    assert report['false_positives'] <= 2


def test_confusion_matrix_and_guards_are_reported():
    report = build_report()
    assert len(report['confusion_matrix']) == 4
    assert report['used_train_test_split'] is True
    assert report['evaluation_set_used_for_fitting'] is False
    assert report['model_family'] in {
        'logistic_regression', 'k_neighbors', 'decision_tree',
        'random_forest', 'gradient_boosting', 'naive_bayes',
    }
