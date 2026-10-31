"""Serve a versioned tabular model with strict input contracts."""

from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_4' / 'artifacts' / 'model.joblib'
)
MODEL_VERSION = '1.0.0'
MAX_BATCH_SIZE = 100


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    support_tickets: int = Field(ge=0, le=1000)
    tenure_months: int = Field(ge=0, le=1200)


class BatchInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    records: list[PredictionInput] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


def create_app(model=None):
    """Inject a fitted trusted pipeline for tests or load the local artifact."""
    if model is None and ARTIFACT_PATH.exists():
        model = joblib.load(ARTIFACT_PATH)
    app = FastAPI(title='Tabular churn inference', version=MODEL_VERSION)
    app.state.model = model

    @app.get('/healthz')
    def healthz():
        if app.state.model is None:
            raise HTTPException(status_code=503, detail='Model artifact is unavailable')
        return {'status': 'ok', 'model_version': MODEL_VERSION}

    @app.post('/predict')
    def predict(record: PredictionInput):
        if app.state.model is None:
            raise HTTPException(status_code=503, detail='Model artifact is unavailable')
        frame = pd.DataFrame([record.model_dump()])
        prediction = int(app.state.model.predict(frame)[0])
        probabilities = app.state.model.predict_proba(frame)[0]
        return {
            'prediction': prediction,
            'probability': float(probabilities[1]),
            'model_version': MODEL_VERSION,
        }

    @app.post('/predict/batch')
    def predict_batch(batch: BatchInput):
        if app.state.model is None:
            raise HTTPException(status_code=503, detail='Model artifact is unavailable')
        frame = pd.DataFrame([record.model_dump() for record in batch.records])
        predictions = app.state.model.predict(frame)
        probabilities = app.state.model.predict_proba(frame)[:, 1]
        return {
            'predictions': [
                {
                    'prediction': int(prediction),
                    'probability': float(probability),
                    'model_version': MODEL_VERSION,
                }
                for prediction, probability in zip(predictions, probabilities)
            ]
        }

    return app


app = create_app()
