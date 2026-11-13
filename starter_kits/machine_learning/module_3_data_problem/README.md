# Module 1 project: audit a prediction dataset

Build a small, repeatable audit for the synthetic order-return dataset in `data/orders.csv`. The business question is whether an order will be returned within 30 days. The prediction is made when the order is placed.

## Requirements

- Validate the table shape, required columns, and unique `order_id` values.
- Report missing and invalid `order_total` values without silently changing the source data.
- Count positive outcomes and describe the class balance.
- Identify `refund_reason` as unavailable at order placement and therefore a leakage feature.
- Use the first eight rows for development and the final four rows as a time-ordered evaluation set. Do not shuffle this fixed exercise dataset.
- Return the report fields asserted in `tests/test_audit.py`.

## Run locally

Use Python 3.11 or newer. Create a virtual environment, then run:

```bash
python -m pip install -e '.[dev]'
pytest
```

The starter checks fail until you implement `build_report` in `src/audit.py`. Do not change the dataset or weaken the expected checks. Commit your finished implementation and submit the public repository and successful CI run on the specialization page.

After the checks pass, print the report with `PYTHONPATH=src python -m audit` and paste that JSON into the project submission form.

This synthetic dataset is created for this exercise. It contains no personal information and has no external data license requirements.
