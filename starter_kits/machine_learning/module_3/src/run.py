"""Create a repeatable training run and provenance manifest."""

from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'
SEED = 7


def run_training():
    """Train, evaluate, and return the manifest fields required by README."""
    training = pd.read_csv(ROOT / 'data' / 'train.csv')
    evaluation = pd.read_csv(ROOT / 'data' / 'evaluation.csv')
    # Add a training pipeline, training-only cross-validation, a fixed-set
    # report, a dataset digest, and a repeat-run comparison. Do not fit on the
    # evaluation frame.
    raise NotImplementedError('Implement the repeatable training run')


if __name__ == '__main__':
    print(json.dumps(run_training(), sort_keys=True))
