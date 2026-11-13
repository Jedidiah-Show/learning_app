# Module 4 project: compare a baseline with a tabular model, and price a house

Train a leakage-safe scikit-learn pipeline to identify fictional accounts likely to churn within 30 days, and fit a straight-line model that predicts house prices. The exercise data is synthetic. `train.csv` is for fitting and cross-validation; `evaluation.csv` is a fixed, held-out set for the final report; `houses.csv` is for the regression part, where the first 12 rows train the model and the last 4 rows test it.

## Requirements

- Compare against a `DummyClassifier` baseline on the same fixed evaluation rows.
- Fit imputation and scaling inside a scikit-learn `Pipeline`.
- Use only `support_tickets` and `tenure_months` as features. `cancelled_after_snapshot` is intentionally leaked post-outcome information.
- Use five-fold stratified cross-validation on training data for model selection.
- Report baseline accuracy and candidate accuracy, precision, recall, and F1 for the positive class.
- Keep the fixed evaluation data out of model fitting and threshold selection.
- Fit a house-price regression on the first 12 rows of `houses.csv`, predict the last 4 rows, and report MAE and R squared computed from your own predictions.
- Meet the deterministic test thresholds in `tests/test_model.py` and explain the trade-offs in your project reflection.

## The datasets

### `data/train.csv` and `data/evaluation.csv` (customer churn)

24 training rows and 12 evaluation rows. One row is one customer.

| Column | Type | Meaning |
| --- | --- | --- |
| `customer_id` | text | Identifier of the customer, for example `C001` in the training file and `E001` in the evaluation file. It is a label for a row, never a feature. |
| `support_tickets` | integer | Number of support tickets the customer opened in the last 12 months. Ranges from 0 to 5. |
| `tenure_months` | integer | How many months the customer has had an account. Ranges from 4 to 39. |
| `cancelled_after_snapshot` | integer | 1 when the account was cancelled after the snapshot date, 0 otherwise. This is recorded after the prediction moment, so using it is leakage and it must stay out of the feature list. |
| `churn_within_30_days` | integer | The target. 1 when the customer churned within 30 days, 0 otherwise. 16 of the 24 training rows and 8 of the 12 evaluation rows are 0, so always predicting 0 scores 8 of 12, which is 0.6667. |

### `data/houses.csv` (house prices)

16 rows, all used by the regression part. One row is one house.

| Column | Type | Meaning |
| --- | --- | --- |
| `size_sqm` | integer | Floor area of the house in square metres. Ranges from 48 to 120. |
| `bedrooms` | integer | Number of bedrooms. Ranges from 1 to 5. |
| `location_score` | integer | How good the location is, from 1 (weakest) to 5 (best). It is an ordinal rating, so a one-point rise is the same step everywhere. |
| `price` | integer | The asking price in the exercise currency. This is the target for the regression part. It ranges from 142000 to 448000. |

The first 12 rows are the training rows and the last 4 rows are the test rows. A least-squares fit on the first 12 rows reaches an MAE of about 5351 and an R squared of about 0.944 on the last 4 rows, so the checks ask for an MAE of at most 30000 and an R squared of at least 0.85.

## The report

`evaluate()` in `src/model.py` returns one dict with the classification keys `train_rows`, `evaluation_rows`, `baseline_accuracy`, `accuracy`, `precision`, `recall`, `f1`, `cross_validation_f1_mean`, `feature_columns`, `leakage_features`, `cross_validation_folds`, `preprocessing_in_pipeline`, `evaluation_set_used_for_fitting` and `data_split`, plus the regression keys `regression_train_rows`, `regression_test_rows`, `regression_mae`, `regression_r2` and `regression_features`. `regression_report()` returns the five regression keys and `evaluate()` merges them into the report.

## Run locally

Use Python 3.11 or newer. Create a virtual environment, then run:

```bash
python -m pip install -e '.[dev]'
pytest
```

The checks initially fail until `evaluate` and `regression_report` are implemented. Keep all three CSV files and the assertions intact. Commit the finished work and submit its public repository and passing CI run on the specialization page.

After the checks pass, print the report with `PYTHONPATH=src python -m model` and paste that JSON into the project submission form.

This dataset is synthetic, contains no personal information, and was created for the exercise.
