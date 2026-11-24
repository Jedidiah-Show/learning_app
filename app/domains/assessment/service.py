"""Assessment and Evaluation domain service.

Encapsulates rubric scoring, submission verification rules,
and competency evidence validation decoupled from HTTP/Flask request state.
"""

from __future__ import annotations

from app.core.exceptions import ValidationError


def calculate_rubric_score(criteria_feedback: list[dict]) -> int:
    """Calculate aggregate passing score percentage from individual rubric criteria."""
    if not criteria_feedback:
        return 0
    scores = []
    for item in criteria_feedback:
        if not isinstance(item, dict):
            continue
        score = item.get('score')
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            scores.append(max(0, min(100, int(score))))
    if not scores:
        return 0
    return int(round(sum(scores) / len(scores)))


def validate_rubric_criteria(criteria_feedback: list[dict], required_count: int = 1) -> bool:
    """Validate that rubric criteria meet structured format and count requirements."""
    if not isinstance(criteria_feedback, list):
        return False
    if len(criteria_feedback) < required_count:
        return False
    for item in criteria_feedback:
        if not isinstance(item, dict):
            return False
        criterion = item.get('criterion') or item.get('name')
        score = item.get('score')
        evidence = item.get('evidence')
        if not isinstance(criterion, str) or not criterion.strip():
            return False
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            return False
        if not isinstance(evidence, str) or not evidence.strip():
            return False
    return True
