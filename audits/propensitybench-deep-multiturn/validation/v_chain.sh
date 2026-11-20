#!/bin/bash
# Validator's local run: server on 127.0.0.1 with the audit's flags, the order-swap check, then stop.
# Hard stop at 100 minutes; OOM watchdog as in scripts/local_chain2.sh (no restart: the run ends).
set -u
cd "$(dirname "$0")/.."
export PB_OPENAI_BASE_URL=http://127.0.0.1:8080/v1 PB_OPENAI_MODEL=data/models/Qwen3-8B-MLX-4bit PB_TIMEOUT=240
LOG=data/validation_server.log
T0=$(date +%s)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 nohup .venv/bin/mlx_lm.server --model data/models/Qwen3-8B-MLX-4bit \
  --host 127.0.0.1 --port 8080 --max-tokens 4096 --decode-concurrency 1 --prompt-concurrency 1 \
  --prompt-cache-bytes 1073741824 --chat-template-args '{"enable_thinking":false}' > "$LOG" 2>&1 &
SP=$!
echo $SP > data/validation_server.pid
until curl -s -m 2 http://127.0.0.1:8080/v1/models >/dev/null; do sleep 2; done
echo "$(date) server up pid $SP"
python3 -I validation/v_order_swap.py &
RP=$!
while kill -0 $RP 2>/dev/null; do
  sleep 10
  if [ $(( $(date +%s) - T0 )) -gt 6000 ]; then echo "$(date) hard stop at 100 min"; kill $RP; break; fi
  if grep -q "Insufficient Memory" "$LOG" 2>/dev/null; then echo "$(date) server OOM, stopping"; kill $RP; break; fi
done
kill $SP; sleep 5; kill -9 $SP 2>/dev/null
echo "$(date) server stopped; elapsed $(( $(date +%s) - T0 )) s"
