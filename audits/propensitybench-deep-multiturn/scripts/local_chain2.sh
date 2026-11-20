#!/bin/bash
# Resume the local three-arm run (after the first Metal out-of-memory crash of the server, 11:14 EST).
# Same arms, order and deadline as local_chain.sh. A watchdog restarts the server whenever its log
# shows "Insufficient Memory"; the run in progress then ends with status "oom" (censored: no trigger
# up to the level reached), never counted as not misaligned in the primary statistic.
set -u
cd "$(dirname "$0")/.."
export PB_DEBUG_LOG=data/local_calls.jsonl PB_RUN_TAG=":nothink" PB_TIMEOUT=240
export PB_OPENAI_BASE_URL=http://127.0.0.1:8080/v1 PB_OPENAI_MODEL=data/models/Qwen3-8B-MLX-4bit
export PB_SERVER_LOG=data/server_cur.log
DL=$(cat data/deadline)
start_server() {
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 nohup .venv/bin/mlx_lm.server --model data/models/Qwen3-8B-MLX-4bit \
    --host 127.0.0.1 --port 8080 --max-tokens 4096 --decode-concurrency 1 --prompt-concurrency 1 \
    --prompt-cache-bytes 1073741824 --chat-template-args '{"enable_thinking":false}' > "$PB_SERVER_LOG" 2>&1 &
  echo $! > data/server.pid
  until curl -s -m 2 http://127.0.0.1:8080/v1/models >/dev/null; do sleep 2; done
  echo "$(date) server up pid $(cat data/server.pid)"
}
watchdog() {
  n=0
  while true; do
    sleep 10
    if grep -q "Insufficient Memory" "$PB_SERVER_LOG" 2>/dev/null; then
      n=$((n+1)); echo "$(date) watchdog: server OOM #$n, restarting"
      sleep 15   # let the client see the failure and end the run as oom
      kill "$(cat data/server.pid)"; sleep 5; kill -9 "$(cat data/server.pid)" 2>/dev/null
      mv "$PB_SERVER_LOG" "data/server_oom_$n.log"
      start_server
    fi
  done
}
start_server
watchdog & WD=$!
python3 -I scripts/run_runs.py --backend openai --arms restored,placebo --start 0 --n 20 --workers 1 --deadline "$DL" --out runs/local_qwen3_8b.jsonl
python3 -I scripts/run_runs.py --backend openai --arms shipped,restored,placebo --start 20 --n 12 --workers 1 --deadline "$DL" --out runs/local_qwen3_8b.jsonl
echo "$(date) chain done"
kill $WD
kill "$(cat data/server.pid)"
echo "$(date) server stopped"
