#!/usr/bin/env bash
# M10 — dependency security review.
# Generates an auditable report without breaking the build on advisories that
# require a triage decision. CI uploads the report as an artifact.
set -u
OUT="${RUNNER_TEMP:-/tmp}/dependency-audit.txt"
{
  echo "# Dependency audit — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "commit: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
  echo
  if command -v pip-audit >/dev/null 2>&1; then
    echo "## pip-audit"
    pip-audit -r requirements.txt -r requirements-dev.txt 2>&1 || echo "(pip-audit reported findings or failed)"
  else
    echo "## pip-audit: not installed in this environment"
    echo "Install locally with: pip install pip-audit"
  fi
  echo
  if command -v npm >/dev/null 2>&1 && [ -f package-lock.json ]; then
    echo "## npm audit (production dependencies)"
    npm audit --omit=dev --audit-level=high 2>&1 || echo "(npm audit reported findings)"
  else
    echo "## npm audit: npm or package-lock.json unavailable"
  fi
} > "$OUT"
echo "Wrote $OUT"
