"""Completion-gate rules for shared course projects.

This module owns the single decision for whether a course project submission
satisfies the completion gate. Both the review submission endpoint and the
GitHub webhook must use the same rule.
"""

from __future__ import annotations


def project_passes_completion_gate(evaluation, evaluation_source, checks_verified):
    """Return True only when checks + AI evaluation satisfy the completion gate.

    Rules:
    - CI/checks must be verified.
    - Evaluation source must be AI (legacy missing source counts as AI-era).
    - Overall score must be an int in 70..100.
    - Every rubric criterion score must be an int in 50..100.
    """
    if (
        not checks_verified
        or evaluation_source not in ('ai', None)
        or not isinstance(evaluation, dict)
    ):
        return False
    score = evaluation.get('score')
    if (
        not isinstance(score, int) or isinstance(score, bool)
        or not 70 <= score <= 100
    ):
        return False
    criteria = evaluation.get('criterion_feedback') or []
    if not isinstance(criteria, list):
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get('score'), int)
        and not isinstance(item.get('score'), bool)
        and 50 <= item['score'] <= 100
        for item in criteria
    )


# Backward-compatible alias used by older imports.
_project_passes_completion_gate = project_passes_completion_gate
