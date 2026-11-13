# Module 1 project: "Hello, AI World!" — a decision program for support requests

You will build a small Python program that reads a list of support requests and decides what to do with each one: `approve`, `review`, or `decline`. The decisions come from written rules that you state in plain language, so a person can read them, check them, and change them.

This is the "Hello, AI World!" project for Week 1. You are not training a model here. You are building the part that comes first in every real system: a clear decision that somebody can point at and agree with.

## The situation

A small online shop receives support requests. Each request has three facts:

- a `channel`: where it arrived — `web`, `mobile`, `email`, or `partner`
- an `amount`: the money asked back, in the shop's currency unit
- a `reason`: why the customer wants the money back — `damaged`, `wrong_item`, `late_delivery`, or `other`

Your program answers each request with exactly one of three decisions:

- `approve` — pay the money back straight away
- `review` — a person looks at the request before any money moves
- `decline` — do not pay the money back

## The decision rules

Check the rules in this order. The first rule that matches wins, and the program stops there.

| # | name | when | then |
|---|------|------|------|
| 1 | `damaged_or_wrong_item` | the reason is `damaged` or `wrong_item` | `approve` |
| 2 | `late_delivery` | the reason is `late_delivery` | `review` |
| 3 | `email_channel` | the channel is `email` | `decline` |
| 4 | `large_amount` | the amount is 50 or more | `review` |
| 5 | `fallback` | no rule above matched | `approve` |

The order is part of the rule, not a detail. Request `R10` arrives by email and asks for 102.40, so it matches row 3 and row 4 at the same time. Row 3 is checked first, so the answer is `decline`. Swap those two rows and the same request becomes `review`, and your program no longer follows the table you wrote.

## The data you are given

`data/requests.json` holds 12 requests. Every object has these keys:

| key | type | meaning |
|-----|------|---------|
| `id` | text | the request name, from `R01` to `R12` |
| `channel` | text | where the request came from: `web`, `mobile`, `email`, or `partner` |
| `amount` | number | the money asked back, such as 24.50 |
| `reason` | text | the customer's reason: `damaged`, `wrong_item`, `late_delivery`, or `other` |
| `expected_decision` | text | the decision the rules above produce, kept so you can check your work |

`expected_decision` is the answer key. Your program must not read it when it decides, and the checks in `tests/test_automation.py` remove that key before they call your function.

Applied to the 12 bundled requests, the rules produce 7 approvals, 3 reviews, and 2 declines. The two declines are `R05`, an email request for 15.00, and `R10`, an email request for 102.40.

This data is synthetic. The 12 requests were written for this exercise, they are not real customer records, they contain no personal information, and there is no third-party licence to honour.

## What to build

| file | what it is for |
|------|----------------|
| `src/rules.py` | your rule table, written out in plain words |
| `src/automation.py` | `decide`, `run_all`, and `build_report`, the code you write |
| `artifacts/decisions.jsonl` | written for you by `run_all`; commit it as evidence |
| `run.sh` | already included; it runs the whole project and prints the report |
| `README.md` | this brief; keep it and improve it as you go |

### Step 1: write the rules down

Open `src/rules.py` and replace the empty `RULES` list with your own. Each rule is a dict with exactly three keys:

```python
RULES = [
    {"name": "damaged_or_wrong_item", "when": "reason is damaged or wrong_item", "then": "approve"},
    {"name": "late_delivery", "when": "reason is late_delivery", "then": "review"},
    {"name": "email_channel", "when": "channel is email", "then": "decline"},
    {"name": "large_amount", "when": "amount is 50 or more", "then": "review"},
]
```

Write at least three rules, and keep them in the same order as the table above. Keep the `when` text in plain English, because a reviewer reads this file before they read your code.

### Step 2: implement `decide`

`decide(request)` takes one request dict and returns `"approve"`, `"review"`, or `"decline"`. Check your rules in order and return as soon as one matches. Every path must return a value, including the fallback that approves a request the rules did not match.

### Step 3: implement `run_all`

`run_all()` reads `data/requests.json`, calls `decide()` for each request, and writes `artifacts/decisions.jsonl`. That file holds one JSON object per line, and each object has two keys:

```json
{"id": "R01", "decision": "approve"}
```

Create the `artifacts` folder if it is not there yet. Twelve requests in, twelve lines out.

### Step 4: implement `build_report`

`build_report()` returns a dict with exactly these seven keys:

| key | type | how you compute it |
|-----|------|-------------------|
| `requests_total` | int | how many requests are in `data/requests.json` |
| `decisions_recorded` | int | how many decisions are in `artifacts/decisions.jsonl` |
| `correct_decisions` | int | how many recorded decisions match the `expected_decision` of the request with the same `id` |
| `decision_rules` | int | how many rules are listed in `rules.RULES` |
| `distinct_decisions` | int | how many different decision words appear in your recorded decisions |
| `readme_present` | bool | `True` when `README.md` is in the project root |
| `run_script_present` | bool | `True` when `run.sh` or `run.py` is in the project root |

Read the files while the function runs. Do not type a number into the function: if you do, the checks pass without the work being done, and a reviewer will see it in the first line.

### Step 5: run the checks

Use Python 3.11 or newer. Create a virtual environment, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

The three checks in `tests/test_automation.py` are:

- `test_report_matches_the_published_contract` runs your program and checks the seven report values.
- `test_decide_matches_every_bundled_request` calls your `decide()` on all 12 requests, with `expected_decision` removed, and compares the answer with the expected one.
- `test_run_all_records_one_decision_per_request` checks that `artifacts/decisions.jsonl` holds 12 lines, one per request, in order.

### Step 6: paste the report

```bash
bash run.sh
```

That prints one JSON object. Paste it into the project submission form. A finished project prints:

```json
{
  "correct_decisions": 12,
  "decision_rules": 4,
  "decisions_recorded": 12,
  "distinct_decisions": 3,
  "readme_present": true,
  "requests_total": 12,
  "run_script_present": true
}
```

`decision_rules` is 4 because your rule table names four rules and the fallback lives inside `decide()`. If you name five rules instead, that number changes, and that is fine as long as it is at least 3.

Finally, commit your work and push it to a public GitHub repository, the way lesson `mle.tools.04` explains. A reviewer should be able to clone the repository, run `pytest`, and see the same report you pasted.
