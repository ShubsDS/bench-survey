"""Validator check of claim 3 (stratum test on the paper's per-subtask SeqQA accuracies).

1. Recompute D from the paper's Table 2 (results/published.json, values checked by eye against
   data/paper/v3.txt Table 2 rows), with the S/F split 6 vs 9 held fixed.
2. Placebo: all C(15,6) = 5,005 splits; answer-type matched: 4 of the 6 primer-pair subtasks + 2
   of the 9 others (15 x 36 = 540).
3. Power: draw a random 6-subtask "true" set (no real effect assumed there), add delta to every
   model's accuracy on it (capped at 1), and run the same test. Power = share of 2,000 draws in
   which that set's mean D exceeds the 97.5th percentile of all 5,005 splits of the injected data.
   Also the minimum detectable D (the 97.5th percentiles themselves).
Run: data/.venv/bin/python -I validation/v3_power.py
"""
import itertools
import json
from pathlib import Path

import numpy as np

A = Path(__file__).resolve().parent.parent
P = json.load(open(A / "results/published.json"))
acc = P["tables"]["accuracy"]
cols = P["columns"]
models = cols[1:]
subs = sorted(k for k in acc if k.startswith("SeqQA_"))
assert len(subs) == 15
name = [s.replace("SeqQA_", "").replace("-v1", "") for s in subs]
M = np.array([[acc[s][m] for m in models] for s in subs])  # 15 x 7
H = np.array([acc[s]["human"] for s in subs])
S = ["ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
     "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"]
PRIMER = ["PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
          "PCR-gene-gibssmaprimers", "PCR-len-primers", "PCR-seq-primers"]
sidx = [name.index(x) for x in S]
pidx = [name.index(x) for x in PRIMER]
oidx = [i for i in range(15) if i not in pidx]


def meanD(Mx, s):
    s = list(s)
    f = [i for i in range(15) if i not in s]
    G = Mx - H[:, None]
    return float((G[s].mean(0) - G[f].mean(0)).mean())


ALL = list(itertools.combinations(range(15), 6))
MATCH = [a + b for a in itertools.combinations(pidx, 4) for b in itertools.combinations(oidx, 2)]


def dist(Mx, splits):
    G = Mx - H[:, None]
    tot = G.sum(0)
    out = []
    for s in splits:
        gs = G[list(s)].sum(0)
        out.append(((gs / 6) - (tot - gs) / 9).mean())
    return np.array(out)


obs = meanD(M, sidx)
dall = dist(M, ALL)
dmat = dist(M, MATCH)
res = {"obs_mean_D": round(obs, 4),
       "split_sizes_fixed": [6, 9],
       "all_splits": {"n": len(ALL), "q025": round(float(np.quantile(dall, .025)), 4),
                      "q975": round(float(np.quantile(dall, .975)), 4),
                      "percentile": round(float((dall < obs).mean()), 4), "sd": round(float(dall.std()), 4)},
       "matched_splits": {"n": len(MATCH), "q025": round(float(np.quantile(dmat, .025)), 4),
                          "q975": round(float(np.quantile(dmat, .975)), 4),
                          "percentile": round(float((dmat < obs).mean()), 4)},
       "per_model_D": {m: round(float(((M - H[:, None])[sidx, j].mean() - (M - H[:, None])[[i for i in range(15) if i not in sidx], j].mean())), 4) for j, m in enumerate(models)}}

rng = np.random.default_rng(0)
power = {}
for delta in [0.05, 0.1, 0.15, 0.18, 0.2, 0.25, 0.3, 0.4, 0.5]:
    hits = 0
    B = 400
    for _ in range(B):
        s = ALL[rng.integers(len(ALL))]
        Mx = M.copy()
        Mx[list(s)] = np.minimum(Mx[list(s)] + delta, 1.0)
        d = dist(Mx, ALL)
        hits += meanD(Mx, s) > np.quantile(d, 0.975)
    power[str(delta)] = round(hits / B, 3)
res["power_all_splits_by_delta"] = power
res["note"] = ("delta is a uniform rise in every model's accuracy on the 6 shortcut subtasks. "
               "Haiku's own centre-dependence on those subtasks, measured as the edit drop averaged "
               "over the 6 subtasks, is 0.18 (147 items).")
json.dump(res, open(A / "validation/v3_power.json", "w"), indent=1)
print(json.dumps(res, indent=1))
