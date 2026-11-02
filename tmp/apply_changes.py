"""One-off curriculum transform for the beginner prerequisite fixes.

Adds a quantitative-literacy primer (1.00) to Module 1, renumbers the module's
"Lesson N of 17" labels to 18, replaces the numpy attention example in 3.02
with pure stdlib, adds plain glosses for cosine/dot product (5.04) and regex
(1.11). Idempotent: safe to re-run.
"""

import ast
import json
import re
from pathlib import Path

DATA = Path('app/data')
CURRICULUM = DATA / 'dynamoai_curriculum.json'
EXTRAS = DATA / 'lesson_extras.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(path, obj):
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )


def build_primer():
    mean_median = (
        "An average is not one number. The mean adds everything and divides by the "
        "count, so one huge outlier pulls it up. The median is the middle value once "
        "you sort, so it ignores the outliers and tells you what a typical request "
        "feels like. When the mean is much larger than the median, a few bad events "
        "are doing most of the damage."
    )
    percentiles = (
        "Sort your numbers, then ask what value a given share of them falls under. "
        "The 50th percentile (p50) is the median: half of requests are faster. The "
        "95th percentile (p95) is the value 95% of requests beat, and p99 is the "
        "same idea for 99%. Users rarely complain about the average; they feel the "
        "percentiles at the top, the slow tail, so engineers report p95 and p99 "
        "rather than a single average."
    )
    cost = (
        "Models are billed by tokens, and tokens are counted per request, so cost "
        "is simple arithmetic you can always sanity-check: tokens per request times "
        "requests per day, divided by one million, times the price per million. "
        "Add retries and fans-out on top. If you cannot sketch the monthly bill on "
        "the back of an envelope, you cannot spot the request pattern that triples it."
    )
    return {
        'id': '1.00',
        'module_id': '01',
        'title': 'Reading numbers: averages, percentiles, and cost',
        'subtitle': (
            "Learn the handful of maths ideas AI engineers use every day - mean and "
            "median, percentiles like p95 and p99, and turning usage into a cost."
        ),
        'meta': 'Python for AI Engineers · Lesson 1 of 18 · study guide',
        'why_it_matters': [
            (
                "Later lessons ask you to 'watch the p99', 'budget tokens', and "
                "'report percentiles' as if these are obvious. They are not obvious "
                "yet, and no earlier lesson teaches them. This primer fills that gap "
                "in one sitting so the performance and cost language from Module 2 "
                "onward reads clearly instead of guessing."
            )
        ],
        'outcomes': [
            "Explain the difference between the mean and the median and when each misleads.",
            "Read a percentile such as p95 and say in one sentence what it means.",
            "Estimate the daily cost of an API from tokens, request volume, and price.",
            "Recognise why slow tails, not averages, drive user complaints.",
        ],
        'core_concepts': [
            {'title': 'Mean, median, and why both matter', 'content': mean_median},
            {'title': 'Percentiles and the slow tail', 'content': percentiles},
            {'title': 'Turning usage into cost', 'content': cost},
        ],
        'key_terms': [
            {'term': 'Mean', 'definition': "Add every value, divide by the count; sensitive to outliers."},
            {'term': 'Median', 'definition': "The middle value once sorted; ignores extreme outliers."},
            {'term': 'Percentile', 'definition': "The value a given share of results fall under, e.g. p95 = 95% are at or below it."},
            {'term': 'p99', 'definition': "The 99th percentile; the slowest 1% of requests are above it. Watch it for tail latency."},
            {'term': 'Throughput', 'definition': "How many requests you finish per second; a count, not a speed."},
            {'term': 'Unit cost', 'definition': "Price for one thing (e.g. USD per million tokens) so totals scale cleanly."},
        ],
        'mental_model': (
            "Think of a shop checkout queue. The average wait hides the truth: one "
            "stalled lane can make ninety shoppers wait while ten breeze through. The "
            "p95 is 'the wait nine out of ten shoppers beat'; the median is the "
            "middle person in line. Averages flatter you, percentiles tell you when to fix things."
        ),
        'worked_example': [
            (
                "Dami logs ten request latencies in milliseconds: 120, 95, 300, 110, "
                "105, 500, 118, 112, 108, 115. Her dashboard says 'average 168 ms' "
                "and the product seems fine. She sorts them, finds a median near 113 "
                "ms, and a p95 of about 380 ms, and realises nine requests are quick "
                "while two stall. She sets an alert on p95 instead of the mean, so the "
                "next stall pages her before users notice. The decision: report the "
                "tail, not the average."
            )
        ],
        'steps': [
            "Compute the mean and median of a short list with the statistics module and notice the gap.",
            "Write a tiny percentile function and check that p0 is the minimum and p100 the maximum.",
            "Estimate a monthly bill from tokens per request, requests per day, and price per million.",
            "Rewrite one dashboard note from 'average latency' to 'p50 and p95 latency' and explain the difference.",
        ],
        'code': {
            'title': 'Mean, median, percentiles, and a rough cost, with the standard library only.',
            'code': (
                "import statistics\n\n"
                "latencies_ms = [120, 95, 300, 110, 105, 500, 118, 112, 108, 115]\n\n"
                "def percentile(values, p):\n"
                "  ordered = sorted(values)\n"
                "  rank = (p / 100) * (len(ordered) - 1)\n"
                "  low = int(rank)\n"
                "  high = min(low + 1, len(ordered) - 1)\n"
                "  weight = rank - low\n"
                "  return ordered[low] * (1 - weight) + ordered[high] * weight\n\n"
                "mean = statistics.mean(latencies_ms)\n"
                "median = statistics.median(latencies_ms)\n"
                "p50 = percentile(latencies_ms, 50)\n"
                "p95 = percentile(latencies_ms, 95)\n\n"
                'print(f\'mean   {mean:6.1f} ms   (one slow request drags this up)\')\n'
                'print(f\'median {median:6.1f} ms   (the typical request)\')\n'
                'print(f\'p50    {p50:6.1f} ms   (half of requests beat this)\')\n'
                'print(f\'p95    {p95:6.1f} ms   (the slow tail users feel)\')\n\n'
                "price_per_million = 2.50\n"
                "tokens_per_request = 1800\n"
                "requests_per_day = 500\n"
                "daily_cost = tokens_per_request * requests_per_day / 1_000_000 * price_per_million\n"
                'print(f\'rough daily inference cost: USD {daily_cost:.2f}\')'
            ),
            'language': 'python',
            'what_to_notice': [
                "The mean (168 ms) is far above the median (about 113 ms): a couple of stalls pulled it up.",
                "percentile() reads sorted data, so p0 returns the minimum and p100 the maximum.",
                "Cost is just three numbers multiplied together; write the formula out before trusting any dashboard.",
            ],
        },
        'common_mistakes': [
            "Reporting only the average and concluding the service is healthy while the p99 doubles.",
            "Confusing throughput (requests per second) with latency (time per request); one is a rate, the other a duration.",
            "Forgetting to divide tokens by one million when the price is quoted per million, so the bill looks 1,000 times smaller.",
        ],
        'production_notes': [
            "Alert on percentiles you can defend, usually p95 or p99, not the mean, because a single request cannot wreck a percentile the way it wrecks an average.",
            "Keep the unit-cost formula in one place so a price change is a single edit, not a hunt through notebooks.",
        ],
        'checklist': [
            "I can say in one sentence what p95 means for a list of latencies.",
            "I know when the median is a better 'typical' number than the mean.",
            "I can estimate a monthly inference bill from tokens, volume, and price.",
            "My example code uses only the Python standard library.",
        ],
        'tasks': [
            "Add a p99 line to the example and run it on your own ten-number list; write the two sentences explaining mean versus p99 (15 minutes).",
            "Estimate the monthly cost of your capstone's model calls from tokens per request, expected requests per day, and a per-million price (15 minutes).",
            "Find one place a real product shows 'average' and rewrite it as p50 and p95 with a one-line note on why it matters (10 minutes).",
        ],
        'capstone': (
            "Your capstone's operations notes need a latency target and a cost model; "
            "this lesson gives you the vocabulary to write both honestly."
        ),
        'questions': [
            "Why can two services with the same mean latency feel very different to users?",
            "What does a p99 of 1200 ms tell you that a p50 of 200 ms does not?",
            "If a price is quoted per million tokens, what mistake makes your cost estimate 1000 times too small?",
            "When would you deliberately report the median instead of the mean?",
        ],
        'prerequisites': ['Complete Module 00 lessons and its module project.'],
        'pages': [
            (
                "Reading numbers: averages, percentiles, and cost\n"
                "The few maths ideas every later module assumes you already have: "
                "mean versus median, percentiles like p95 and p99, and turning usage "
                "into money.\n"
                "Python for AI Engineers · Lesson 1 of 18 · study guide\n\n"
                "WHY THIS LESSON MATTERS\n"
                "From Module 2 onward the lessons talk about watching the p99, "
                "budgeting tokens, and reporting percentiles as though they are "
                "second nature. For an absolute beginner they are not, and no other "
                "lesson stops to teach them. This primer gives you those words now, in "
                "one short sitting, so performance and cost pages read clearly later.\n\n"
                "MEAN, MEDIAN, AND WHY BOTH\n"
                "The mean is the total divided by the count. The median is the middle "
                "value after you sort. A single extreme number moves the mean a lot and "
                "the median almost not at all, so a mean far above the median is your "
                "signal that a few outliers are doing most of the damage.\n\n"
                "PERCENTILES AND THE SLOW TAIL\n"
                "Sort the numbers and mark where a share of them sit. The 50th "
                "percentile (p50) equals the median. The 95th (p95) is beaten by 95% of "
                "requests; p99 by 99%. Users do not feel the average, they feel the "
                "tail, which is why engineers say 'p95 latency' rather than 'average "
                "latency'.\n\n"
                "TURNING USAGE INTO COST\n"
                "Cost is arithmetic: tokens per request times requests per day, divided "
                "by one million, times the price per million, plus retries. Being able "
                "to sketch that by hand is what lets you notice when a change triples "
                "the bill."
            ),
            (
                "A short percentile you can run\n"
                "The standard library gives you mean and median directly, and a "
                "percentile is only a lookup into a sorted list, so you never need an "
                "extra package to reason about latency.\n\n"
                "WHAT TO PRACTICE\n"
                "Run the numbers, change one latency to 5000 ms, and watch the mean "
                "jump while p50 barely moves. That gap is the whole lesson: the tail is "
                "where the problem lives, and averages hide it."
            ),
        ],
    }


def renumber(lesson):
    lesson['meta'] = re.sub(
        r'Lesson (\d+) of 17',
        lambda m: f'Lesson {int(m.group(1)) + 1} of 18',
        lesson.get('meta', ''),
    )
    lesson['pages'] = [
        re.sub(
            r'Lesson (\d+) of 17',
            lambda m: f'Lesson {int(m.group(1)) + 1} of 18',
            str(page),
        )
        for page in lesson.get('pages') or []
    ]


STDLIB_CODE = """import math


def dot(a, b):
  return sum(x * y for x, y in zip(a, b))


def softmax(row):
  peak = max(row)
  exps = [0.0 if value == float("-inf") else math.exp(value - peak) for value in row]
  total = sum(exps)
  return [value / total for value in exps]


def attention(q, k, v, causal):
  head_width = len(q[0])
  scores = [[dot(qi, kj) / math.sqrt(head_width) for kj in k] for qi in q]
  if causal:
    for i, row in enumerate(scores):
      for j in range(i + 1, len(row)):
        row[j] = float("-inf")
  weights = [softmax(row) for row in scores]
  return [
    [sum(w * v[r][c] for r, w in enumerate(wrow)) for c in range(len(v[0]))]
    for wrow in weights
  ]


tokens = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
q = k = v = tokens
for row in attention(q, k, v, causal=True):
  print([round(value, 2) for value in row])"""


def replace_3_02_numpy(lesson):
    code = lesson.get('code')
    if isinstance(code, dict) and 'numpy' in code.get('code', ''):
        code['code'] = STDLIB_CODE
        code['title'] = (
            'A miniature causal self-attention pass in pure Python, so it runs '
            'without any third-party package.'
        )
    marker = 'earlier tokens.\n'
    for index, page in enumerate(lesson.get('pages') or []):
        if 'import numpy' not in page:
            continue
        start = page.index(marker) + len(marker)
        end = page.index('\nWHAT TO NOTICE', start)
        indented = '\n'.join(
            ('  ' + line) if line.strip() else '' for line in STDLIB_CODE.split('\n')
        )
        lesson['pages'][index] = page[:start] + indented + page[end:]


def replace_5_04_cosine(lesson):
    old = 'Similarity is usually cosine, which compares direction rather than length.'
    new = (
        'Similarity is usually cosine, which compares direction rather than length '
        '(a dot product multiplies two vectors element by element and adds the '
        "results; cosine divides that sum by the two vectors' lengths, leaving only "
        'the angle between them).'
    )
    lesson['pages'] = [
        str(page).replace(old, new) for page in lesson.get('pages') or []
    ]


def replace_1_11_regex(lesson):
    old = 'regexes for environment names'
    new = (
        'regexes (short for regular expressions: compact pattern strings that '
        'describe allowed text, e.g. a name that is only lowercase letters and '
        'underscores) for environment names'
    )
    lesson['pages'] = [
        str(page).replace(old, new) for page in lesson.get('pages') or []
    ]
    for concept in lesson.get('core_concepts') or []:
        if isinstance(concept, dict) and old in str(concept.get('content', '')):
            concept['content'] = concept['content'].replace(old, new)


def main():
    curriculum = load(CURRICULUM)
    extras = load(EXTRAS)

    primer = build_primer()
    ast.parse(primer['code']['code'])

    # Insert the primer and renumber within the top-level lessons list.
    top = curriculum['lessons']
    if not any(l['id'] == '1.00' for l in top):
        position = next(i for i, l in enumerate(top) if l['id'] == '1.01')
        top.insert(position, primer)
    for lesson in top:
        if lesson['module_id'] == '01' and lesson['id'] != '1.00':
            renumber(lesson)

    # Mirror into the module-01 embedded lessons copy so the raw file is consistent.
    for module in curriculum['modules']:
        if module['id'] != '01':
            continue
        embedded = module.get('lessons') or []
        if embedded and not any(l.get('id') == '1.00' for l in embedded):
            position = next(i for i, l in enumerate(embedded) if l.get('id') == '1.01')
            embedded.insert(position, primer)
        for lesson in embedded:
            if lesson.get('module_id') == '01' and lesson.get('id') != '1.00':
                renumber(lesson)
        module['lesson_count'] = len(
            [l for l in curriculum['lessons'] if l['module_id'] == '01']
        )

    curriculum['course']['total_lessons'] = len(curriculum['lessons'])
    curriculum['course']['description'] = curriculum['course']['description'].replace(
        '212-lesson', '213-lesson'
    )

    by_id = {l['id']: l for l in curriculum['lessons']}
    replace_3_02_numpy(by_id['3.02'])
    replace_5_04_cosine(by_id['5.04'])
    replace_1_11_regex(by_id['1.11'])

    # Beginner-layer extras for the new lesson (module 01 is out of enforced
    # scope, but an authored intro keeps the plain-language layer 100% covered).
    extras['1.00'] = {
        'intro': (
            "Every later module talks about p99 latency, token budgets, and cost "
            "percents as if they are obvious. This short lesson teaches the few maths "
            "words behind them - mean, median, percentile, and simple cost maths - so "
            "nothing you read later starts with a term you were never given."
        ),
        'concepts': [
            {
                'title': 'Mean, median, and why both matter',
                'plain': (
                    'Add everything and divide by the count to get the mean; sort and '
                    'take the middle to get the median. One huge number moves the mean '
                    'a lot and the median barely at all, so a big gap between them '
                    'means a few outliers are doing the damage.'
                ),
                'example': (
                    'Latencies 95, 105, 108, 110, 112, 115, 118, 120, 300, 500 average '
                    'to 168 ms but have a median near 113 ms - the average is lying.'
                ),
            },
            {
                'title': 'Percentiles and the slow tail',
                'plain': (
                    'Sort the numbers and ask what value a given share of them fall '
                    'under. p50 is the middle; p95 is beaten by 95% of results; p99 by '
                    '99%. Users feel the top percentiles, not the average.'
                ),
                'example': (
                    'Saying "p95 latency is 380 ms" means 95 out of 100 requests came '
                    'back in 380 ms or less, and the slowest 5% were worse.'
                ),
            },
            {
                'title': 'Turning usage into cost',
                'plain': (
                    'Cost is just multiplication: tokens per request times requests '
                    'per day, divided by one million, times the price per million, '
                    'plus any retries. Write the formula down before trusting a bill.'
                ),
                'example': (
                    '1800 tokens x 500 requests / 1,000,000 x $2.50 per million comes '
                    'to about $2.25 a day.'
                ),
            },
        ],
        'answers': [
            (
                'Because the mean hides the tail: one service has every request '
                'around the average, the other has many quick ones and a few very '
                'slow ones that users actually notice.'
            ),
            (
                'p99 = 1200 ms means the slowest 1% of requests take about 1.2 '
                'seconds or more, revealing a tail that the p50 of 200 ms never shows.'
            ),
            (
                'Multiplying by the per-million price but forgetting to divide the '
                'token count by one million makes the estimate a thousand times too big '
                '(reading it the wrong way round makes it a thousand times too small).'
            ),
            (
                'When a few extreme outliers would distort the mean, the median gives '
                'the more honest "typical" value.'
            ),
        ],
    }

    # Enrich the in-scope embeddings plain-language concept with a foot-hold.
    embeddings_concept = extras['5.04']['concepts'][0]
    if 'dot product' not in embeddings_concept['plain']:
        embeddings_concept['plain'] += (
            " A dot product multiplies two equal-length lists element by element and "
            "adds up the results; cosine similarity is that total divided by the two "
            "lists' lengths, so it measures the angle between them, not how far apart "
            "their ends are."
        )

    dump(CURRICULUM, curriculum)
    dump(EXTRAS, extras)

    # Self-checks.
    result = load(CURRICULUM)
    lesson_ids = [l['id'] for l in result['lessons']]
    assert len(lesson_ids) == result['course']['total_lessons'] == 213, len(lesson_ids)
    assert lesson_ids.count('1.00') == 1
    l302 = next(l for l in result['lessons'] if l['id'] == '3.02')
    assert 'numpy' not in json.dumps(l302)
    ast.parse(l302['code']['code'])
    l111 = next(l for l in result['lessons'] if l['id'] == '1.11')
    assert 'regular expressions' in json.dumps(l111)
    l504 = next(l for l in result['lessons'] if l['id'] == '5.04')
    assert 'dot product' in json.dumps(l504)
    print('OK: primer added, total_lessons =', result['course']['total_lessons'])
    print('Module 01 lessons:', sum(1 for l in result['lessons'] if l['module_id'] == '01'))


if __name__ == '__main__':
    main()
