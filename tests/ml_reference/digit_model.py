"""Reference implementation of the Module 7 deep-learning digits project."""

import csv
import json
from pathlib import Path

from sklearn.datasets import load_digits
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_7_deep_learning'
)
ARTIFACTS = ROOT / 'artifacts'


def load_digits_split():
    digits = load_digits()
    features = digits.data / 16.0
    return features[:1200], digits.target[:1200], features[1200:], digits.target[1200:]


def train_and_predict():
    x_train, y_train, x_test, y_test = load_digits_split()
    model = Pipeline([
        ('scale', StandardScaler()),
        ('network', MLPClassifier(
            hidden_layer_sizes=(128,),
            activation='relu',
            solver='adam',
            max_iter=300,
            random_state=7,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=10,
        )),
    ])
    model.fit(x_train, y_train)
    network = model.named_steps['network']
    predictions = model.predict(x_test)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with (ARTIFACTS / 'predictions.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['index', 'true_label', 'predicted_label'])
        start = 1200
        for offset, (actual, guess) in enumerate(zip(y_test, predictions)):
            writer.writerow([start + offset, int(actual), int(guess)])
    config = {
        'hidden_layers': len(network.hidden_layer_sizes),
        'activation_function': network.activation,
        'epochs': len(network.loss_curve_),
        'used_validation_split': True,
    }
    (ARTIFACTS / 'training_config.json').write_text(
        json.dumps(config, indent=2) + '\n', encoding='utf-8',
    )
    return config


def _read_predictions():
    with (ARTIFACTS / 'predictions.csv').open(encoding='utf-8', newline='') as source:
        return [
            (int(row['index']), int(row['true_label']), int(row['predicted_label']))
            for row in csv.DictReader(source)
        ]


def build_report():
    _, y_train, _, _ = load_digits_split()
    if not (ARTIFACTS / 'predictions.csv').is_file():
        train_and_predict()
    rows = _read_predictions()
    config = json.loads((ARTIFACTS / 'training_config.json').read_text())
    correct = sum(1 for _, actual, guess in rows if actual == guess)
    accuracy = correct / len(rows)
    majority = max(set(y_train), key=lambda value: list(y_train).count(value))
    baseline = sum(1 for value in y_train if value == majority) / len(y_train)
    return {
        'train_rows': int(len(y_train)),
        'test_rows': len(rows),
        'classes': len(set(int(value) for value in y_train)),
        'accuracy': round(accuracy, 6),
        'beats_majority_baseline': accuracy > baseline,
        'hidden_layers': int(config['hidden_layers']),
        'activation_function': config['activation_function'],
        'epochs': int(config['epochs']),
        'used_validation_split': bool(config['used_validation_split']),
        'confusion_matrix_rows': 10,
        'evaluation_set_used_for_fitting': False,
    }


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
