# Module 2 project: profile a dataset with statistics

Describe the bundled synthetic order data with statistics. A **data profile** is a small set of numbers that summarises a table: how many rows and columns it has, where its centre sits, how widely the values spread, how many values are missing or invalid, and the one rule you used to decide that a value is unusual. You will write a script that prints that profile as JSON, a test file that checks it, and a short write-up in this README.

## The dataset

`data/orders.csv` has 12 rows and 6 columns. It is synthetic, so it contains no personal information and has no external data license requirements.

| column | meaning |
| --- | --- |
| `order_id` | the order number, 1001 to 1012 |
| `order_date` | the date the order was placed, 2025-01-01 to 2025-01-12 |
| `order_total` | the money the customer paid, in dollars |
| `channel` | how the order was placed: `web`, `mobile` or `partner` |
| `returned_within_30_days` | `1` if the order came back within 30 days, `0` if not |
| `refund_reason` | why the order came back, blank when it did not come back |

Two rows are deliberately imperfect. Order 1004 has an empty `order_total`, and order 1007 has an `order_total` of `-5.00`.

## The numbers your report must contain

`build_report` in `src/profile.py` returns a dict with exactly these ten keys.

| key | type | value your report must contain |
| --- | --- | --- |
| `row_count` | int | 12 |
| `column_count` | int | 6 |
| `mean_order_total` | float | 38.29 (within 0.005) |
| `median_order_total` | float | 29.99 (within 0.005) |
| `stdev_order_total` | float | 30.6929 (within 0.02) |
| `missing_order_total_count` | int | 1 |
| `nonpositive_order_total_count` | int | 1 |
| `returned_count` | int | 4 |
| `return_rate` | float | 0.3333333333 (within 0.001) |
| `outlier_rule` | str | one sentence of at least 10 characters naming the rule you applied |

Two definitions decide the centre and spread figures, and you must use exactly these.

- **Present values.** The mean, the median and the standard deviation are computed over the rows where `order_total` is present. That is 11 of the 12 rows, because order 1004 is blank.
- **A negative total is still a present value.** The `-5.00` in order 1007 is a value that was recorded, so it is included in the mean, the median and the standard deviation. It is counted separately by `nonpositive_order_total_count`, which reports data quality rather than changing the numbers.
- **Population standard deviation.** Use `statistics.pstdev`, which divides the sum of squared distances by the count of values. That is the figure 30.6929. `statistics.stdev` divides by one less than the count and gives 32.19, which is the sample standard deviation and will not pass the check.

Check your own arithmetic before you run the tests: the 11 present totals are 24.50, 81.00, 17.25, 44.00, 12.75, -5.00, 63.20, 29.99, 15.00, 102.40 and 36.10. They add to 421.19, and 421.19 divided by 11 is 38.29.

## What to build

1. Open `data/orders.csv` with the `csv` module from the standard library. Read it inside `build_report`, every time the function is called. Never hard-code a number and never paste the table into your script.
2. Count the rows and the columns.
3. Collect the `order_total` values. A blank cell is missing, not zero. Count how many cells are blank for `missing_order_total_count`, and how many present values are zero or negative for `nonpositive_order_total_count`.
4. Compute the mean, the median and the population standard deviation of the present values with the `statistics` module: `statistics.fmean`, `statistics.median` and `statistics.pstdev`.
5. Count the rows where `returned_within_30_days` is `1` for `returned_count`, and divide that by `row_count` for `return_rate`.
6. Write your outlier rule as one sentence in `outlier_rule`. Say what makes a total unusual, not just that something was unusual. One usable rule for this data is that a total is unusual when it falls outside the middle 50 percent of the totals, which is below about 16.1 or above about 53.6 for these 11 values, and that rule flags six of the eleven totals. The check only asks for a sentence of at least 10 characters, so you must write it yourself, and you must be able to say which rows your own rule flags.

## Run locally

Use Python 3.11 or newer. Create a virtual environment, then run:

```bash
python -m pip install -e '.[dev]'
pytest
```

The checks fail until you implement `build_report` in `src/profile.py`. Do not change the dataset and do not weaken the expected checks. Commit your finished implementation and submit the public repository and the successful CI run on the specialization page.

After the checks pass, print the report with `PYTHONPATH=src python -m profile` and paste that JSON into the project submission form.

## The write-up

In this README, add a short section called `## What the numbers say` with the mean, the median and the spread of the order totals, the number of values you used, the two data quality problems you found, and the outlier rule you applied with the rows it flags. Say what the numbers mean for the data rather than repeating the table.

## Rubric

| criterion | weight |
| --- | --- |
| Summary statistics are computed correctly from the bundled data | 40 |
| Data quality problems are found and explained, not silently fixed | 30 |
| The write-up states the numbers and what they mean for the data | 30 |
