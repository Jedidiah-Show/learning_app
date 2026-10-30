"""Train and evaluate a leakage-safe churn classifier."""

from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'


def evaluate():
    """Return deterministic metrics for the fixed held-out evaluation set."""
    training = pd.read_csv(ROOT / 'data' / 'train.csv')
    evaluation = pd.read_csv(ROOT / 'data' / 'evaluation.csv')
    # Keep the fixed evaluation data out of fitting and model selection.
    # Build a DummyClassifier baseline, then a preprocessing + classifier
    # Pipeline. Use only FEATURE_COLUMNS; cancelled_after_snapshot is leakage.
    raise NotImplementedError('Build a baseline, pipeline, and fixed-set report')


if __name__ == '__main__':
    print(json.dumps(evaluate(), sort_keys=True))
