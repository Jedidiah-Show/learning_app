#!/usr/bin/env bash
# Reproducible clean export excluding dev artifacts and secrets
set -e
OUTDIR=${1:-/tmp/ruach-clean-export}
# Guard against unsafe paths
case "$OUTDIR" in
  /|/home|/root|/etc|/usr|/var|/bin|/sbin|"$HOME") echo "Refusing unsafe output path"; exit 1 ;;
  /*|./*|../*) ;; 
  *) echo "Output path must be absolute or start with ./ or ../"; exit 1 ;;
esac
if [ -z "$OUTDIR" ] || [ "$OUTDIR" = "/" ]; then echo "Invalid output path"; exit 1; fi
rm -rf -- "$OUTDIR"
mkdir -p -- "$OUTDIR"
rsync -a --exclude='.git' \
  --exclude='.venv' --exclude='venv' --exclude='env' \
  --exclude='node_modules' \
  --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.pytest_cache' --exclude='test-results' \
  --exclude='.env' --exclude='.env.local' --exclude='*.pem' --exclude='*.key' \
  --exclude='.qoder' --exclude='.DS_Store' \
  . "$OUTDIR/"
echo "Clean export created at $OUTDIR"
