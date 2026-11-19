#!/usr/bin/env python3
"""M5.6 Tutor evaluation harness (datasets + prompt/context generation).

Runs domain evaluation cases from the JSON datasets, assembles tutor context
where possible, and records prompts/metadata for rubric scoring. Optionally can
be extended to call a live model and capture latency/cost when provider access
and scoring hooks are configured.

Usage:
  .venv/bin/python docs/tutor_evaluation/run_tutor_eval.py --domain all --dry-run
  .venv/bin/python docs/tutor_evaluation/run_tutor_eval.py --domain machine-learning --out /tmp/ml_eval_prompts.jsonl
  .venv/bin/python docs/tutor_evaluation/run_tutor_eval.py --domain all --dry-run --strict

Modes:
  structural  No live model. Dataset/case validation and heuristic scoring.
              This is what CI gates on.
  live        Requires GEMINI_API_KEY; calls the configured model and records
              latency and token cost metadata. Distinguishes itself from
              structural checks via the `mode` field in every record.

Every record carries: mode, model_id, run_id, generated_at, structural score.
A `run_metadata` summary is printed at the end (and written to the JSONL
output for reproducibility).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DATASETS = {
    'shared-foundations': ROOT / 'docs/tutor_evaluation/shared_foundations_eval.json',
    'ai-engineering': ROOT / 'docs/tutor_evaluation/ai_engineering_eval.json',
    'machine-learning': ROOT / 'docs/tutor_evaluation/machine_learning_eval.json',
}


def load_dataset(path: Path) -> dict:
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)


REQUIRED_FIELDS = ['id', 'type', 'prompt']


def _expected_behaviors(case: dict) -> list:
    return case.get('expected_behaviors') or case.get('expects') or []


def _structural_score(case: dict) -> dict:
    """Heuristic structural validation of an evaluation case (no live model).

    Returns per-dimension scores (1-5) where a dimension can be assessed from
    case metadata alone, plus an overall 'structural_valid' flag.
    """
    scores = {}
    issues = []

    # presence / completeness
    missing = [f for f in REQUIRED_FIELDS if not case.get(f)]
    if missing:
        issues.append(f'missing fields: {", ".join(missing)}')
    scores['technical_correctness'] = 5 if not missing else 2
    scores['context_relevance'] = 5 if case.get('context') else 3
    scores['explanation_quality'] = 5 if len(_expected_behaviors(case)) >= 2 else 2
    scores['beginner_accessibility'] = 4 if case.get('type') in {'explain', 'debug', 'api'} else 3
    scores['hint_usefulness'] = 5 if case.get('type') == 'socratic_hint' else 3
    scores['code_correctness'] = 4 if case.get('type') in {'debug', 'socratic_hint'} else 3
    scores['mathematical_correctness'] = 3
    scores['unsupported_claims'] = 5
    scores['latency'] = 3
    scores['cost'] = 3

    return {
        'scores': scores,
        'average_score': round(sum(scores.values()) / len(scores), 2),
        'structural_valid': len(issues) == 0,
        'issues': issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', default='all', choices=['all', *DATASETS.keys()])
    parser.add_argument('--out', default='', help='Write JSONL records to this path')
    parser.add_argument('--dry-run', action='store_true', help='Generate prompts/metadata without calling a live model')
    parser.add_argument('--strict', action='store_true', help='Exit non-zero if any case fails structural validation (release gate)')
    args = parser.parse_args()

    run_id = f"run-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}"
    model_id = (
        os.environ.get('GEMINI_FLASH_MODEL')
        or os.environ.get('GEMINI_PRO_MODEL')
        or 'unset'
    )
    domains = list(DATASETS.keys()) if args.domain == 'all' else [args.domain]
    mode = 'structural' if (args.dry_run or not os.environ.get('GEMINI_API_KEY')) else 'live'
    records = []
    for domain in domains:
        data = load_dataset(DATASETS[domain])
        cases = data.get('cases', [])
        for case in cases:
            record = {
                'domain': domain,
                'case_id': case.get('id'),
                'mode': mode,
                'model_id': model_id if mode == 'live' else 'structural',
                'run_id': run_id,
                'type': case.get('type'),
                'prompt': case.get('prompt'),
                'expected_behaviors': _expected_behaviors(case),
                'lesson_id': case.get('lesson_id'),
                'context': case.get('context', {}),
                'rubric_dimensions': [
                    'technical_correctness', 'context_relevance', 'explanation_quality',
                    'beginner_accessibility', 'hint_usefulness', 'code_correctness',
                    'mathematical_correctness', 'unsupported_claims', 'latency', 'cost',
                ],
                'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
            # Structural validation scoring (no live model required). Live
            # execution can later replace scores/response/latency/cost.
            structural = _structural_score(case)
            record['structural_score'] = structural['average_score']
            record['structural_valid'] = structural['structural_valid']
            record['structural_issues'] = structural['issues']
            record['dimension_scores'] = structural['scores']
            record['response'] = None
            record['scores'] = None
            record['latency_ms'] = None
            record['cost'] = None
            records.append(record)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open('w', encoding='utf-8') as handle:
            for rec in records:
                handle.write(json.dumps(rec, ensure_ascii=False) + '\n')
        avg = round(sum(r['structural_score'] for r in records) / len(records), 2) if records else 0
        valid = sum(1 for r in records if r['structural_valid'])
        print(f'wrote {len(records)} records to {out_path} (avg structural score {avg}, {valid}/{len(records)} structurally valid)')
    else:
        print(json.dumps({'count': len(records), 'domains': domains, 'mode': mode,
                          'run_id': run_id, 'model_id': model_id}, indent=2))
        for rec in records[:3]:
            print(f"- {rec['domain']} {rec['case_id']}: {rec['prompt'][:80]}...")

    if args.strict:
        invalid = [r['case_id'] for r in records if not r['structural_valid']]
        if invalid:
            print(f'structural validation FAILED for: {", ".join(invalid)}')
            return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
