from pathlib import Path

from vision_model import build_report, extract_features, train_and_predict

ROOT = Path(__file__).resolve().parents[1]


def test_features_are_extracted_for_every_image():
    import csv

    with (ROOT / 'data' / 'images.csv').open() as source:
        rows = list(csv.DictReader(source))
    features = extract_features(rows[0])
    assert len(features) >= 8
    assert all(isinstance(value, (int, float)) for value in features)


def test_predictions_cover_the_fixed_evaluation_split():
    train_and_predict()
    lines = (ROOT / 'artifacts' / 'predictions.csv').read_text().strip().splitlines()
    assert len(lines) == 11  # header + 10 evaluation images
    report = build_report()
    assert report['images_total'] == 30
    assert report['train_images'] == 20
    assert report['test_images'] == 10
    assert report['features_extracted'] == 30


def test_classifier_meets_fixed_thresholds():
    report = build_report()
    assert report['feature_count'] >= 8
    assert report['accuracy'] >= 0.80
    assert report['precision'] >= 0.75
    assert report['recall'] >= 0.75
    assert len(report['confusion_matrix']) == 4
    assert report['evaluation_set_used_for_fitting'] is False
    assert report['inference_script_present'] is True
