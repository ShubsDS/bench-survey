"""Power of the pre-registered contrasts at the protocol (cluster) level, before any outcome.

Uses only the ProtocolQA cluster sizes (23 protocols, 107 items) and assumed outcome models:
  per-item success probability p_i = logistic(mu + u_cluster + e_item),
  u ~ N(0, 0.8^2) (design effect ~1.5, as the parent saw), e ~ N(0, 2.0^2) (items are mostly
  'always right' or 'always wrong' for a model, so two runs of one arm disagree on ~20% of items).
Contrasts (95% percentile cluster bootstrap must exclude 0, as in the analysis):
  P1 paired drop (qo -> qo_pa on the same items): drop delta in accuracy.
  P2 stratum gap (accuracy in stratum G minus stratum D, unpaired items, clusters shared),
     for a 50/50 and a 30/70 split of items.
Writes results/power.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import RESULTS, load  # noqa: E402

rng = np.random.default_rng(0)
items = load()
p = items[items.subset == "ProtocolQA"]
cl = p.cluster.astype("category").cat.codes.to_numpy()
n, k = len(cl), cl.max() + 1
SIM, BOOT = 400, 400


def logit_inv(x):
    return 1 / (1 + np.exp(-x))


def mu_for(acc):
    # find mu giving mean accuracy acc under the random-effects model (by simulation)
    lo, hi = -5, 5
    z = rng.normal(0, 0.8, 20000) + rng.normal(0, 2.0, 20000)
    for _ in range(40):
        m = (lo + hi) / 2
        if logit_inv(m + z).mean() < acc:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def boot_excl0(diff_by_item, cl):
    groups = [np.where(cl == g)[0] for g in range(k)]
    stats = np.empty(BOOT)
    for b in range(BOOT):
        pick = rng.integers(0, k, k)
        sel = np.concatenate([groups[g] for g in pick])
        stats[b] = diff_by_item[sel].mean()
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return lo > 0 or hi < 0


def power_paired(acc, delta):
    mu = mu_for(acc)
    hits = 0
    for _ in range(SIM):
        u = rng.normal(0, 0.8, k)[cl]
        e = rng.normal(0, 2.0, n)
        p0 = logit_inv(mu + u + e)
        p1 = np.clip(p0 - delta, 0, 1)  # uniform absolute drop
        a = rng.random(n) < p0
        b = rng.random(n) < p1
        hits += boot_excl0(a.astype(float) - b, cl)
    return hits / SIM


def power_strata(acc_g, acc_d, frac_g):
    mug, mud = mu_for(acc_g), mu_for(acc_d)
    hits = 0
    for _ in range(SIM):
        u = rng.normal(0, 0.8, k)[cl]
        e = rng.normal(0, 2.0, n)
        g = rng.random(n) < frac_g
        pr = logit_inv(np.where(g, mug, mud) + u + e)
        y = (rng.random(n) < pr).astype(float)
        groups = [np.where(cl == c)[0] for c in range(k)]
        stats = []
        for b in range(BOOT // 2):
            sel = np.concatenate([groups[c] for c in rng.integers(0, k, k)])
            gs, ds = sel[g[sel]], sel[~g[sel]]
            if len(gs) and len(ds):
                stats.append(y[gs].mean() - y[ds].mean())
        lo, hi = np.percentile(stats, [2.5, 97.5])
        hits += lo > 0
    return hits / SIM


out = {"n_items": int(n), "n_clusters": int(k), "sims": SIM, "boot": BOOT,
       "model": "logit p = mu + N(0,0.8^2) cluster + N(0,2.0^2) item",
       "paired_drop": {}, "strata_gap": {}}
for acc in (0.55, 0.70):
    for d in (0.05, 0.10, 0.15, 0.20):
        out["paired_drop"][f"acc{acc}_drop{d}"] = power_paired(acc, d)
for fg in (0.5, 0.3):
    for gap in (0.15, 0.25, 0.35):
        out["strata_gap"][f"fracG{fg}_gap{gap}"] = power_strata(0.55 + gap / 2, 0.55 - gap / 2, fg)
(RESULTS / "power.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
