"""Reference implementation of the Module 2 data-profile project.

Kept outside ``starter_kits`` so learner downloads stay stubbed. The kit's own
test file runs against this file, so it proves the project is satisfiable with
the standard library alone.
"""

from pathlib import Path
import csv
import json
import statistics


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_2_math_foundations'
    / 'data' / 'orders.csv'
)


def build_report(data_path=DATA_PATH):
    """Return the data profile of the orders dataset as a dict.

    The contract is the one in the kit README and in ``tests/test_profile.py``:
    row and column counts, the centre and spread of the order totals that are
    present, the two data quality counts, the return count and rate, and one
    sentence naming the outlier rule. Every value is computed from the file
    on every call.
    """
    with open(data_path, newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))

    columns = list(rows[0].keys()) if rows else []
    totals = []
    missing = 0
    for row in rows:
        raw = (row.get('order_total') or '').strip()
        if raw == '':
            missing += 1
            continue
        totals.append(float(raw))

    returned = sum(
        1 for row in rows
        if (row.get('returned_within_30_days') or '').strip() == '1'
    )
    row_count = len(rows)
    lower, _, upper = statistics.quantiles(totals, n=4, method='inclusive')

    return {
        'row_count': row_count,
        'column_count': len(columns),
        'mean_order_total': statistics.fmean(totals),
        'median_order_total': statistics.median(totals),
        'stdev_order_total': statistics.pstdev(totals),
        'missing_order_total_count': missing,
        'nonpositive_order_total_count': sum(1 for value in totals if value <= 0),
        'returned_count': returned,
        'return_rate': returned / row_count if row_count else 0.0,
        'outlier_rule': (
            'a total is unusual when it falls outside the middle 50 percent '
            f'of the totals (below {lower:.2f} or above {upper:.2f})'
        ),
    }


if __name__ == '__main__':
    print(json.dumps(build_report(), sort_keys=True))
