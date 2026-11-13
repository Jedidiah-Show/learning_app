# Module 5 project: a PyTorch model for tabular data

Train a PyTorch neural network to predict fictional churn from the same synthetic dataset used in Module 2. `train.csv` is for fitting and validation; `evaluation.csv` is a fixed, held-out set for the final comparison against the classical baseline.

## Requirements

- Use only `support_tickets` and `tenure_months` as features. `cancelled_after_snapshot` is leaked post-outcome information.
- Build and train a feedforward PyTorch model (`nn.Module`) with a deterministic training loop and a fixed random seed.
- Compare the neural network with the `DummyClassifier` baseline and the Module 2 classical baseline on the same fixed evaluation rows.
- Keep the evaluation data out of model fitting and threshold selection.
- Track the experiment: record the seed, epoch count, optimizer, learning rate, and the metrics needed to reproduce the result.
- Report accuracy, precision, recall, and F1 for the positive class.
- Meet the deterministic checks in `tests/test_train_nn.py` and explain the comparison in your project reflection.

## Run locally

Use Python 3.11 or newer. Create a virtual environment, then run:

```bash
python -m pip install -e '.[dev]'
pytest
```

The checks initially fail until `train_and_evaluate` is implemented in `src/train_nn.py`. Keep both CSV files and the assertions intact. Commit the finished work and submit its public repository and passing CI run on the specialization page.

After the checks pass, print the report with `PYTHONPATH=src python -m train_nn` and paste that JSON into the project submission form.

This dataset is synthetic, contains no personal information, and was created for the exercise.
