"""Power of the pre-registered rule (prereg.md) by simulation. Seed 0, 5,000 draws per cell.

Model per pair: P(K right, D wrong) = drop + c, P(K wrong, D right) = c, with c = 0.01 (the
letter-only Sonnet run had 0 D-only pairs of 48). Pairs n = 48, 40 (the floor if the cap cuts), 20 (Gibson only).
"Yes" = diff >= 0.10 and exact two-sided McNemar p < 0.05. "No" = item-bootstrap upper < 0.10.
"""
import json
from math import comb
from pathlib import Path

import numpy as np


def p2(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def sim(n, drop, c=0.01, B=5000, seed=0):
    rng = np.random.default_rng(seed)
    yes = no = 0
    for _ in range(B):
        u = rng.random(n)
        b = int((u < drop + c).sum())
        cc = int(((u >= drop + c) & (u < drop + 2 * c)).sum())
        diff = (b - cc) / n
        if diff >= 0.10 and p2(b, cc) < 0.05:
            yes += 1
        d = np.r_[np.ones(b), -np.ones(cc), np.zeros(n - b - cc)]
        bs = [d[rng.integers(0, n, n)].mean() for _ in range(200)]
        if np.percentile(bs, 97.5) < 0.10:
            no += 1
    return {"yes": round(yes / B, 3), "no": round(no / B, 3)}


out = {f"n{n}_drop{dr}": sim(n, dr) for n in (48, 40, 20) for dr in (0.0, 0.10, 0.27)}
print(json.dumps(out, indent=1))
Path(__file__).resolve().parent.parent.joinpath("power.json").write_text(json.dumps(out, indent=1) + "\n")
