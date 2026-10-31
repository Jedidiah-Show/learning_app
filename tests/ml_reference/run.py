"""Reference implementation of the Module 3 reproducible-training project."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_3'
)
FEATURE_COLUMNS = ['support_tickets', 'tenure_months']
TARGET_COLUMN = 'churn_within_30_days'
SEED = 7
ARTIFACT_VERSION = '1.0.0'
RUN_MANIFEST_FIELDS = [
    'artifact_version', 'dataset_sha256', 'feature_columns', 'fixed_metrics',
    'parameters', 'package_versions', 'source_revision', 'training_seed',
    'validation_f1_mean',
]


def _dataset_digest():
    train = (ROOT / 'data' / 'train.csv').read_bytes()
    evaluation = (ROOT / 'data' / 'evaluation.csv').read_bytes()
    return hashlib.sha256(train + evaluation).hexdigest()


def _train_once():
    training = pd.read_csv(ROOT / 'data' / 'train.csv')
    model = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(max_iter=1000, random_state=SEED)),
    ])
    model.fit(training[FEATURE_COLUMNS], training[TARGET_COLUMN])
    return model


def run_training():
    training = pd.read_csv(ROOT / 'data' / 'train.csv')
    evaluation = pd.read_csv(ROOT / 'data' / 'evaluation.csv')
    X_train, y_train = training[FEATURE_COLUMNS], training[TARGET_COLUMN]
    X_eval, y_eval = evaluation[FEATURE_COLUMNS], evaluation[TARGET_COLUMN]

    first = _train_once()
    second = _train_once()
    predictions_match = bool(
        np.array_equal(first.predict(X_eval), second.predict(X_eval))
        and np.allclose(first.predict_proba(X_eval), second.predict_proba(X_eval))
    )

    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_scores = cross_validate(first, X_train, y_train, cv=folds, scoring='f1')
    predicted = first.predict(X_eval)

    accuracy = float(accuracy_score(y_eval, predicted))
    return {
        'train_rows': int(len(training)),
        'evaluation_rows': int(len(evaluation)),
        'seed': SEED,
        'dataset_sha256': _dataset_digest(),
        'feature_columns': list(FEATURE_COLUMNS),
        'artifact_version': ARTIFACT_VERSION,
        'run_manifest_fields': list(RUN_MANIFEST_FIELDS),
        'repeated_run_predictions_match': predictions_match,
        'evaluation_set_used_for_fitting': False,
        'accuracy': accuracy,
        'f1': float(f1_score(y_eval, predicted, zero_division=0)),
        'validation_f1_mean': float(cv_scores['test_score'].mean()),
    }
