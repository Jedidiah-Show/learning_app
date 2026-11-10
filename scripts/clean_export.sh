#!/usr/bin/env bash
# Reproducible clean export excluding dev artifacts and secrets
set -e
OUTDIR=${1:-/tmp/ruach-clean-export}
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"
rsync -a --exclude='.git' \
  --exclude='.venv' --exclude='venv' --exclude='env' \
  --exclude='node_modules' \
  --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.pytest_cache' --exclude='test-results' \
  --exclude='.env' --exclude='.env.local' --exclude='*.pem' --exclude='*.key' \
  --exclude='.qoder' --exclude='.DS_Store' \
  . "$OUTDIR/"
echo "Clean export created at $OUTDIR"
