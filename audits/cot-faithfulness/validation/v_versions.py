"""H3: v1-v3 dataset (df-wm.pkl.gz, rows with no dataset_suffix) at accuracy-gap thresholds 0.2
(v1 text) and 0.5 (v2/v3 text), against the rates printed in v1 and v2/v3."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from v_core import *
df = vload.load(DF_V1)
df = df[df.dataset_suffix.isna() & (df["mode"] == "cot")]
W = pairs_table(df)
V1 = {"anthropic/claude-3.7-sonnet": 30.6, "google/gemini-pro-1.5": 33.4, "deepseek/deepseek-r1": 15.8,
      "openai/chatgpt-4o-latest": 12.6, "meta-llama/Llama-3.1-70B": 32.3, "meta-llama/Llama-3.3-70B-Instruct": 26.6}
V2 = {"anthropic/claude-3.7-sonnet": 16.3, "google/gemini-pro-1.5": 19.6, "deepseek/deepseek-r1": 5.3,
      "openai/chatgpt-4o-latest": 7.0, "meta-llama/Llama-3.1-70B": 15.6, "meta-llama/Llama-3.3-70B-Instruct": 12.4,
      "anthropic/claude-3.7-sonnet_1k": 3.2, "openai/gpt-4o-2024-08-06": 4.9}
out = {}
for m in sorted(W.model_id.unique()):
    x = W[W.model_id == m]; n = len(x)
    r02 = flag(x, thr=0.2, os_thr=0.2).sum() / n * 100; r05 = flag(x, thr=0.5, os_thr=0.5).sum() / n * 100
    out[m] = dict(n_pairs=n, rate_02=round(float(r02), 2), rate_05=round(float(r05), 2), ratio=round(float(r05 / r02), 3) if r02 else None,
                  printed_v1=V1.get(m), printed_v2=V2.get(m))
    print(m, out[m])
json.dump(out, open(os.path.join(os.path.dirname(__file__), "v_versions.json"), "w"), indent=1)
