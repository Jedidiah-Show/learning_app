"""Reference implementation of the Module 8 computer-vision project."""

import csv
import json
import statistics
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_8_computer_vision'
)
DATA = ROOT / 'data' / 'images.csv'
ARTIFACTS = ROOT / 'artifacts'


def _pixels(image):
    return [int(image[f'p{index}']) for index in range(64)]


def extract_features(image):
    pixels = _pixels(image)
    grid = [pixels[row * 8:(row + 1) * 8] for row in range(8)]
    columns = [[grid[row][column] for row in range(8)] for column in range(8)]
    horizontal_edges = sum(
        abs(grid[row][column] - grid[row][column + 1])
        for row in range(8) for column in range(7)
    )
    vertical_edges = sum(
        abs(grid[row][column] - grid[row + 1][column])
        for row in range(7) for column in range(8)
    )
    return [
        round(statistics.fmean(pixels), 6),
        round(statistics.pstdev(pixels), 6),
        min(pixels),
        max(pixels),
        round(statistics.fmean(pixels[:32]), 6),
        round(statistics.fmean(pixels[32:]), 6),
        round(statistics.fmean(columns[0] + columns[1] + columns[2] + columns[3]), 6),
        round(statistics.fmean(columns[4] + columns[5] + columns[6] + columns[7]), 6),
        horizontal_edges,
        vertical_edges,
    ]


def _load_images():
    with DATA.open(encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        row['label'] = int(row['label'])
    return rows


def train_and_predict():
    rows = _load_images()
    training = [row for row in rows if row['image_id'].startswith('I')]
    evaluation = [row for row in rows if row['image_id'].startswith('T')]
    features = {row['image_id']: extract_features(row) for row in rows}
    model = Pipeline([
        ('scale', StandardScaler()),
        ('classifier', LogisticRegression(max_iter=1000, random_state=7)),
    ])
    model.fit(
        [features[row['image_id']] for row in training],
        [row['label'] for row in training],
    )
    predictions = model.predict([features[row['image_id']] for row in evaluation])
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    width = len(next(iter(features.values())))
    with (ARTIFACTS / 'features.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['image_id'] + [f'f{index}' for index in range(width)])
        for row in rows:
            writer.writerow([row['image_id']] + features[row['image_id']])
    with (ARTIFACTS / 'predictions.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['image_id', 'predicted_label'])
        for row, prediction in zip(evaluation, predictions):
            writer.writerow([row['image_id'], int(prediction)])


def build_report():
    rows = _load_images()
    if not (ARTIFACTS / 'predictions.csv').is_file():
        train_and_predict()
    with (ARTIFACTS / 'predictions.csv').open(encoding='utf-8', newline='') as source:
        predicted = {
            row['image_id']: int(row['predicted_label'])
            for row in csv.DictReader(source)
        }
    evaluation = [row for row in rows if row['image_id'].startswith('T')]
    matrix = [[0, 0], [0, 0]]
    for row in evaluation:
        matrix[row['label']][predicted[row['image_id']]] += 1
    true_negatives, false_positives = matrix[0]
    false_negatives, true_positives = matrix[1]
    positive_calls = true_positives + false_positives
    actual_positives = true_positives + false_negatives
    precision = true_positives / positive_calls if positive_calls else 0.0
    recall = true_positives / actual_positives if actual_positives else 0.0
    correct = true_negatives + true_positives
    return {
        'images_total': len(rows),
        'train_images': 20,
        'test_images': 10,
        'feature_count': 10,
        'features_extracted': len(rows),
        'accuracy': round(correct / len(evaluation), 6),
        'precision': round(precision, 6),
        'recall': round(recall, 6),
        'confusion_matrix': [
            true_negatives, false_positives, false_negatives, true_positives,
        ],
        'inference_script_present': (ROOT / 'src' / 'inference.py').is_file(),
        'evaluation_set_used_for_fitting': False,
    }


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
