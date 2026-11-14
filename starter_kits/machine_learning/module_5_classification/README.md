# Module 5 project: classify email as spam or not spam

Train at least two classifiers on the bundled email dataset, compare them on the
same fixed evaluation rows, and report precision, recall and F1 together with a
confusion matrix. The dataset is synthetic and contains no personal data.

## Requirements

- Use `data/emails.csv`. Rows `E001`–`E024` are training rows; rows `T001`–`T012`
  are the fixed evaluation rows (six spam, six not spam).
- Train at least two model families on the same split.
- Keep the evaluation rows out of fitting and threshold selection.
- Write one prediction per evaluation email to `artifacts/predictions.csv`
  with columns `email_id,predicted_label`.
- `build_report()` must recompute the metrics from that predictions file rather
  than returning hard-coded numbers.
- Meet the deterministic thresholds in `tests/test_spam_model.py` and explain
  the false positives and false negatives in your reflection.

## The dataset

| Column | Meaning |
| --- | --- |
| `email_id` | Row identifier. `E…` rows train, `T…` rows evaluate. |
| `subject` | Email subject line. |
| `body` | Email body text. |
| `label` | 1 = spam, 0 = not spam. |

## The report

`build_report()` in `src/spam_model.py` returns exactly:

`train_rows`, `test_rows`, `baseline_accuracy`, `accuracy`, `precision`,
`recall`, `f1`, `confusion_matrix`, `true_positives`, `false_positives`,
`model_family`, `used_train_test_split`, `evaluation_set_used_for_fitting`.

`confusion_matrix` is `[true_negatives, false_positives, false_negatives,
true_positives]` in that order. The baseline is always predicting the majority
class, which scores 0.5 on the balanced evaluation set.

## Run locally

```bash
python -m pip install -e '.[dev]'
pytest
PYTHONPATH=src python -m spam_model
```

Paste the printed JSON into the project submission form after CI passes.
