"""Reference implementation of the Module 2 classical-ML baseline project."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_4_classical_ml'
)
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'
REGRESSION_FEATURES = ['size_sqm', 'bedrooms', 'location_score']
REGRESSION_TARGET = 'price'
REGRESSION_TRAIN_ROWS = 12


def _pipeline():
    return Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(
            max_iter=1000, random_state=7, class_weight='balanced',
        )),
    ])


def regression_report():
    """Fit a straight-line price model on the first 12 houses and score the last 4.

    A least-squares fit with an explicit intercept column is enough. MAE and
    R squared are computed from the predictions of those 4 rows.
    """
    houses = pd.read_csv(ROOT / 'data' / 'houses.csv')
    features = REGRESSION_FEATURES
    values = houses[features].to_numpy(dtype=float)
    prices = houses[REGRESSION_TARGET].to_numpy(dtype=float)

    train_values = values[:REGRESSION_TRAIN_ROWS]
    train_prices = prices[:REGRESSION_TRAIN_ROWS]
    test_values = values[REGRESSION_TRAIN_ROWS:]
    test_prices = prices[REGRESSION_TRAIN_ROWS:]

    design = np.hstack([train_values, np.ones((train_values.shape[0], 1))])
    coefficients, *_ = np.linalg.lstsq(design, train_prices, rcond=None)
    test_design = np.hstack([test_values, np.ones((test_values.shape[0], 1))])
    predicted = test_design @ coefficients

    errors = test_prices - predicted
    mae = float(np.abs(errors).mean())
    residual = float((errors ** 2).sum())
    total = float(((test_prices - test_prices.mean()) ** 2).sum())
    r2 = float(1 - residual / total)

    return {
        'regression_train_rows': int(train_values.shape[0]),
        'regression_test_rows': int(test_values.shape[0]),
        'regression_mae': mae,
        'regression_r2': r2,
        'regression_features': list(features),
    }


def evaluate():
    training = pd.read_csv(ROOT / 'data' / 'train.csv')
    evaluation = pd.read_csv(ROOT / 'data' / 'evaluation.csv')
    X_train, y_train = training[FEATURE_COLUMNS], training[TARGET_COLUMN]
    X_eval, y_eval = evaluation[FEATURE_COLUMNS], evaluation[TARGET_COLUMN]

    baseline = DummyClassifier(strategy='most_frequent').fit(X_train, y_train)
    model = _pipeline().fit(X_train, y_train)

    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
    scores = cross_validate(
        _pipeline(), X_train, y_train, cv=folds, scoring='f1',
    )

    predicted = model.predict(X_eval)
    report = {
        'train_rows': int(len(training)),
        'evaluation_rows': int(len(evaluation)),
        'baseline_accuracy': float(accuracy_score(y_eval, baseline.predict(X_eval))),
        'accuracy': float(accuracy_score(y_eval, predicted)),
        'precision': float(precision_score(y_eval, predicted, zero_division=0)),
        'recall': float(recall_score(y_eval, predicted, zero_division=0)),
        'f1': float(f1_score(y_eval, predicted, zero_division=0)),
        'cross_validation_f1_mean': float(scores['test_score'].mean()),
        'feature_columns': list(FEATURE_COLUMNS),
        'leakage_features': ['cancelled_after_snapshot'],
        'cross_validation_folds': 5,
        'preprocessing_in_pipeline': True,
        'evaluation_set_used_for_fitting': False,
        'data_split': 'fixed_holdout',
    }
    report.update(regression_report())
    return report
