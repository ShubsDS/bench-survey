"""Estimate hidden input the CLI adds to each call: regress reported input tokens on the characters
of (system + prompt) that the harness sent. The intercept is the per-call overhead the CLI adds."""
import glob
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
rows = []
for f in glob.glob(str(HERE.parent / "inference" / "cache" / "*.json")):
    c = json.load(open(f))
    u = c.get("usage") or {}
    tok = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
    rows.append((c["model"], len(c["system"]), len(c["prompt"]), tok))
out = {}
for m in sorted({r[0] for r in rows}):
    a = np.array([r[1:] for r in rows if r[0] == m], float)
    X = np.c_[np.ones(len(a)), a[:, 0], a[:, 1]]
    coef, *_ = np.linalg.lstsq(X, a[:, 2], rcond=None)
    pred = X @ coef
    out[m] = {"n": len(a), "intercept_tokens": float(coef[0]), "tok_per_char_system": float(coef[1]),
              "tok_per_char_prompt": float(coef[2]), "r2": float(1 - ((a[:, 2] - pred) ** 2).sum() / ((a[:, 2] - a[:, 2].mean()) ** 2).sum()),
              "min_total_tokens": float(a[:, 2].min()), "chars_at_min": float((a[:, 0] + a[:, 1])[a[:, 2].argmin()])}
    # same-system subsets: overhead = tokens - chars/ratio with ratio fitted on prompt only
print(json.dumps(out, indent=1))
(HERE / "v_overhead.json").write_text(json.dumps(out, indent=1))
