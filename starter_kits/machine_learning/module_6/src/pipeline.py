"""Integrate the pathway projects into one reproducible pipeline report."""

from pathlib import Path
import json

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
TRAIN_PATH = DATA_DIR / 'train.csv'
EVALUATION_PATH = DATA_DIR / 'evaluation.csv'
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'
SEED = 7
STAGES = [
    'data_audit', 'classical_baseline', 'reproducible_training',
    'production_service', 'pytorch_model', 'integration_test',
]
MONITORING_SIGNALS = [
    'error_rate', 'latency', 'input_drift', 'prediction_drift',
]


def build_report(train_path=TRAIN_PATH, evaluation_path=EVALUATION_PATH):
    """Return the capstone report described in README.md.

    Fit on the training rows only, evaluate once on the fixed evaluation
    rows, and keep every stage reproducible from the recorded seed.
    """
    raise NotImplementedError('Complete the capstone integration pipeline')


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
