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

from common import MODELS, RESULTS, load

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
res = json.load(open(RESULTS))
res["robustness_errors"] = out
json.dump(res, open(RESULTS, "w"), indent=1)
print(json.dumps(out, indent=1))
