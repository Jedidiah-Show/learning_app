# Module 6 project: capstone integration

Integrate the work from Modules 1-5 into one reproducible pipeline on the shared synthetic churn dataset. The capstone is about the seams between stages: data audit, classical baseline, reproducible training, production serving, the PyTorch model, and an end-to-end integration test.

## Requirements

- Reuse the Module 1 data contract, the Module 2 classical baseline, the Module 3 reproducibility manifest, the Module 4 service-and-monitor design, and the Module 5 PyTorch model.
- Keep `support_tickets` and `tenure_months` as the only features. `cancelled_after_snapshot` remains leaked post-outcome information.
- Run every stage on the same fixed split: fit on `train.csv`, evaluate once on `evaluation.csv`.
- Record the ordered pipeline stages in the report.
- Document the monitoring signals the deployed pipeline exposes: error rate, latency, input drift, and prediction drift.
- Define canary stop conditions and the rollback path to the last known-good model version.
- Choose the model the pipeline deploys (`classical_baseline` or `pytorch_mlp`) and justify it in your reflection.
- Meet the deterministic checks in `tests/test_pipeline.py`.

## Run locally

Use Python 3.11 or newer. Create a virtual environment, then run:

```bash
python -m pip install -e '.[dev]'
pytest
```

The checks initially fail until `build_report` is implemented in `src/pipeline.py`. Keep both CSV files and the assertions intact. Commit the finished work and submit its public repository and passing CI run on the specialization page.

After the checks pass, print the report with `PYTHONPATH=src python -m pipeline` and paste that JSON into the project submission form.

This dataset is synthetic, contains no personal information, and was created for the exercise.
