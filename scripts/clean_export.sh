#!/usr/bin/env bash
# Backwards-compatible wrapper. The canonical, fail-closed exporter is
# scripts/export_release_source.sh (see docs/RELEASE_ARTIFACT_POLICY.md).
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

OUTDIR="${1:-/tmp/ruach-clean-export}"
echo "scripts/clean_export.sh is deprecated; using scripts/export_release_source.sh" >&2
exec "$SCRIPT_DIR/export_release_source.sh" "$OUTDIR"
