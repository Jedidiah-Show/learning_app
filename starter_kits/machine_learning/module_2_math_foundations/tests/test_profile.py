import shutil
import tempfile
from pathlib import Path

from profile import DATA_PATH, build_report


REPORT_KEYS = {
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
}


def test_report_has_exactly_the_contracted_keys():
    assert set(build_report()) == REPORT_KEYS


def test_shape_of_the_table():
    report = build_report()
    assert report['row_count'] == 12
    assert report['column_count'] == 6


def test_centre_and_spread_of_the_present_totals():
    report = build_report()
    assert abs(report['mean_order_total'] - 38.29) < 0.005
    assert abs(report['median_order_total'] - 29.99) < 0.005
    assert abs(report['stdev_order_total'] - 30.6929) < 0.02


def test_data_quality_counts():
    report = build_report()
    assert report['missing_order_total_count'] == 1
    assert report['nonpositive_order_total_count'] == 1


def test_return_counts_and_rate():
    report = build_report()
    assert report['returned_count'] == 4
    assert abs(report['return_rate'] - 0.3333333333) < 0.001


def test_outlier_rule_is_a_written_rule():
    rule = build_report()['outlier_rule']
    assert isinstance(rule, str)
    assert len(rule.strip()) >= 10


def test_report_is_reproducible():
    assert build_report() == build_report()


def test_report_is_computed_from_the_data_file():
    with tempfile.TemporaryDirectory() as folder:
        changed = Path(folder) / 'orders.csv'
        shutil.copy(DATA_PATH, changed)
        text = changed.read_text()
        assert '24.50' in text
        changed.write_text(text.replace('24.50', '74.50', 1))
        baseline = build_report()
        updated = build_report(data_path=changed)
    assert updated['mean_order_total'] != baseline['mean_order_total']
    assert abs(updated['mean_order_total'] - 42.8355) < 0.005
