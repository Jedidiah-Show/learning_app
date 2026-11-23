"""Deterministic ML project report contract checks (M4).

The contract is authored with the curriculum and embedded in the ML pathway
manifest. Keeping the validator in the domain (rather than the HTTP route)
lets both submission handling and M4 evaluation evidence use the same rule
without duplicating it or trusting a generated score.
"""

from __future__ import annotations

import math

from app.ml_pathway import machine_learning_pathway


def module_by_id(module_id):
    return next(
        (
            module for module in machine_learning_pathway()['modules']
            if module['id'] == module_id
        ),
        None,
    )


def report_matches(module_id, report):
    """Return whether ``report`` satisfies the module's published contract."""
    module = module_by_id(module_id)
    contract = (module or {}).get('report_contract') or []
    if not contract or not isinstance(report, dict):
        return False
    keys = {entry['key'] for entry in contract}
    if set(report) != keys:
        return False
    for entry in contract:
        key = entry['key']
        value = report[key]
        kind = entry.get('type')
        if kind in ('int', 'float'):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
            if not math.isfinite(value):
                return False
            if kind == 'int' and not isinstance(value, int):
                return False
            if 'equals' in entry:
                expected = entry['equals']
                tolerance = entry.get('tolerance', 1e-9)
                if abs(value - expected) > tolerance:
                    return False
            if 'min' in entry and value < entry['min']:
                return False
            if 'max' in entry and value > entry['max']:
                return False
        elif kind in ('bool',):
            if not isinstance(value, bool) or value != entry.get('equals', value):
                return False
        elif kind in ('str', 'string'):
            if not isinstance(value, str):
                return False
            if 'equals' in entry and value != entry['equals']:
                return False
            if 'allowed' in entry and value not in entry['allowed']:
                return False
            if 'length' in entry and len(value) != entry['length']:
                return False
            if 'min_length' in entry and len(value) < entry['min_length']:
                return False
        elif kind in ('list',):
            if not isinstance(value, list):
                return False
            if 'equals' in entry and value != entry['equals']:
                return False
            if 'length' in entry and len(value) != entry['length']:
                return False
        else:
            return False
    return True
