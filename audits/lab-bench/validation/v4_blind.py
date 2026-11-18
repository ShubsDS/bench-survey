"""Validator recomputation of claims 4-6 from the raw Haiku CSVs (not the auditor's analysis).

- Accuracy per (subset, condition), with errors (API refusals) dropped and unparsed counted wrong.
- Chance per item = 1 / (number of substantive options) for forced/opts; for std/blind the
  refusal option is excluded from the chance computation (picking it scores 0) and reported
  separately as 1 / (substantive + 1) for a uniform picker.
- Intervals: Wilson and a cluster bootstrap (ProtocolQA by protocol text, CloningScenarios by
  source, FigQA by figure hash where available; otherwise items).
- Claim 6 accounting: std accuracy counts a refusal as not correct (the paper's accuracy).
  Delta = acc_forced - acc_std on paired items; share of std refusals answered right when forced.
Run: data/.venv/bin/python -I validation/v4_blind.py
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

A = Path(__file__).resolve().parent.parent
frames = []
for b in ["b2_blind", "b3_protclone", "b4_opts", "b6b_litsupp", "b5b_seqstd5", "b1_l4"]:
    d = pd.read_csv(A / f"results/haiku_{b}.csv")
    d["batch"] = b
    frames.append(d)
d = pd.concat(frames)
d = d[d.cond != "edit"]
REFUSED_BY_API = set(d[d.bucket == "error"].id)
d = d[~d.id.isin(REFUSED_BY_API)]
d["c"] = (d.bucket == "correct").astype(float)
d["ref"] = (d.bucket == "refuse").astype(float)
d["chance"] = 1.0 / d.n_sub

clu = {}
for s, col in [("ProtocolQA", "source"), ("FigQA", "figure-path")]:
    t = pq.read_table(A / f"data/hf/{s}/train-00000-of-00001.parquet")
    keep = [c for c in t.column_names if c not in ("figure", "tables")]
    df = t.select(keep).to_pandas()
    if s == "ProtocolQA":
        df["pkey"] = df.protocol.str.split("\n").str[0].str[:60]  # protocol title line: 24 protocols
        col = "pkey"
    if col and col in df:
        clu.update({i: hashlib.sha1(str(v).encode()).hexdigest()[:10] for i, v in zip(df.id, df[col])})
rng = np.random.default_rng(0)


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(c - h, 3), round(c + h, 3)]


def cboot(g, col="c", B=2000):
    cl = g.id.map(lambda i: clu.get(i, i)).values
    u = np.unique(cl)
    idx = {k: np.where(cl == k)[0] for k in u}
    v = g[col].values
    bs = []
    for _ in range(B):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[k] for k in pick])
        bs.append(v[ii].mean())
    return [round(float(np.quantile(bs, q)), 3) for q in (0.025, 0.975)], int(len(u))


out = {}
for (s, c), g in d.groupby(["subset", "cond"]):
    g = g.drop_duplicates("id")
    ci, ncl = cboot(g)
    out[f"{s}|{c}"] = {"n": len(g), "acc": round(g.c.mean(), 3), "wilson": wilson(g.c.sum(), len(g)),
                       "cluster_ci": ci, "n_clusters": ncl, "chance": round(g.chance.mean(), 3),
                       "refusal_rate": round(g.ref.mean(), 3),
                       "precision": round(g.c.sum() / max(1, (1 - g.ref).sum()), 3)}
# paired forced vs std / blindf vs blind
pairs = {}
for s, a, b in [("ProtocolQA", "forced", "std"), ("CloningScenarios", "forced", "std"), ("LitQA2", "forced", "std"),
                ("SuppQA", "forced", "std"), ("FigQA", "blindf", "blind"), ("TableQA", "blindf", "blind"),
                ("FigQA", "blind", "last")]:
    x = d[(d.subset == s) & (d.cond == a)].drop_duplicates("id").set_index("id")
    y = d[(d.subset == s) & (d.cond == b)].drop_duplicates("id").set_index("id")
    ids = x.index.intersection(y.index)
    diff = (x.loc[ids].c - y.loc[ids].c).values
    bs = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
    r = {"n": len(ids), "delta_acc": round(float(diff.mean()), 3),
         "ci": [round(float(np.quantile(bs, q)), 3) for q in (0.025, 0.975)]}
    refused = y.loc[ids][y.loc[ids].ref == 1].index
    if len(refused) and a != "blind":
        r["refused_items_forced_acc"] = round(float(x.loc[refused].c.mean()), 3)
        r["refused_items_chance"] = round(float(x.loc[refused].chance.mean()), 3)
        r["n_refused"] = int(len(refused))
    if a == "blind":
        dr = (x.loc[ids].ref - y.loc[ids].ref).values
        bs = [dr[rng.integers(0, len(dr), len(dr))].mean() for _ in range(2000)]
        r["refusal_rate_diff_blind_minus_last"] = round(float(dr.mean()), 3)
        r["refusal_ci"] = [round(float(np.quantile(bs, q)), 3) for q in (0.025, 0.975)]
    pairs[f"{s}|{a}-{b}"] = r
out["paired"] = pairs
json.dump(out, open(A / "validation/v4_blind.json", "w"), indent=1)
for k, v in out.items():
    print(k, v)
