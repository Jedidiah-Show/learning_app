"""Reference implementation of the Module 1 "Hello, AI World!" project.

Kept outside ``starter_kits`` so learner downloads stay stubbed. The module
is the same one the kit asks for: the same three public functions, the same
report keys, and the same output file.

The rule table lives here instead of in ``src/rules.py`` because the shipped
kit ships an empty rule list on purpose; the learner fills that file in.
"""

from pathlib import Path
import json

KIT_ROOT = (
    Path(__file__).resolve().parents[2]
    / 'starter_kits' / 'machine_learning' / 'module_1_ai_tools'
)
DATA_PATH = KIT_ROOT / 'data' / 'requests.json'
ARTIFACTS_DIR = KIT_ROOT / 'artifacts'
DECISIONS_PATH = ARTIFACTS_DIR / 'decisions.jsonl'
README_PATH = KIT_ROOT / 'README.md'
RUN_SCRIPT_NAMES = ('run.sh', 'run.py')

RULES = [
    {
        'name': 'damaged_or_wrong_item',
        'when': 'reason is damaged or wrong_item',
        'then': 'approve',
    },
    {'name': 'late_delivery', 'when': 'reason is late_delivery', 'then': 'review'},
    {'name': 'email_channel', 'when': 'channel is email', 'then': 'decline'},
    {'name': 'large_amount', 'when': 'amount is 50 or more', 'then': 'review'},
]


def decide(request):
    """Return 'approve', 'review', or 'decline' for one request."""
    if request['reason'] in ('damaged', 'wrong_item'):
        return 'approve'
    if request['reason'] == 'late_delivery':
        return 'review'
    if request['channel'] == 'email':
        return 'decline'
    if request['amount'] >= 50:
        return 'review'
    return 'approve'


def run_all():
    """Decide every bundled request and write artifacts/decisions.jsonl."""
    requests = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    recorded = []
    with DECISIONS_PATH.open('w', encoding='utf-8') as handle:
        for request in requests:
            decision = decide(request)
            handle.write(json.dumps({'id': request['id'], 'decision': decision}) + '\n')
            recorded.append({'id': request['id'], 'decision': decision})
    return recorded


def build_report():
    """Return the project report, computed from the files on disk."""
    requests = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    decisions = []
    if DECISIONS_PATH.exists():
        for line in DECISIONS_PATH.read_text(encoding='utf-8').splitlines():
            if line.strip():
                decisions.append(json.loads(line))
    decided = {row['id']: row['decision'] for row in decisions}
    correct = sum(
        1
        for request in requests
        if decided.get(request['id']) == request['expected_decision']
    )
    return {
        'requests_total': len(requests),
        'decisions_recorded': len(decisions),
        'correct_decisions': correct,
        'decision_rules': len(RULES),
        'distinct_decisions': len({row['decision'] for row in decisions}),
        'readme_present': README_PATH.exists(),
        'run_script_present': any(
            (KIT_ROOT / name).exists() for name in RUN_SCRIPT_NAMES
        ),
    }


if __name__ == '__main__':
    run_all()
    print(json.dumps(build_report(), sort_keys=True))
