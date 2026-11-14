"""Train and evaluate an email spam classifier."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
DATA = ROOT / 'data' / 'emails.csv'


def load_emails():
    """Load the bundled emails and return (training, evaluation) rows.

    Each row is a dict with ``email_id``, ``subject``, ``body`` and ``label``.
    Training rows start with ``E``; evaluation rows start with ``T``.
    """
    raise NotImplementedError('Read data/emails.csv and split E…/T… rows')


def train_and_predict():
    """Fit your classifiers and write artifacts/predictions.csv.

    Return a dict with your chosen model's evaluation predictions, or simply
    write the CSV and recompute the report in ``build_report()``.
    """
    raise NotImplementedError(
        'Train at least two classifiers and write artifacts/predictions.csv '
        'with email_id,predicted_label'
    )


def build_report():
    """Return the report described in README.md.

    The metrics must be computed from ``artifacts/predictions.csv`` and the
    evaluation labels in ``data/emails.csv``. Do not return hard-coded values.
    """
    raise NotImplementedError('Compute the report from artifacts/predictions.csv')


if __name__ == '__main__':
    train_and_predict()
    print(json.dumps(build_report(), sort_keys=True))
