#!/bin/bash
# Run arms in sequence (each run uses at most 4 concurrent calls). Usage:
#   bash audits/lab-bench-deep-recall/scripts/batch.sh <model> <style> "arm:subset" ...
set -u
PY=audits/lab-bench/data/.venv/bin/python
R=audits/lab-bench-deep-recall/scripts/run.py
model=$1; style=$2; shift 2
for spec in "$@"; do
  arm=${spec%%:*}; sub=${spec##*:}
  $PY -I $R --arm "$arm" --model "$model" --style "$style" --subset "$sub" --quiet < /dev/null
done
