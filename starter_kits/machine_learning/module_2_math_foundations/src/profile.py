"""Profile the bundled synthetic order data with descriptive statistics.

Implement ``build_report`` so that it reads ``data/orders.csv`` at call time
and returns the data profile described in README.md. The standard library is
enough: ``csv`` to read the file and ``statistics`` to summarise it.
"""

from pathlib import Path
import json


DATA_PATH = Path(__file__).resolve().parents[1] / 'data' / 'orders.csv'

REPORT_KEYS = (
    'row_count',
    'column_count',
    'mean_order_total',
    'median_order_total',
    'stdev_order_total',
    'missing_order_total_count',
    'nonpositive_order_total_count',
    'returned_count',
    'return_rate',
    'outlier_rule',
)


def build_report(data_path=DATA_PATH):
    """Return the data profile of the orders dataset as a dict.

    Read ``data_path``, a CSV file with the six bundled columns
    ``order_id``, ``order_date``, ``order_total``, ``channel``,
    ``returned_within_30_days`` and ``refund_reason``, and return a dict with
    exactly these keys:

    row_count                     int    number of data rows
    column_count                  int    number of columns
    mean_order_total              float  mean of the order totals that are present
    median_order_total            float  median of the order totals that are present
    stdev_order_total             float  population standard deviation of those totals
    missing_order_total_count     int    rows where order_total is empty
    nonpositive_order_total_count int    present rows whose order_total is zero or negative
    returned_count                int    rows where returned_within_30_days is 1
    return_rate                   float  returned_count divided by row_count
    outlier_rule                  str    one sentence naming the rule you applied

    The centre and spread figures are computed over the rows where
    ``order_total`` is present, which is 11 of the 12 rows, and the negative
    total counts as a present value. Use ``statistics.pstdev`` for the
    population standard deviation. Compute every number from the file on
    every call; nothing may be hard-coded, and the file may not be edited.
    """
    raise NotImplementedError('Complete the data profile in build_report')


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
