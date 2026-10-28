#!/bin/bash
# Stream each pinned shard through extract.py; nothing from the download is executed.
# Run from this directory: bash fetch_all.sh [python]. Writes data/compact/<env>.jsonl.
W="$(cd "$(dirname "$0")" && pwd)"
PY="${1:-python}"
B=https://huggingface.co/datasets/anonymouslinuxarena/linuxarena-public/resolve/2fd29f9c7bc190fb873bd76c6bd648f22b9ab0a7/data
mkdir -p "$W/data/compact"
for e in auto_workflow clinical_trial file_indexing media_processing model_registry shared_dotfiles slack_clone tiktok user_tracking web_scraping; do
  [ -s "$W/data/compact/$e.jsonl" ] && continue
  curl -sL --retry 5 "$B/$e.jsonl" | (cd /tmp && "$PY" -I "$W/extract.py" "$W/data/compact/$e.part") && mv "$W/data/compact/$e.part" "$W/data/compact/$e.jsonl"
  echo "done $e $(date)"
done
