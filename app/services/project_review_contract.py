"""Validation for AI project review outputs.

Keeps route handlers thin and makes the AI output contract testable.
"""

from __future__ import annotations


def _valid_text_list(value):
    return (
        isinstance(value, list)
        and len(value) <= 20
        and all(
            isinstance(item, str) and item.strip() and len(item) <= 2000
            for item in value
        )
    )


def validate_project_review_evaluation(evaluation, evaluation_source, rubric):
    """Validate a project review evaluation against the contract.

    Returns (True, normalized_evaluation) or (False, error_message).
    """
    if not isinstance(evaluation, dict):
        return False, 'Project evaluation returned an invalid result. Please retry.'

    criterion_feedback = evaluation.get('criterion_feedback')
    criteria_ok = evaluation_source == 'local' or (
        isinstance(criterion_feedback, list)
        and len(criterion_feedback) == len(rubric)
        and all(
            isinstance(item, dict)
            and item.get('criterion') == criterion.get('criterion')
            and isinstance(item.get('score'), int)
            and not isinstance(item.get('score'), bool)
            and 0 <= item['score'] <= 100
            and isinstance(item.get('evidence'), str)
            and bool(item['evidence'].strip())
            and len(item['evidence']) <= 2000
            and isinstance(item.get('gap'), str)
            and len(item['gap']) <= 2000
            for item, criterion in zip(criterion_feedback, rubric)
        )
    )

    if (
        not isinstance(evaluation.get('summary'), str)
        or not evaluation['summary'].strip()
        or len(evaluation['summary']) > 6000
        or (
            evaluation.get('score') is not None
            and (
                not isinstance(evaluation.get('score'), int)
                or isinstance(evaluation.get('score'), bool)
                or not 0 <= evaluation['score'] <= 100
            )
        )
        or any(
            not _valid_text_list(evaluation.get(field, []))
            for field in ('strengths', 'gaps', 'next_steps')
        )
        or not criteria_ok
    ):
        return False, 'Project evaluation returned an invalid result. Please retry.'

    normalized = dict(evaluation)
    normalized['evaluation_source'] = evaluation_source
    return True, normalized
