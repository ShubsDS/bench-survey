"""Power of the planned D-versus-K design (no model output; simulation only). Seed 0.

Scenarios (effect = accuracy K - D on a subtask):
  U  uniform drop 0.20 on all six cue subtasks (the size the parent saw for Haiku, about 0.2)
  H  Haiku-like heterogeneity from the parent's per-subtask edit drops: gibshind 0.52,
     gibssma 0.40, gcpercent 0.12, gene-enz 0.05, AAseq 0, seq-enz 0 (mean 0.18)
  U10 uniform 0.10
Baseline K accuracy 0.95. Pairs: with probability 0.6 the D outcome copies the K outcome, otherwise
it is an independent draw chosen so that the D marginal is 0.95 - effect (so discordant pairs occur
in both directions, as in a real rerun).
Tests:
  item  pooled paired difference, bootstrap 95% CI (normal approximation of the paired mean)
        excludes 0 AND point >= 0.10  (the prereg's "relies" rule)
  null  pooled upper bound < 0.10 (the prereg's "does not rely" rule), reported under each scenario
  sub   6 subtask means, cluster (subtask) bootstrap 95% CI excludes 0 (percentile, 300 per replicate)
  sign  sign-flip test over 6 subtask differences, two-sided p < 0.05 (min attainable 0.031)
Writes power.json.
"""
import json
from pathlib import Path

import numpy as np

FAMS = ["gc", "aaseq", "seqenz", "geneenz", "gibshind", "gibssma"]
H = {"gc": 0.12, "aaseq": 0.0, "seqenz": 0.0, "geneenz": 0.05, "gibshind": 0.52, "gibssma": 0.40}
PLANS = {"sonnet": {"gc": 6, "aaseq": 6, "seqenz": 6, "geneenz": 10, "gibshind": 10, "gibssma": 10},
         "haiku": {f: 15 for f in FAMS}}


def sim(plan, eff, pk=0.95, reps=2000, seed=0):
    rng = np.random.default_rng(seed)
    hits = {"item": 0, "null": 0, "sub": 0, "sign": 0}
    signs = np.array(np.meshgrid(*[[-1, 1]] * 6)).reshape(6, -1).T
    for _ in range(reps):
        diffs, means = [], []
        for f in FAMS:
            n = plan[f]
            pd_ = max(pk - eff[f], 0.0)
            k = rng.random(n) < pk
            q = (pd_ - 0.6 * pk) / 0.4
            d = np.where(rng.random(n) < 0.6, k, rng.random(n) < q)
            dd = k.astype(float) - d.astype(float)
            diffs.append(dd)
            means.append(dd.mean())
        allv = np.concatenate(diffs)
        m, se = allv.mean(), allv.std(ddof=1) / np.sqrt(len(allv)) if allv.std() > 0 else 0.0
        lo, hi = m - 1.96 * se, m + 1.96 * se
        hits["item"] += (lo > 0) and (m >= 0.10)
        hits["null"] += hi < 0.10
        means = np.array(means)
        bs = [means[rng.integers(0, 6, 6)].mean() for _ in range(300)]
        hits["sub"] += np.percentile(bs, 2.5) > 0
        obs = abs(means.mean())
        null = np.abs((signs * means).mean(1))
        hits["sign"] += np.mean(null >= obs - 1e-12) < 0.05
    return {k: round(v / reps, 3) for k, v in hits.items()}


def main():
    out = {}
    for model, plan in PLANS.items():
        out[model] = {"n_pairs": sum(plan.values()), "plan": plan,
                      "U_0.20": sim(plan, {f: 0.20 for f in FAMS}),
                      "H_haiku_pattern": sim(plan, H),
                      "U_0.10": sim(plan, {f: 0.10 for f in FAMS}),
                      "zero": sim(plan, {f: 0.0 for f in FAMS})}
    Path(__file__).resolve().parent.parent.joinpath("power.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
