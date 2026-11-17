"""Robustness: exposure-conditioned ASR with errored runs not counted as successes (S1e).

Run after 04-06: data/.venv/bin/python -I scripts/07_errors_conditioned.py
Writes the 'robustness_errors' block of results.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from common import MODELS, RESULTS, load, save_block

att = load()
att = att[att.pipeline.isin(MODELS)]
none = load("none")
U = none[none.pipeline.isin(MODELS)].groupby("pipeline").utility.mean().loc[MODELS]
att = att.assign(sec_ok=att.security & ~att.error)
S0 = att.groupby("pipeline").security.mean().loc[MODELS]
S0e = att.groupby("pipeline").sec_ok.mean().loc[MODELS]
E = att[att.exposed]
S1e = E.groupby("pipeline").sec_ok.mean().loc[MODELS]
S1 = E.groupby("pipeline").security.mean().loc[MODELS]
rev = 0
for i, a in enumerate(MODELS):
    for b in MODELS[i + 1:]:
        if np.sign(S1e[a] - S1e[b]) == -np.sign(S0[a] - S0[b]) and S0[a] != S0[b]:
            rev += 1
out = dict(
    S1e=S1e.round(4).to_dict(),
    spearman_S0_S1e=round(float(spearmanr(S0, S1e).statistic), 3),
    spearman_S0e_S1e=round(float(spearmanr(S0e, S1e).statistic), 3),
    trend_U_S0e=round(float(spearmanr(U, S0e).statistic), 3),
    trend_U_S1e=round(float(spearmanr(U, S1e).statistic), 3),
    n_pairs_point_reversed_vs_published=rev,
    max_abs_change_S1_pp=round(float(100 * (S1 - S1e).abs().max()), 2),
)
# common support detail: pairs whose order on jointly exposed cases reverses, and whether
# the published order for that pair was separated (two-way bootstrap, 04_effect.py)
from scipy.stats import norm as _norm
pairs = pd.read_csv(os.path.join(os.path.dirname(RESULTS), "results", "pairs.csv"))
att2 = att.assign(key=att.ut + "|" + att.it)
pe = att2.pivot(index="key", columns="pipeline", values="exposed")
ps = att2.pivot(index="key", columns="pipeline", values="security")
cs = []
for r in pairs.itertuples():
    both = pe[r.a] & pe[r.b]
    d = ps.loc[both, r.a].mean() - ps.loc[both, r.b].mean()
    if np.sign(d) == -np.sign(r.S0_diff) and r.S0_diff != 0:
        cs.append(dict(a=r.a, b=r.b, S0_diff=r.S0_diff, common_diff=round(float(d), 4),
                       n_common=int(both.sum()), S0_separated=bool(r.S0_sign != 0)))
out["common_support_reversals"] = cs
# Holm on normal-approximation p from the bootstrap z (B=2000 bootstrap p cannot go below 1/2000)
holm = {}
for s in ["S0", "S1", "S2", "S3"]:
    p = np.sort(2 * _norm.sf(np.abs(pairs[f"{s}_z"].values)))
    m = len(p)
    adj = np.maximum.accumulate(np.minimum(1, p * (m - np.arange(m))))
    holm[s] = int((adj < 0.05).sum())
out["holm_separated_pairs_normal_approx"] = holm

save_block("robustness_errors", out)
print(json.dumps(out, indent=1))
