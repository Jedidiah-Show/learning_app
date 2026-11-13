"""The checks that define the contract for the Module 1 project.

The first check runs your program and compares the report with the values
the submission form expects. The second check calls your decision function on
every bundled request and compares the answer with the expected one, with the
``expected_decision`` column removed so the answer cannot be copied. The
third check looks at the file your program writes.

The paths come from the ``automation`` module itself, so the checks read the
bundled data and the artifacts in the same folder as your code.
"""

import json

from automation import (
    DATA_PATH,
    DECISIONS_PATH,
    build_report,
    decide,
    run_all,
)


def _load_requests():
    """Return the bundled requests as a list of dicts."""
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _without_expected_answer(request):
    """Return the request without its expected_decision column."""
    return {
        key: value
        for key, value in request.items()
        if key != "expected_decision"
    }


def test_report_matches_the_published_contract():
    run_all()
    report = build_report()
    assert report["requests_total"] == 12
    assert report["decisions_recorded"] == 12
    assert report["correct_decisions"] == 12
    assert report["decision_rules"] >= 3
    assert report["distinct_decisions"] >= 2
    assert report["readme_present"] is True
    assert report["run_script_present"] is True


def test_decide_matches_every_bundled_request():
    for request in _load_requests():
        decision = decide(_without_expected_answer(request))
        assert decision == request["expected_decision"], request["id"]


def test_run_all_records_one_decision_per_request():
    recorded = run_all()
    lines = DECISIONS_PATH.read_text(encoding="utf-8").splitlines()
    requests = _load_requests()
    assert len(lines) == 12
    assert len(recorded) == 12
    for line, request in zip(lines, requests):
        row = json.loads(line)
        assert row["id"] == request["id"]
        assert row["decision"] in ("approve", "review", "decline")
