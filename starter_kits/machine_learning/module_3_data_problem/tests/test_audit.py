from audit import build_report


def test_dataset_contract_and_quality_counts():
    report = build_report()
    assert report['row_count'] == 12
    assert report['required_columns_present'] is True
    assert report['unique_order_ids'] == 12
    assert report['missing_order_total_count'] == 1
    assert report['nonpositive_order_total_count'] == 1
    assert report['returned_count'] == 4


def test_time_ordered_evaluation_boundary_and_leakage_review():
    report = build_report()
    assert report['development_rows'] == 8
    assert report['evaluation_rows'] == 4
    assert report['split_strategy'] == 'time_ordered'
    assert report['leakage_features'] == ['refund_reason']
