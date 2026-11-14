#!/usr/bin/env python3
"""M5.6 Tutor evaluation harness (datasets + prompt/context generation).

Runs domain evaluation cases from the JSON datasets, assembles tutor context
where possible, and records prompts/metadata for rubric scoring. Optionally can
be extended to call a live model and capture latency/cost when provider access
and scoring hooks are configured.

Usage:
  .venv/bin/python docs/tutor_evaluation/run_tutor_eval.py --domain all --dry-run
  .venv/bin/python docs/tutor_evaluation/run_tutor_eval.py --domain machine-learning --out /tmp/ml_eval_prompts.jsonl
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', default='all', choices=['all', *DATASETS.keys()])
    parser.add_argument('--out', default='', help='Write JSONL records to this path')
    parser.add_argument('--dry-run', action='store_true', help='Generate prompts/metadata without calling a live model')
    args = parser.parse_args()

    domains = list(DATASETS.keys()) if args.domain == 'all' else [args.domain]
    records = []
    for domain in domains:
        data = load_dataset(DATASETS[domain])
        cases = data.get('cases', [])
        for case in cases:
            record = {
                'domain': domain,
                'case_id': case.get('id'),
                'type': case.get('type'),
                'prompt': case.get('prompt'),
                'expected_behaviors': case.get('expected_behaviors', []),
                'lesson_id': case.get('lesson_id'),
                'context': case.get('context', {}),
                'rubric_dimensions': [
                    'technical_correctness', 'context_relevance', 'explanation_quality',
                    'beginner_accessibility', 'hint_usefulness', 'code_correctness',
                    'mathematical_correctness', 'unsupported_claims', 'latency', 'cost',
                ],
                'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'mode': 'dry-run' if args.dry_run or not os.environ.get('GEMINI_API_KEY') else 'ready-for-live-run',
            }
            # Placeholder for live execution: integrate with app tutor flow/provider,
            # capture response text, latency_ms, token/cost metrics, and rubric scores.
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
        print(f'wrote {len(records)} records to {out_path}')
    else:
        print(json.dumps({'count': len(records), 'domains': domains, 'dry_run': bool(args.dry_run)}, indent=2))
        for rec in records[:3]:
            print(f"- {rec['domain']} {rec['case_id']}: {rec['prompt'][:80]}...")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
