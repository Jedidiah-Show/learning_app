"""Reference implementation of the Module 2 classical-ML baseline project."""

from pathlib import Path

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
    / 'starter_kits' / 'machine_learning' / 'module_2'
)
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'


def _pipeline():
    return Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(
            max_iter=1000, random_state=7, class_weight='balanced',
        )),
    ])


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
    return {
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
