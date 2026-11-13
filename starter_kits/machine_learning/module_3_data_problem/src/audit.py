"""Implement a deterministic audit for the bundled synthetic order data."""

from pathlib import Path
import json

import pandas as pd


DATA_PATH = Path(__file__).resolve().parents[1] / 'data' / 'orders.csv'
REQUIRED_COLUMNS = {
    'order_id', 'order_date', 'order_total', 'channel',
    'returned_within_30_days', 'refund_reason',
}


def build_report(data_path=DATA_PATH):
    """Return the audit report described in README.md.

    Keep this function deterministic. Do not change the dataset or the
    development/evaluation boundary to make the expected checks pass.
    """
    raise NotImplementedError('Complete the dataset audit')


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
