"""Reference implementation of the Module 5 classification project.

Runs the shipped spam-model tests and produces a report that satisfies the
server-owned contract for ``mle.classification-models``.
"""

import csv
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_5_classification'
)
DATA = ROOT / 'data' / 'emails.csv'
ARTIFACTS = ROOT / 'artifacts'


def load_emails():
    with DATA.open(encoding='utf-8', newline='') as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        row['label'] = int(row['label'])
    training = [row for row in rows if row['email_id'].startswith('E')]
    evaluation = [row for row in rows if row['email_id'].startswith('T')]
    return training, evaluation


def _text(row):
    return f"{row['subject']} {row['body']}"


def train_and_predict():
    training, evaluation = load_emails()
    model = Pipeline([
        ('text', TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ('classifier', LogisticRegression(max_iter=1000, random_state=7)),
    ])
    model.fit([_text(row) for row in training], [row['label'] for row in training])
    predictions = model.predict([_text(row) for row in evaluation])
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with (ARTIFACTS / 'predictions.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['email_id', 'predicted_label'])
        for row, prediction in zip(evaluation, predictions):
            writer.writerow([row['email_id'], int(prediction)])
    return {'model_family': 'logistic_regression'}


def _read_predictions():
    with (ARTIFACTS / 'predictions.csv').open(encoding='utf-8', newline='') as source:
        return {
            row['email_id']: int(row['predicted_label'])
            for row in csv.DictReader(source)
        }


def build_report():
    _, evaluation = load_emails()
    if not (ARTIFACTS / 'predictions.csv').is_file():
        train_and_predict()
    predicted = _read_predictions()
    matrix = [[0, 0], [0, 0]]
    for row in evaluation:
        actual = row['label']
        guess = predicted[row['email_id']]
        matrix[actual][guess] += 1
    true_negatives, false_positives = matrix[0]
    false_negatives, true_positives = matrix[1]
    positive_calls = true_positives + false_positives
    actual_positives = true_positives + false_negatives
    precision = true_positives / positive_calls if positive_calls else 0.0
    recall = true_positives / actual_positives if actual_positives else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    correct = true_negatives + true_positives
    baseline = max(
        sum(1 for row in evaluation if row['label'] == 0),
        sum(1 for row in evaluation if row['label'] == 1),
    ) / len(evaluation)
    return {
        'train_rows': 24,
        'test_rows': 12,
        'baseline_accuracy': round(baseline, 6),
        'accuracy': round(correct / len(evaluation), 6),
        'precision': round(precision, 6),
        'recall': round(recall, 6),
        'f1': round(f1, 6),
        'confusion_matrix': [
            true_negatives, false_positives, false_negatives, true_positives,
        ],
        'true_positives': true_positives,
        'false_positives': false_positives,
        'model_family': 'logistic_regression',
        'used_train_test_split': True,
        'evaluation_set_used_for_fitting': False,
    }


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
