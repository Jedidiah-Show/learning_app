"""Reference implementation of the Module 1 data-audit project.

Kept outside ``starter_kits`` so learner downloads stay stubbed. CI runs the
shipped kit tests against this file and compares the output with the
server-owned report contract (Stage A of machine_learning_pathway.md).
"""

from pathlib import Path

import pandas as pd


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_1' / 'data' / 'orders.csv'
)
REQUIRED_COLUMNS = {
    'order_id', 'order_date', 'order_total', 'channel',
    'returned_within_30_days', 'refund_reason',
}


def build_report(data_path=DATA_PATH):
    frame = pd.read_csv(data_path)
    totals = pd.to_numeric(frame['order_total'], errors='coerce')
    return {
        'row_count': int(len(frame)),
        'required_columns_present': bool(REQUIRED_COLUMNS.issubset(frame.columns)),
        'unique_order_ids': int(frame['order_id'].nunique()),
        'missing_order_total_count': int(frame['order_total'].isna().sum()),
        'nonpositive_order_total_count': int((totals <= 0).sum()),
        'returned_count': int((frame['returned_within_30_days'] == 1).sum()),
        'development_rows': 8,
        'evaluation_rows': 4,
        'split_strategy': 'time_ordered',
        'leakage_features': ['refund_reason'],
    }
