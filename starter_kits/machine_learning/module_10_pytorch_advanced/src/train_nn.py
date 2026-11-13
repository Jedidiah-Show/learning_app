"""Train a PyTorch neural network for the bundled synthetic churn data."""

from pathlib import Path
import json

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
TRAIN_PATH = DATA_DIR / 'train.csv'
EVALUATION_PATH = DATA_DIR / 'evaluation.csv'
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'
SEED = 7


def train_and_evaluate(train_path=TRAIN_PATH, evaluation_path=EVALUATION_PATH):
    """Return the comparison report described in README.md.

    Keep this function deterministic. Fit only on the training rows and use
    the evaluation rows once, after training, for the reported metrics.
    """
    raise NotImplementedError('Complete the PyTorch tabular model')


if __name__ == '__main__':
    print(json.dumps(train_and_evaluate(), sort_keys=True))
