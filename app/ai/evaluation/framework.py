"""Dataset-driven evaluation with deterministic structural checks (M2.7).

The bundled tutor datasets contain human-readable quality expectations. Those
expectations are retained for review but are not silently converted into an
LLM-as-judge score. Automated checks cover the parts that can be proven
offline: structured output validity, in-scope contracts and non-empty answers.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

DATASET_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'docs', 'tutor_evaluation')
)
DATASET_FILES = (
    'shared_foundations_eval.json',
    'ai_engineering_eval.json',
    'machine_learning_eval.json',
)


@dataclass
class EvalCase:
    id: str
    prompt: str
    expects: List[str] = field(default_factory=list)
    case_type: str = 'general'
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    case: EvalCase
    passed: bool
    reasons: List[str] = field(default_factory=list)
    response: Optional[Dict[str, Any]] = None
    manual_review: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.case.id,
            'type': self.case.case_type,
            'passed': self.passed,
            'reasons': self.reasons,
            'manual_review': self.manual_review,
            'response': self.response,
        }


def load_dataset(path: str) -> List[EvalCase]:
    with open(path, 'r', encoding='utf-8') as handle:
        payload = json.load(handle)
    return [
        EvalCase(
            id=str(item['id']),
            prompt=str(item['prompt']),
            expects=list(item.get('expects') or []),
            case_type=str(item.get('type') or 'general'),
            context=dict(item.get('context') or {}),
        )
        for item in payload.get('cases', [])
    ]


def dataset_paths() -> List[str]:
    return [os.path.join(DATASET_DIR, name) for name in DATASET_FILES]


def run_structural_check(case: EvalCase, response: Any) -> EvalResult:
    """Check invariants that do not require subjective grading."""
    reasons: List[str] = []
    if not isinstance(response, dict):
        return EvalResult(case, False, ['Response is not a JSON object'])
    if 'in_scope' not in response or not isinstance(response['in_scope'], bool):
        reasons.append('Response has no boolean in_scope field')
    if case.case_type == 'out_of_scope' and response.get('in_scope') is not False:
        reasons.append('Out-of-scope case was accepted')
    elif case.case_type != 'out_of_scope' and response.get('in_scope') is False:
        reasons.append('In-scope case was rejected')
    answer = response.get('answer')
    if response.get('in_scope') is True and (
        not isinstance(answer, str) or not answer.strip()
    ):
        reasons.append('In-scope response has no answer text')
    return EvalResult(case, not reasons, reasons, response, list(case.expects))


def evaluate_dataset(
    cases: List[EvalCase],
    generator: Callable[[EvalCase], Any],
) -> Dict[str, Any]:
    """Run one dataset through an injected generator.

    ``generator`` may call the gateway, a local stub or a recorded fixture.
    Keeping it injectable makes evaluation reproducible in CI without live
    provider credentials.
    """
    results: List[EvalResult] = []
    for case in cases:
        try:
            response = generator(case)
            result = run_structural_check(case, response)
        except Exception as error:  # a failed call is a failed case
            result = EvalResult(
                case, False, [f'{type(error).__name__}: {error}']
            )
        results.append(result)
    passed = sum(1 for result in results if result.passed)
    return {
        'total': len(results),
        'passed': passed,
        'failed': len(results) - passed,
        'results': [result.to_dict() for result in results],
    }
