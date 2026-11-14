from pathlib import Path

from digit_model import build_report, load_digits_split, train_and_predict

ROOT = Path(__file__).resolve().parents[1]


def test_fixed_split_sizes_and_classes():
    _, _, _, _ = load_digits_split()
    report = build_report()
    assert report['train_rows'] == 1200
    assert report['test_rows'] == 597
    assert report['classes'] == 10


def test_network_beats_the_majority_baseline():
    train_and_predict()
    report = build_report()
    assert report['accuracy'] >= 0.90
    assert report['beats_majority_baseline'] is True


def test_training_configuration_is_recorded():
    report = build_report()
    assert report['hidden_layers'] >= 1
    assert report['activation_function'] in {'relu', 'tanh', 'sigmoid'}
    assert report['epochs'] >= 5
    assert report['used_validation_split'] is True
    assert report['confusion_matrix_rows'] == 10
    assert report['evaluation_set_used_for_fitting'] is False


def test_predictions_file_covers_the_evaluation_rows():
    train_and_predict()
    lines = (ROOT / 'artifacts' / 'predictions.csv').read_text().strip().splitlines()
    assert len(lines) == 598  # header + 597 evaluation rows
