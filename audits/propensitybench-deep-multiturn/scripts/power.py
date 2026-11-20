"""Power of the pre-registered three-arm design (prereg.md), by simulation. Pure Python, seed fixed.

Model: scenario s has a per-run misaligned probability p_s ~ Beta(mean = base rate, concentration 2),
shared by all arms (scenario heterogeneity; arms paired by scenario). Shipped (A) and placebo (P) runs
are Bernoulli(p_s); prohibition-restored (B) runs are Bernoulli(p_s * (1 - r)). Each scenario
contributes k runs per arm (k = number of pressure categories run). Intervals: percentile bootstrap
over scenarios stratified by domain (16 + 16 at n = 32), 400 resamples.

Reported, per base rate, n and r:
  P(yes)  = P(A-B >= 10 pts with CI > 0, and D = (A-B)-(A-P) >= 10 pts with CI > 0)
  P(no)   = P(D's CI within +/-15 pts and A >= 20%)     (computed with r = 0)
  P(0 shipped successes in the pilot) at the pilot size.

    python3 -I scripts/power.py  -> power.json
"""
import json
import random
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
SIMS, BOOT = 300, 400


def beta(rng, mean, conc=2.0):
    return rng.betavariate(mean * conc, (1 - mean) * conc)


def sim_once(rng, n, k, base, r):
    rows = []
    for i in range(n):
        p = beta(rng, base)
        a = sum(rng.random() < p for _ in range(k)) / k
        pl = sum(rng.random() < p for _ in range(k)) / k
        b = sum(rng.random() < p * (1 - r) for _ in range(k)) / k
        rows.append((i % 2, a, pl, b))
    return rows


def stats(rows):
    n = len(rows)
    A = sum(x[1] for x in rows) / n
    P = sum(x[2] for x in rows) / n
    B = sum(x[3] for x in rows) / n
    return A, A - B, (A - B) - (A - P)


def ci(rng, rows):
    strata = [[x for x in rows if x[0] == d] for d in (0, 1)]
    ab, dd = [], []
    for _ in range(BOOT):
        s = [rng.choice(st) for st in strata for _ in st]
        _, x, y = stats(s)
        ab.append(x); dd.append(y)
    ab.sort(); dd.sort()
    lo, hi = int(0.025 * BOOT), int(0.975 * BOOT) - 1
    return (ab[lo], ab[hi]), (dd[lo], dd[hi])


def power(n, k, base, r, seed):
    rng = random.Random(seed)
    yes = no = 0
    for _ in range(SIMS):
        rows = sim_once(rng, n, k, base, r)
        A, ab, d = stats(rows)
        (ablo, _), (dlo, dhi) = ci(rng, rows)
        if ab >= 0.10 and ablo > 0 and d >= 0.10 and dlo > 0:
            yes += 1
        if dlo >= -0.15 and dhi <= 0.15 and A >= 0.20:
            no += 1
    return yes / SIMS, no / SIMS


def main():
    out = {"model": __doc__.split("\n\n")[1], "sims": SIMS, "boot": BOOT, "seed": 20261120, "cells": []}
    designs = [("haiku_affordable", 6, 1), ("haiku_10", 10, 1), ("one_category_all_32", 32, 1),
               ("local_32x6", 32, 6)]
    seed = 20261120
    for name, n, k in designs:
        for base in (0.05, 0.20, 0.50):
            for r in (0.0, 0.5, 1.0):
                seed += 1
                py, pn = power(n, k, base, r, seed)
                out["cells"].append({"design": name, "n_scenarios": n, "runs_per_scenario_per_arm": k,
                                     "base_rate": base, "relative_reduction": r, "P_yes": py,
                                     "P_no": pn if r == 0.0 else None})
                print(name, n, k, base, r, py, pn)
    # chance that a pilot of n shipped runs shows 0 misaligned, by base rate (independent runs; heterogeneity
    # raises it further)
    out["pilot_zero_prob"] = {str(n): {str(b): round((1 - b) ** n, 4) for b in (0.05, 0.10, 0.20, 0.50)}
                              for n in (16, 20, 32)}
    (FOLDER / "power.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
