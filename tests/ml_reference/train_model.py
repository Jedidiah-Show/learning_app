"""Reference training entry for the Module 4 artifact."""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_4'
)


def train_and_save():
    training = pd.read_csv(ROOT / 'data' / 'train.csv')
    features = ['support_tickets', 'tenure_months']
    model = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(max_iter=1000, random_state=7)),
    ])
    model.fit(training[features], training['churn_within_30_days'])
    output = ROOT / 'artifacts' / 'model.joblib'
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    return output
