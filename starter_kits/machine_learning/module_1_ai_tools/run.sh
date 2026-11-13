#!/usr/bin/env bash
# Run the whole project: decide every bundled request, then print the report
# as JSON. The JSON printed here is what you paste into the submission form.
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m automation
