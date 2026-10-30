# Module 2 project: compare a baseline with a tabular model

Train a leakage-safe scikit-learn pipeline to identify fictional accounts likely to churn within 30 days. The exercise data is synthetic. `train.csv` is for fitting and cross-validation; `evaluation.csv` is a fixed, held-out set for the final report.

## Requirements

- Compare against a `DummyClassifier` baseline on the same fixed evaluation rows.
- Fit imputation and scaling inside a scikit-learn `Pipeline`.
- Use only `support_tickets` and `tenure_months` as features. `cancelled_after_snapshot` is intentionally leaked post-outcome information.
- Use five-fold stratified cross-validation on training data for model selection.
- Report baseline accuracy and candidate accuracy, precision, recall, and F1 for the positive class.
- Keep the fixed evaluation data out of model fitting and threshold selection.
- Meet the deterministic test thresholds in `tests/test_model.py` and explain the trade-offs in your project reflection.

## Run locally

Use Python 3.11 or newer. Create a virtual environment, then run:

```bash
python -m pip install -e '.[dev]'
pytest
```

The checks initially fail until `evaluate` is implemented. Keep both CSV files and the assertions intact. Commit the finished work and submit its public repository and passing CI run on the specialization page.

After the checks pass, print the report with `PYTHONPATH=src python -m model` and paste that JSON into the project submission form.

This dataset is synthetic, contains no personal information, and was created for the exercise.
