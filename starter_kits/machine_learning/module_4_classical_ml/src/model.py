"""Train and evaluate a leakage-safe churn classifier and a house-price regressor."""

from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'
REGRESSION_FEATURES = ['size_sqm', 'bedrooms', 'location_score']
REGRESSION_TARGET = 'price'


def regression_report():
    """Return the house-price part of the report.

    Read ``data/houses.csv``. Fit a straight-line model on the first 12 rows
    that predicts ``price`` from ``size_sqm``, ``bedrooms`` and
    ``location_score``, then predict the price of the last 4 rows.

    Return a dict with exactly these keys:

    * ``regression_train_rows``: int, how many rows you fitted on (12).
    * ``regression_test_rows``: int, how many rows you predicted (4).
    * ``regression_mae``: float, the average absolute error on those 4 rows,
      in the same currency units as ``price``.
    * ``regression_r2``: float, the share of the variation in the 4 prices
      your model explains, computed from your own predictions.
    * ``regression_features``: list of the three feature names you used.

    A least-squares fit with ``numpy.linalg.lstsq`` and an explicit column of
    ones for the intercept is enough. Compute MAE and R squared yourself from
    the predictions instead of hard-coding them.
    """
    raise NotImplementedError(
        'Fit the house-price regression on data/houses.csv and return the five '
        'regression_* keys'
    )


def evaluate():
    """Return deterministic metrics for the fixed held-out evaluation set."""
    training = pd.read_csv(ROOT / 'data' / 'train.csv')
    evaluation = pd.read_csv(ROOT / 'data' / 'evaluation.csv')
    # Keep the fixed evaluation data out of fitting and model selection.
    # Build a DummyClassifier baseline, then a preprocessing + classifier
    # Pipeline. Use only FEATURE_COLUMNS; cancelled_after_snapshot is leakage.
    # Merge the five regression_* keys from regression_report() into the
    # report you return.
    raise NotImplementedError('Build a baseline, pipeline, and fixed-set report')


if __name__ == '__main__':
    print(json.dumps(evaluate(), sort_keys=True))
