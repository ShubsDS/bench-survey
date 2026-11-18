"""Pooled residual gap without the alignment-faking label over the 44 Opus helpful-only variants,
for the hard label (auditor) and the soft label, two-way bootstrap (variants x queries, 1000 draws,
seed 12345). Also the paper-metric AF rate per variant vs the hard-label rate. Writes c1c_pooled.json.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rederive import D, OPUS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(12345)
M = {}
for v in OPUS:
    x = D[(D.variant == v) & D.pm_score.notna()]
    tr = x[x.tier == "train"].set_index("qid"); dp = x[x.tier == "deploy"].set_index("qid")
    q = tr.index.intersection(dp.index)
    M[v] = dict(q=np.array(q), pm=(tr.loc[q].c_pm.astype(int) - dp.loc[q].c_pm.astype(int)).values,
                hard=((tr.loc[q].c_pm & ~tr.loc[q].hard).astype(int) - dp.loc[q].c_pm.astype(int)).values,
                soft=((tr.loc[q].c_pm & ~tr.loc[q].soft).astype(int) - dp.loc[q].c_pm.astype(int)).values)


def tot(key, vw, qw):
    num = sum(vw[i] * (qw[M[v]["q"]] * M[v][key]).sum() for i, v in enumerate(OPUS))
    den = sum(vw[i] * qw[M[v]["q"]].sum() for i, v in enumerate(OPUS))
    return num / den


ov, oq = np.ones(len(OPUS)), np.ones(400)
out = {k: 100 * tot(k, ov, oq) for k in ("pm", "hard", "soft")}
bs = {k: [] for k in ("pm", "hard", "soft")}
for _ in range(1000):
    vw = np.bincount(rng.integers(0, len(OPUS), len(OPUS)), minlength=len(OPUS)); qw = rng.poisson(1.0, 400).astype(float)
    for k in bs:
        bs[k].append(100 * tot(k, vw, qw))
out["ci"] = {k: list(np.percentile(v, [2.5, 97.5])) for k, v in bs.items()}
rates = []
for v in OPUS:
    x = D[(D.variant == v) & (D.tier == "train")]
    rates.append((v, 100 * x.hard.mean(), 100 * ((x.hard & x.c_pm).mean() + (x.soft & x.c_pm).mean()) / 2))
out["af_rate_hard_minus_paper_median"] = float(np.median([a - b for _, a, b in rates]))
out["af_rate_per_variant"] = rates
json.dump(out, open(os.path.join(HERE, "c1c_pooled.json"), "w"), indent=1, default=float)
print({k: out[k] for k in ("pm", "hard", "soft", "ci", "af_rate_hard_minus_paper_median")})
