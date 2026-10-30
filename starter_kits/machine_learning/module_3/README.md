# Module 3 project: make a training run reproducible

Build a CPU-only training command that writes a run manifest for the fixed churn exercise dataset. The dataset is synthetic and copied unchanged from the Module 2 exercise. This project focuses on repeatability and provenance, not on finding a larger model.

## Requirements

- Keep `train.csv` and `evaluation.csv` unchanged and record a combined SHA-256 digest.
- Use seed `7`, the fixed feature list, a pipeline, and five-fold stratified cross-validation on training rows.
- Keep the fixed evaluation file out of fitting and parameter selection.
- Write a JSON manifest containing dataset digest, source revision, parameters, package versions, validation metric, fixed-set metrics, and artifact version.
- Run the training command twice and verify that predictions and metric values agree.
- Meet the fixed checks in `tests/test_run.py`.

Install from `pyproject.toml` with `python -m pip install -e '.[dev]'`, then run `pytest`. Implement `run_training` in `src/run.py`. After the checks pass, use `PYTHONPATH=src python -m run` to print the report JSON. The test workflow runs on CPU only.

The dataset is synthetic, contains no personal information, and was created for this exercise.
