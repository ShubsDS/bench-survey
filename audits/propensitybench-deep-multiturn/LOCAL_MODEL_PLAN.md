# Plan: attach a local open-weights model to the multi-turn runner

Status: 2026-11-20. **Executed, with the deviations below.** Results are in [`README.md`](README.md),
section "Local model: Qwen3-8B".

**Who ran what.**

- **Steps 1–2 (venv and download)** were run by the main session after the owner approved the
  download in chat. This auditor did not act on the earlier relayed approval.
- **This auditor checked them.** `mlx-lm` 0.31.3 and `mlx` 0.32.4 on Python 3.12.12.
  `model.safetensors` is 4,351,884,216 bytes with sha256
  `fcc83d7537bee76cc143be3e25f8954b816798f93528103db1cddb02977c5617`. No `.py`, `.bin`, `.pkl` or
  `.pt` files.
- **Steps 3–7 were run by this auditor, with these deviations** (prereg Amendment 1, dated before
  any local run finished):
  - **Thinking off.** `--chat-template-args '{"enable_thinking":false}'`. With thinking on, a call
    took about 40 s and the pilot alone would have taken about 5 h.
  - **Server flags.** `--max-tokens 4096 --decode-concurrency 1 --prompt-concurrency 1
    --prompt-cache-bytes 1073741824`, bound to 127.0.0.1, with `HF_HUB_OFFLINE=1`.
  - **The tool-call check passed 20/20** with thinking on and 20/20 with thinking off, so the
    native backend (b) was used.
  - **The arms ran unattended** from `scripts/local_chain.sh`, which applies the pre-registered
    rule and the deadline.
  - **Memory.** The machine is shared, and with the model loaded 10–13 GB of its 16 GB was wired.
    Before thinking was turned off, some calls took several minutes, most likely from swapping.

## Why a local model

- On Claude, the 3 USD cap allows about 6–10 scenarios per arm in the real multi-turn loop
  ([`prereg.md`](prereg.md), Power).
- A three-arm answer needs about 32 scenarios per arm at a base rate of 20% or more. That costs
  nothing on a local model except time.
- A model the paper tested ties the result to a published PP number.

## Which open-weights models the paper tested

Source: `sec/results.tex` and Table `tab:propensity-main` in the parent's pinned paper source
(sha256 `95d3ade1…43d5c`). The open-weights models are the four below the second rule.

| Model (paper) | PP_zero | PP_H | PP_B | Cyber, benign | Self-prolif., benign | 4-bit size | Fits a 16 GB M4? |
|---|---|---|---|---|---|---|---|
| Llama 3.1 70B | 11.9 | 55.4 | 61.9 | 67.7 | 62.7 | about 40 GB | No |
| Qwen 2.5 32B | 4.9 | 22.9 | 48.5 | 59.5 | 56.5 | 18.44 GB (`mlx-community/Qwen2.5-32B-Instruct-4bit`, measured) | No: weights alone exceed RAM |
| Llama 3.1 8B | 37.6 | 66.5 | 83.7 | 85.6 | 87.1 | 4.52 GB (`mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`) | Yes, but see licence |
| **Qwen 3 8B** | 57.8 | 75.2 | 80.0 | 84.1 | 87.1 | **4.35 GB** (`Qwen/Qwen3-8B-MLX-4bit`) | **Yes** |

Domain columns are from Table `tab:domain-breakdown`. Sizes are summed from the Hugging Face API
file listing (anonymous metadata request, 2026-11-20).

The closest relative of Qwen 2.5 32B that fits is `mlx-community/Qwen2.5-14B-Instruct-4bit`
(8.32 GB). The paper did not test it, so a result from it would be about that model only. It is
not recommended over a model the paper tested.

## Recommendation

**`Qwen/Qwen3-8B-MLX-4bit`, revision `383413e909f3bc5303ce195ebbdf0339c5a1a2a3`.**

- **Publisher.** Qwen's own MLX 4-bit conversion of a model the paper tested.
- **Licence.** Apache-2.0: no gate and no new licence terms.
- **Files.** 4,351,884,216 bytes of weights in one `model.safetensors` file. The other files are
  JSON and text: config, tokenizer, merges, vocab, index, README, LICENSE, `.gitattributes`. The
  repository has no `.py`, no pickle and no custom code.
- **Memory.** About 4.4 GB of weights plus the KV cache. At 32k tokens of context, Qwen3-8B's
  KV cache (36 layers, 8 KV heads of dimension 128, fp16) is about 4.7 GB. That fits in 16 GB,
  and a full 12-level run stays under about 30k tokens (the mock run's last call is about 14k
  tokens of text).
- **Base rate.** By the paper, its base rate in this condition is high (PP_B 80.0%; 84–87% in the
  two domains used here). That is where the power table says a three-arm test can answer.

Why not Llama 3.1 8B: its weights are under the Llama 3.1 Community License. The methodology says
not to accept new licence terms, so it is not recommended without the owner's say.

## Expected speed and time

These are estimates, not measurements. The pilot measures them.

- **Speed.** About 20 tokens/s generation and a few hundred tokens/s prompt processing for an
  8B 4-bit model on a base M4 (memory-bandwidth bound). `mlx_lm.server` reuses the KV cache
  across requests with a common prefix, so each call processes only the new turn.
- **Calls per run.** A run that never triggers makes about 78 calls (the mock run). With
  Qwen 3 8B's published early failures (R_B 0.6: most failures at the task turn or level 1),
  a triggering run makes about 5–15 calls.
- **Time per call.** About 6 s with thinking off (100 tokens) and about 20 s with thinking on
  (400 tokens).
- **Time per run.** At an 80% trigger rate, about 3 min (thinking off) to 8 min (thinking on).

| Stage | Runs | Time (thinking off / on) |
|---|---|---|
| Tool-call check | 20 requests | under 5 min |
| Pilot, shipped arm (= the first 20 scenarios of arm A) | 20 | 1 h / 2.7 h |
| Rest of the three arms, 32 scenarios each (12 more shipped, 32 restored, 32 placebo) | 76 | 3.8 h / 10 h |

- **Thinking mode.** Qwen3's chat template turns thinking on by default. The paper does not say
  how it ran Qwen 3 8B, so the default (on) is used. If the pilot's time per run would push the
  three arms past about 6 hours, the three-arm run is cut by the pre-registered rule: as many
  scenarios as fit, in the fixed order, with at least 10 per arm or not at all. Thinking is not
  switched off midway.
- **Pilot runs as arm A.** The pilot runs are the first 20 shipped runs of the three-arm design:
  the same run ids, prompts and seeds. The runner skips finished run ids.

## Commands (run from the repository root; nothing system-wide)

```bash
cd audits/propensitybench-deep-multiturn

# 1. Runtime in a uv virtual environment inside this folder (.venv is git-ignored)
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python "mlx-lm==0.31.3"
.venv/bin/python -c "import mlx_lm, mlx.core as mx; print(mlx_lm.__version__, mx.__version__)"

# 2. Weights, anonymously, at the pinned revision, into data/ (git-ignored); safetensors only
env -u HF_TOKEN HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_HUB_DISABLE_TELEMETRY=1 \
  .venv/bin/hf download Qwen/Qwen3-8B-MLX-4bit \
  --revision 383413e909f3bc5303ce195ebbdf0339c5a1a2a3 \
  --local-dir data/models/Qwen3-8B-MLX-4bit
ls -la data/models/Qwen3-8B-MLX-4bit; shasum -a 256 data/models/Qwen3-8B-MLX-4bit/model.safetensors
find data/models -name '*.py' -o -name '*.bin' -o -name '*.pkl' -o -name '*.pt'   # must print nothing

# 3. OpenAI-compatible server on 127.0.0.1 only, offline (no further downloads)
HF_HUB_OFFLINE=1 .venv/bin/mlx_lm.server --model data/models/Qwen3-8B-MLX-4bit \
  --host 127.0.0.1 --port 8080 > data/server.log 2>&1 &
echo $! > data/server.pid

# 4. Attach backend (b): no code change, environment only
export PB_OPENAI_BASE_URL=http://127.0.0.1:8080/v1
export PB_OPENAI_MODEL=data/models/Qwen3-8B-MLX-4bit     # same string as --model, so nothing else is loaded
python3 -I scripts/toolcall_check.py                      # 20/20 -> backend openai; else openai-text
BE=openai   # or openai-text if the check fails

# 5. Pilot, shipped arm, one run at a time (mlx serves requests serially), checkpointed per run
python3 -I scripts/run_runs.py --backend $BE --arms shipped --n 20 --workers 1 --out runs/local_qwen3_8b.jsonl

# 6. Only if the pilot meets the prereg rule (>= 20% and >= 4 misaligned runs): the three arms,
#    sized to the wall clock (N = 32 if it fits, at least 10)
nohup python3 -I scripts/run_runs.py --backend $BE --arms shipped,restored,placebo --n $N --workers 1 \
  --out runs/local_qwen3_8b.jsonl > data/local_run.log 2>&1 &

# 7. Stop the server
kill $(cat data/server.pid)
```

Then `python3 -I scripts/analyze.py` produces the numbers for `results.json` and `README.md`.
Record in the README pins:

- the repo id and revision;
- the `model.safetensors` sha256 and file sizes;
- the `mlx-lm` and `mlx` versions;
- the server flags;
- the time per run.
