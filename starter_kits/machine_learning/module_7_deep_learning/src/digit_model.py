"""Train a small neural network on the scikit-learn digits dataset."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'


def load_digits_split():
    """Return (X_train, y_train, X_test, y_test) using the fixed split.

    Rows 0–1199 train, rows 1200–1796 evaluate. Scale the pixel values to the
    range 0–1 before training.
    """
    raise NotImplementedError('Load sklearn digits and apply the fixed split')


def train_and_predict():
    """Train the network and write predictions plus training_config.json.

    Return the report dict, or write the artifacts and let ``build_report()``
    recompute the report.
    """
    raise NotImplementedError(
        'Train a neural network, write artifacts/predictions.csv and '
        'artifacts/training_config.json'
    )


def build_report():
    """Return the report described in README.md.

    Recompute accuracy and the confusion matrix from
    ``artifacts/predictions.csv`` and the saved training configuration.
    """
    raise NotImplementedError('Compute the report from your artifacts')


if __name__ == '__main__':
    train_and_predict()
    print(json.dumps(build_report(), sort_keys=True))
