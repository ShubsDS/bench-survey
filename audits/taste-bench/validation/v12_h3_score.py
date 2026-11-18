"""Score the validator's H3 placebo arm against the auditor's H1 and H2 (Haiku only), task bootstrap."""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import DATA, SEED, save  # noqa: E402


def item_scores(name):
    sc, meta = defaultdict(list), {}
    for l in (DATA / name).read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            sc[r["id"]].append(bool(r.get("ok")))
            meta[r["id"]] = (r["cell"], r["task_id"])
    return {i: np.mean(v) for i, v in sc.items()}, meta, sum(json.loads(l).get("pred") is None
                                                          for l in (DATA / name).read_text().splitlines() if l.strip())


h1, meta, _ = item_scores("haiku_H1.jsonl")
h2, _, _ = item_scores("haiku_H2.jsonl")
h3, _, unp3 = item_scores("haiku_V_H3.jsonl")
ids = sorted(set(h1) & set(h2) & set(h3))
det = np.array([meta[i][0].startswith("detour") for i in ids])
tasks = np.array([meta[i][0] + "|" + meta[i][1] for i in ids])
rng = np.random.default_rng(SEED)
ut = np.unique(tasks)
idx_by = {t: np.where(tasks == t)[0] for t in ut}


def contrast(a, b, sel=None):
    d = np.array([a[i] - b[i] for i in ids])
    return (d[det].mean() - d[~det].mean()) * 100, d[det].mean() * 100, d[~det].mean() * 100


def boot(a, b):
    d = np.array([a[i] - b[i] for i in ids])
    vals = []
    for _ in range(2000):
        pick = np.concatenate([idx_by[t] for t in rng.choice(ut, len(ut))])
        dd, dt = d[pick], det[pick]
        vals.append((dd[dt].mean() - dd[~dt].mean()) * 100)
    return [round(float(np.percentile(vals, 2.5)), 1), round(float(np.percentile(vals, 97.5)), 1)]


out = {"n_items": len(ids), "h3_unparsed_presentations": int(unp3)}
for name, a, b in (("H2_minus_H1", h2, h1), ("H3_minus_H1", h3, h1), ("H2_minus_H3", h2, h3)):
    c, dd, dp = contrast(a, b)
    out[name] = {"detour_minus_parallel": round(c, 2), "detour": round(dd, 2), "parallel": round(dp, 2),
                 "ci_task_boot": boot(a, b)}
for name, a in (("H1", h1), ("H2", h2), ("H3", h3)):
    v = np.array([a[i] for i in ids])
    out[f"{name}_single_order"] = {"detour": round(float(v[det].mean() * 100), 1), "parallel": round(float(v[~det].mean() * 100), 1)}
save("v12_h3_score.json", out)
print(json.dumps(out, indent=1))
