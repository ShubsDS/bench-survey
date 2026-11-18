"""Validator re-derivation of claim 1 (and claim 8) without the auditor's code.

Two centre rules, both fixed before looking at any accuracy:
  - edit medoid: the option with the smallest summed Levenshtein distance to the other options
    (characters, case-sensitive, whitespace stripped);
  - numeric medoid: when every option parses as a number, the option with the smallest summed
    absolute difference to the others.
"combined": numeric medoid if all options are numeric, else edit medoid. Nothing is chosen on
the data. Ties get fractional credit. Null: the key drawn uniformly among an item's options
(equivalent to shuffling the key position, since the rules are order-invariant), 1,000 draws,
within subtask. Item text is never written out.

Run: data/.venv/bin/python -I validation/v1_rule.py
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

A = Path(__file__).resolve().parent.parent
SHA = {
    "SeqQA": "5864776d3d85774f91d82432e30ac31e9222f1670621e8ea141414173c5e9b46",
    "DbQA": "0f20e6de5f2a7afeaeba8b2f7bfcd16146540c92b7405496476b8335eca33e46",
}


def load(s):
    p = A / "data/hf" / s / "train-00000-of-00001.parquet"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == SHA[s]
    df = pq.read_table(p).to_pandas()
    df["subtask"] = df["subtask"].str.replace("-public", "").str.replace("-v1", "")
    return df


def lev(a, b):
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    bb = np.frombuffer(b.encode("utf-32-le"), dtype=np.uint32)
    prev = np.arange(len(b) + 1)
    j = np.arange(len(b) + 1)
    for ch in a:
        c = np.uint32(ord(ch))
        cost = (bb != c).astype(int)
        t = np.empty_like(prev)
        t[0] = prev[0] + 1
        t[1:] = np.minimum(prev[1:] + 1, prev[:-1] + cost)
        prev = j + np.minimum.accumulate(t - j)
    return int(prev[-1])


NUM = re.compile(r"^[-+]?\d+(\.\d+)?%?$")


def scores(opts):
    """Lower is more central. Returns (kind, array)."""
    o = [x.strip() for x in opts]
    if all(NUM.match(x) for x in o):
        v = np.array([float(x.rstrip("%")) for x in o])
        return "num", np.abs(v[:, None] - v[None, :]).sum(1)
    k = len(o)
    d = np.zeros((k, k))
    for i in range(k):
        for jj in range(i + 1, k):
            d[i, jj] = d[jj, i] = lev(o[i], o[jj])
    return "edit", d.sum(1)


def credit(sc, key_idx):
    m = sc.min()
    w = (sc == m).astype(float)
    w /= w.sum()
    return w[key_idx], w


def run(subset):
    df = load(subset)
    rng = np.random.default_rng(0)
    out = {}
    per_item = []
    for st, g in df.groupby("subtask"):
        accs, ws, kinds = [], [], []
        for _, r in g.iterrows():
            opts = [r["ideal"]] + list(r["distractors"])
            kind, sc = scores(opts)
            c, w = credit(sc, 0)
            accs.append(c)
            ws.append(w)
            kinds.append(kind)
            per_item.append({"id": r["id"], "subtask": st, "credit": round(float(c), 4), "kind": kind})
        obs = float(np.mean(accs))
        null = np.array([np.mean([w[rng.integers(len(w))] for w in ws]) for _ in range(1000)])
        out[st] = {
            "n": len(g),
            "acc": round(obs, 4),
            "n_full_credit": int(sum(a == 1.0 for a in accs)),
            "chance": round(float(np.mean([1 / len(w) for w in ws])), 4),
            "null_95": [round(float(np.quantile(null, q)), 4) for q in (0.025, 0.975)],
            "p_perm": round(float((1 + (null >= obs).sum()) / 1001), 4),
            "kind": max(set(kinds), key=kinds.count),
        }
    return out, per_item


if __name__ == "__main__":
    res = {}
    for s in ["SeqQA", "DbQA"]:
        out, items = run(s)
        res[s] = out
        tot = sum(v["acc"] * v["n"] for v in out.values()) / sum(v["n"] for v in out.values())
        res[s + "_overall"] = round(tot, 4)
        res[s + "_full_credit_subtasks"] = [k for k, v in out.items() if v["acc"] == 1.0]
        res[s + "_full_credit_items"] = sum(v["n"] for k, v in out.items() if v["acc"] == 1.0)
        # cluster bootstrap over subtasks for the overall number
        rng = np.random.default_rng(1)
        keys = list(out)
        bs = []
        for _ in range(2000):
            pick = rng.choice(keys, len(keys))
            bs.append(np.mean([out[k]["acc"] for k in pick]))
        res[s + "_overall_ci_subtask_bootstrap"] = [round(float(np.quantile(bs, q)), 4) for q in (0.025, 0.975)]
        json.dump(items, open(A / f"validation/v1_items_{s}.json", "w"))
    json.dump(res, open(A / "validation/v1_rule.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
