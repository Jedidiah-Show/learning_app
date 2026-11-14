# Module 7 project: classify handwritten digits

Train a small neural network on the bundled scikit-learn digits dataset and
report its performance on a fixed held-out split. Watch the training and
validation curves and describe where the model fails.

## Requirements

- Load the digits with `sklearn.datasets.load_digits()`.
- Use rows 0–1199 for training and rows 1200–1796 for the fixed evaluation set.
- Hold out part of the training rows for validation. Never fit on the evaluation
  rows or use them to choose hyperparameters.
- Write `artifacts/predictions.csv` with `index,true_label,predicted_label` for
  every evaluation row.
- Write `artifacts/training_config.json` with `hidden_layers`,
  `activation_function`, `epochs` and `used_validation_split`.
- `build_report()` recomputes accuracy and the confusion matrix from the
  predictions file.

## The report

`build_report()` in `src/digit_model.py` returns exactly:

`train_rows`, `test_rows`, `classes`, `accuracy`, `beats_majority_baseline`,
`hidden_layers`, `activation_function`, `epochs`, `used_validation_split`,
`confusion_matrix_rows`, `evaluation_set_used_for_fitting`.

The majority baseline is the most common digit in the training rows.

## Run locally

```bash
python -m pip install -e '.[dev]'
pytest
PYTHONPATH=src python -m digit_model
```
