"""Validate the published Practice Arena content against its public checks.

Checks every published problem's starter code, worked solution and browser
checks compile, and verifies that each worked solution passes the public
browser checks before it can be published.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.practice_arena import all_arena_problems

ALLOW_TOP_LEVEL_AWAIT = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT


def main():
    problems = all_arena_problems()
    failures = []
    for problem in problems.values():
        compiled = True
        code_by_field = {}
        for field in ('starter_code', 'solution_code', 'browser_checks'):
            try:
                code_by_field[field] = compile(
                    problem[field], f'{problem["id"]}:{field}', 'exec',
                    flags=ALLOW_TOP_LEVEL_AWAIT,
                )
            except Exception as error:  # report and continue
                compiled = False
                failures.append(f'{problem["id"]}: {field} does not compile: {error}')

        if not compiled:
            continue
        namespace = {}
        exec(code_by_field['solution_code'], namespace)
        exec(code_by_field['browser_checks'], namespace)

    for failure in failures:
        print(f'FAIL {failure}')
    if failures:
        raise SystemExit(1)
    print(f'Validated {len(problems)} Practice Arena problems successfully.')


if __name__ == '__main__':
    main()
