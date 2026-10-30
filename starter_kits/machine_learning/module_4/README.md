# Module 4 project: serve and operate a tabular model

Wrap the fitted churn pipeline in a small FastAPI service with validated single-row and batch contracts. Add a monitor that distinguishes input drift from model quality, and a release manager that can stop a canary and restore the last known-good model version.

## Requirements

- Load only a locally built, versioned pipeline artifact. Do not fetch model artifacts from request-provided URLs.
- Provide `/healthz`, `/predict`, and `/predict/batch` endpoints with explicit input and response schemas.
- Reject missing, negative, extra, and incorrectly typed features instead of silently coercing them.
- Include the model version in prediction responses and enforce a batch-size limit.
- Detect a synthetic input shift against a documented reference window; do not label drift alone as model-quality failure.
- Stop a canary when the fixed error-rate guardrail is crossed and restore the prior model version.
- Meet the deterministic service and operations checks in `tests/test_service.py`.

## Run locally

Use Python 3.11 or newer. Install pinned dependencies with `python -m pip install -e '.[dev]'`, then run `pytest`. Implement `train_and_save`, create the trusted local model artifact with `PYTHONPATH=src python -m train_model`, and start the service with `PYTHONPATH=src uvicorn service:app --host 127.0.0.1 --port 8000`. Produce the submission report with `PYTHONPATH=src python -c 'from project_report import build_report; from train_model import train_and_save; import joblib, json; print(json.dumps(build_report(joblib.load(train_and_save()))))'` after implementing the monitor and release controls.

This project uses the same synthetic exercise data as Modules 2 and 3. Keep it unchanged and include a runbook explaining alert ownership, canary stop conditions, and rollback steps.
