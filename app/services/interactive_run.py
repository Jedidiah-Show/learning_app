"""Shared path for interactive, formative Python runs.

Selection order:
1. Piston (when PISTON_URL is configured) — the self-hosted, isolated
   execution engine; see docs/PISTON_SETUP.md.
2. The in-house Docker judge (when JUDGE_SUBMISSIONS_ENABLED is set or the
   app is running in tests).
3. Otherwise the caller must report 503 so the client falls back to the
   Pyodide browser runtime.
"""

from flask import current_app

from app.services import piston


def interactive_run_available():
    if current_app.testing:
        return True
    if piston.piston_enabled():
        return True
    return bool(current_app.config.get('JUDGE_SUBMISSIONS_ENABLED', False))


def run_learner_code(source, checks_code, timeout_sec=15.0, memory_mb=512):
    """Run learner source + checks and return a normalized result dict.

    Returns ``None`` when no execution engine is available (caller then
    responds 503 so the browser falls back to Pyodide).
    """
    run_code = f'{source}\n\n{checks_code}' if checks_code else source

    if piston.piston_enabled():
        try:
            return piston.execute_python(
                run_code, timeout_sec=timeout_sec, memory_mb=memory_mb,
            )
        except piston.PistonUnavailable as exc:
            current_app.logger.warning('Piston run failed for a practice exercise: %s', exc)
            return None

    from app.services.judge import execute_in_sandbox
    result = execute_in_sandbox(
        run_code, '', timeout_sec=timeout_sec, memory_mb=memory_mb, mode='run',
    )
    if result.verdict == 'INTERNAL_ERROR' and 'unavailable' in (result.error_details or '').lower():
        return None
    return result.to_dict()
