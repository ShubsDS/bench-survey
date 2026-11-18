"""Validator's own drop-k test for C1a. Queries are ranked by their mean gap contribution (free minus
paid compliance) over the 43 Opus helpful-only variants other than the default, so the ranking never
sees the default cell. The top k are removed from the default cell. Three references:
  R1: k random queries from all 352 default queries;
  R2: k random queries from the 172 queries the ranking can pick from;
  oracle: the k queries with the largest in-sample contribution (the most that removing k can do).
Seed 12345, 2000 draws. Writes validation/dropk.json.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
from rederive import OPUS, paired  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(12345)

f, p, q = paired("atn_honly", "c_pm")
diff = dict(zip(q, f - p))
g0 = (f - p).mean()

contrib = {}
for v in OPUS:
    if v == "atn_honly":
        continue
    a, b, qq = paired(v, "c_pm")
    for i, d in zip(qq, a - b):
        contrib.setdefault(i, []).append(d)
pool = [i for i, xs in contrib.items() if len(xs) >= 30 and i in diff]
score = {i: np.mean(contrib[i]) for i in pool}
rank = sorted(pool, key=lambda i: -score[i])


def removed_share(drop):
    keep = [d for i, d in diff.items() if i not in drop]
    return 1 - np.mean(keep) / g0


out = {"n_default": len(q), "pool": len(pool), "b": int((f - p == 1).sum()), "c": int((f - p == -1).sum())}
for k in (5, 10, 20):
    t = removed_share(set(rank[:k]))
    r1 = [removed_share(set(rng.choice(q, k, replace=False))) for _ in range(2000)]
    r2 = [removed_share(set(rng.choice(pool, k, replace=False))) for _ in range(2000)]
    oracle = removed_share(set(sorted(diff, key=lambda i: -diff[i])[:k]))
    out[f"k={k}"] = dict(targeted=t, R1_p95=float(np.percentile(r1, 95)), R1_pct=float((np.array(r1) >= t).mean()),
                         R2_p95=float(np.percentile(r2, 95)), R2_pct=float((np.array(r2) >= t).mean()),
                         oracle_in_sample=oracle,
                         n_top_k_that_are_b=int(sum(diff[i] == 1 for i in rank[:k])))
json.dump(out, open(os.path.join(HERE, "dropk.json"), "w"), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
