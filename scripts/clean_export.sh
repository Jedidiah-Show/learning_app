#!/usr/bin/env bash
# Reproducible clean export excluding dev artifacts and secrets
set -e
OUTDIR=${1:-/tmp/ruach-clean-export}
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
OUTDIR="$(realpath -m -- "$OUTDIR")"
case "$OUTDIR" in
  /|"$REPO_ROOT"|"$REPO_ROOT"/*)
    echo "Output must be outside the repository"
    exit 1
    ;;
esac
if [ -e "$OUTDIR" ]; then
  echo "Output path already exists; choose a new path"
  exit 1
fi
mkdir -p -- "$(dirname -- "$OUTDIR")"
mkdir -- "$OUTDIR"
rsync -a --exclude='.git' \
  --exclude='.venv' --exclude='venv' --exclude='env' \
  --exclude='node_modules' \
  --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.pytest_cache' --exclude='test-results' \
  --exclude='.env' --exclude='.env.local' --exclude='*.pem' --exclude='*.key' \
  --exclude='.qoder' --exclude='.DS_Store' \
  "$REPO_ROOT/" "$OUTDIR/"
echo "Clean export created at $OUTDIR"
