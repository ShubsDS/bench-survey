#!/bin/bash
# Download the ScaleAI/mrt folders this audit reads, at the revision pinned by
# findings/mrt-shade-arena (bc636d0). Uses the logged-in `hf` CLI. Data lands in data/mrt (git-ignored).
#   bash scripts/fetch_mrt.sh [shade|cua|w2s]
set -eu
cd "$(dirname "$0")/.."
SHA=bc636d0c3b881c7d8c76fd71b45b009c3710d437
S36=claude-3-5-sonnet-20241022
S4=claude-sonnet-4-20250514
inc=()
case "${1:-shade}" in
shade)
  for a in transcripts_no_hint_naive_thinking_time transcripts_no_hint_no_thinking_time \
           transcripts_no_hint_selective_thinking_time transcripts_no_secondary_task; do
    for s in "" _sequential_5_likert_reminder_v2 _hierarchical_5_likert_reminder_v2; do
      for w in "" _unaware _superaware; do
        inc+=(--include "task_pairs/*/${a}${s}${w}/${S36}/${S36}/*.json")
      done; done; done ;;
cua)
  inc+=(--include "task_pairs_agentcompany/*/transcripts_no_hint_*/${S4}/${S36}/*.json") ;;
w2s)
  for a in transcripts_no_hint_selective_thinking_time transcripts_no_secondary_task; do
    inc+=(--include "task_pairs/*/${a}/*/*/*.json")
  done ;;
esac
hf download ScaleAI/mrt --repo-type dataset --revision "$SHA" --local-dir data/mrt --max-workers 8 --quiet "${inc[@]}" >/dev/null
echo "done $1: $(find data/mrt -name 'transcript_*.json' | wc -l) transcript files in data/mrt"
