"""Shared ML project submission labels and workflow rules."""

FAILURE_STAGES = {
    'report_contract': 'Report does not match the fixed dataset contract',
    'ci_verification': 'Public automated checks could not be verified',
    'review_unavailable': 'Automated review unavailable (submission saved)',
    'review_invalid': 'Automated review returned an invalid result',
    'rubric_below_threshold': 'Review completed but below the pass threshold',
}

_TYPE_PLACEHOLDERS = {
    'int': 0,
    'float': 0.0,
    # null signals "fill this in" without hinting at either expected boolean.
    'bool': None,
    'str': '',
    'list': [],
    'dict': {},
}


def example_report_skeleton(report_contract):
    """Build a type-matched placeholder skeleton of a report.

    Shows the field names and expected JSON types only — never the expected
    values (``equals``), which would leak the fixed checks.
    """
    skeleton = {}
    for entry in report_contract or []:
        key = entry.get('key')
        if not isinstance(key, str) or not key:
            continue
        skeleton[key] = _TYPE_PLACEHOLDERS.get(entry.get('type'), None)
    return skeleton
