"""Diagnostic feedback for Arena submissions (M3.4).

Categories (per the milestone spec):
``syntax_error`` · ``runtime_error`` · ``incorrect_algorithm`` ·
``boundary_condition`` · ``data_structure_misuse`` · ``complexity_issue`` ·
``incorrect_assumption`` · ``incomplete_implementation`` · ``inconclusive``

Honesty rules:
- Derived from the verdict, tests_passed, total_tests and error_details —
  never from unseen hidden inputs.
- Every diagnostic carries a ``confidence`` field and a fixed disclaimer.
  When evidence is thin, the category is ``inconclusive``.
- We never claim to know *which* hidden case failed; we only describe what
  the evidence supports.
"""

DISCLAIMER = ('Derived only from the verdict and your code’s behaviour — '
              'we cannot see the hidden test inputs, so treat this as a hint, not a verdict on intent.')

CATEGORIES = (
    'syntax_error', 'runtime_error', 'incorrect_algorithm',
    'boundary_condition', 'data_structure_misuse', 'complexity_issue',
    'incorrect_assumption', 'incomplete_implementation', 'inconclusive',
)

_LABELS = {
    'syntax_error': 'Syntax error',
    'runtime_error': 'Runtime error',
    'incorrect_algorithm': 'Likely incorrect algorithm',
    'boundary_condition': 'Boundary-condition failure',
    'data_structure_misuse': 'Data structure misuse',
    'complexity_issue': 'Complexity / resource limit',
    'incorrect_assumption': 'Incorrect assumption',
    'incomplete_implementation': 'Incomplete implementation',
    'inconclusive': 'Inconclusive — not enough evidence to categorize',
}

_DETAILS = {
    'syntax_error': 'Your code did not compile, so no behaviour was executed.',
    'boundary_condition': 'Some public/aggregate checks passed while others did not. Failing cases may involve edges — empty inputs, boundaries, or zero-sized values — but the hidden cases themselves are not visible to us.',
    'data_structure_misuse': 'A lookup or access pattern failed — a missing key, wrong index, or misused container operation.',
    'complexity_issue': 'The judge stopped your program for exceeding time or memory — the algorithm may be correct but too slow or too heavy for the constraints.',
    'incorrect_assumption': 'Your program raised an error the data did not support — check your assumptions about inputs and types.',
    'incomplete_implementation': 'Something referenced or relied on is missing — an unset variable, an unbuilt path, an unimplemented branch.',
    'incorrect_algorithm': 'All or almost all checks failed. The approach itself is probably off — re-read the spec and the contract, not just the tests.',
    'runtime_error': 'Your program raised an exception the judge could not attribute to a specific cause.',
    'inconclusive': 'Not enough evidence to categorize the failure honestly.',
}


def diagnostic_for(submission):
    """Return {'category', 'label', 'detail', 'confidence', 'disclaimer'} or None."""
    verdict = (getattr(submission, 'verdict', None) or '').upper()
    tests_passed = getattr(submission, 'tests_passed', None) or 0
    total = getattr(submission, 'total_tests', None) or 0
    error = (getattr(submission, 'error_details', None) or '').lower()

    if verdict in {'COMPILE_ERROR'} or 'syntaxerror' in error:
        category, confidence = 'syntax_error', 'high'
    elif verdict in {'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED'}:
        category, confidence = 'complexity_issue', 'high'
    elif verdict == 'RUNTIME_ERROR':
        mapping = (
            (('indexerror', 'list index out of range'), 'boundary_condition'),
            (('keyerror',), 'data_structure_misuse'),
            (('typeerror',), 'incorrect_assumption'),
            (('zerodivisionerror',), 'incorrect_assumption'),
            (('valueerror',), 'incorrect_assumption'),
            (('attributeerror',), 'incorrect_assumption'),
            (('nameerror',), 'incomplete_implementation'),
            (('recursionerror', 'stack overflow'), 'complexity_issue'),
        )
        category, confidence = None, 'medium'
        for markers, candidate in mapping:
            if any(marker in error for marker in markers):
                category = candidate
                break
        if category is None:
            category = 'runtime_error'
    elif verdict == 'WRONG_ANSWER':
        if total > 0 and tests_passed == 0:
            category, confidence = 'incorrect_algorithm', 'medium'
        elif total > 0 and tests_passed < total:
            category, confidence = 'boundary_condition', 'low'
        else:
            category, confidence = 'inconclusive', 'low'
    elif verdict in {'PENDING', 'RUNNING', 'INTERNAL_ERROR'}:
        category, confidence = 'inconclusive', 'low'
    else:
        return None  # ACCEPTED / COMPLETED: nothing to diagnose

    return {
        'category': category,
        'label': _LABELS[category],
        'detail': _DETAILS[category],
        'confidence': confidence,
        'disclaimer': DISCLAIMER,
    }
