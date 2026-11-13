"""Decide every bundled support request with written rules.

You write this module. The function names and the report keys are fixed
because the checks in ``tests/test_automation.py`` call them.

The files this module works with:

``data/requests.json``
    the 12 bundled requests, read by ``run_all()`` and ``build_report()``.
``artifacts/decisions.jsonl``
    your recorded decisions, one JSON object per line with the keys ``id``
    and ``decision``, written by ``run_all()``.
``README.md`` and ``run.sh``
    the files in the project root that ``build_report()`` checks for.

Running this module as a script records the decisions and prints the report
as JSON, which is what you paste into the project submission form.
"""

from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "requests.json"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DECISIONS_PATH = ARTIFACTS_DIR / "decisions.jsonl"
README_PATH = PROJECT_ROOT / "README.md"
RUN_SCRIPT_NAMES = ("run.sh", "run.py")


def decide(request):
    """Return the decision for one request.

    Args:
        request: a dict with the keys ``id``, ``channel``, ``amount``, and
            ``reason``. The value of ``amount`` is a number and the value of
            ``reason`` is one of ``damaged``, ``wrong_item``,
            ``late_delivery``, or ``other``.

    Returns:
        The string ``"approve"``, ``"review"``, or ``"decline"``, chosen with
        the rule order written in README.md. The first rule that matches
        wins, and every path returns a value.
    """
    raise NotImplementedError(
        "Implement decide() with the rules in README.md, first match wins"
    )


def run_all():
    """Decide every bundled request and record the decisions.

    Reads ``data/requests.json``, calls ``decide()`` for each request, and
    writes ``artifacts/decisions.jsonl`` with one JSON object per line. Each
    line holds the keys ``id`` and ``decision``. The ``artifacts`` folder is
    created if it does not exist yet.

    Returns:
        The list of the recorded decision dicts, in request order.
    """
    raise NotImplementedError(
        "Implement run_all() so that every request gets one recorded decision"
    )


def build_report():
    """Return the project report described in README.md.

    Compute every value from the files on disk while this function runs.
    Read ``data/requests.json`` and ``artifacts/decisions.jsonl``, count the
    rules in ``rules.RULES``, and check the project files. Do not type a
    number into this function.

    Returns:
        A dict with exactly these keys:

        ``requests_total``
            int, how many requests are in ``data/requests.json``.
        ``decisions_recorded``
            int, how many decisions are in ``artifacts/decisions.jsonl``.
        ``correct_decisions``
            int, how many recorded decisions equal the ``expected_decision``
            of the request with the same ``id``.
        ``decision_rules``
            int, how many rules are listed in ``rules.RULES``.
        ``distinct_decisions``
            int, how many different decision words appear in the recorded
            decisions.
        ``readme_present``
            bool, ``True`` when ``README.md`` is in the project root.
        ``run_script_present``
            bool, ``True`` when ``run.sh`` or ``run.py`` is in the project
            root.
    """
    raise NotImplementedError(
        "Implement build_report() by reading your own files, not typed-in numbers"
    )


if __name__ == "__main__":
    run_all()
    print(json.dumps(build_report(), sort_keys=True))
