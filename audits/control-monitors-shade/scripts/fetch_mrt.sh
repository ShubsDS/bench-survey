#!/bin/bash
# Fetch the ScaleAI/mrt folders this audit reads, at the revision pinned by findings/mrt-shade-arena
# (bc636d0, which is also the dataset's HEAD). Per-file HTTP downloads hit HF rate limits (429), so
# this uses a blob-less git clone plus a sparse checkout: blobs arrive in one batched fetch.
# Lands in data/mrt-git (git-ignored, about 8 GB, 28,728 transcript files).
#   bash scripts/fetch_mrt.sh
set -eu
cd "$(dirname "$0")/../data"
SHA=bc636d0c3b881c7d8c76fd71b45b009c3710d437
S36=claude-3-5-sonnet-20241022
S4=claude-sonnet-4-20250514
[ -d mrt-git ] || GIT_LFS_SKIP_SMUDGE=1 git clone -q --filter=blob:none --no-checkout \
    https://huggingface.co/datasets/ScaleAI/mrt mrt-git
cd mrt-git
git sparse-checkout init --no-cone
cat > .git/info/sparse-checkout <<EOF
/task_pairs/*/transcripts_no_hint_naive_thinking_time*/$S36/$S36/*.json
/task_pairs/*/transcripts_no_hint_no_thinking_time*/$S36/$S36/*.json
/task_pairs/*/transcripts_no_secondary_task*/$S36/$S36/*.json
/task_pairs/*/transcripts_no_hint_selective_thinking_time/*/*/*.json
/task_pairs/*/transcripts_no_hint_selective_thinking_time_sequential_4_likert_reminder_v2/*/*/*.json
/task_pairs/*/transcripts_no_hint_selective_thinking_time_hierarchical_4_likert_reminder_v2/*/*/*.json
/task_pairs/*/transcripts_no_secondary_task/*/*/*.json
/task_pairs/*/transcripts_no_secondary_task_sequential_4_likert_reminder_v2/*/*/*.json
/task_pairs/*/transcripts_no_secondary_task_hierarchical_4_likert_reminder_v2/*/*/*.json
/task_pairs_agentcompany/*/transcripts_no_hint_*/$S4/$S36/*.json
/task_pairs/base_task_definition.py
/task_pairs/*/task_definition.py
EOF
git checkout -q "$SHA"
test "$(git rev-parse HEAD)" = "$SHA"
echo "$(find . -name 'transcript_*.json' | wc -l) transcript files at $SHA"
