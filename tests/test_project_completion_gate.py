from app.services.project_completion import project_passes_completion_gate


def test_completion_gate_requires_verified_checks_and_ai_score():
    evaluation = {
        'score': 80,
        'criterion_feedback': [{'criterion': 'A', 'score': 70, 'evidence': 'x', 'gap': ''}],
    }
    assert project_passes_completion_gate(evaluation, 'ai', True) is True
    assert project_passes_completion_gate(evaluation, 'ai', False) is False
    assert project_passes_completion_gate(evaluation, 'local', True) is False


def test_completion_gate_requires_all_criteria_at_least_50():
    evaluation = {
        'score': 90,
        'criterion_feedback': [
            {'criterion': 'A', 'score': 90, 'evidence': 'x', 'gap': ''},
            {'criterion': 'B', 'score': 49, 'evidence': 'x', 'gap': 'weak'},
        ],
    }
    assert project_passes_completion_gate(evaluation, 'ai', True) is False


def test_completion_gate_accepts_legacy_missing_source():
    evaluation = {
        'score': 70,
        'criterion_feedback': [{'criterion': 'A', 'score': 50, 'evidence': 'x', 'gap': ''}],
    }
    assert project_passes_completion_gate(evaluation, None, True) is True
