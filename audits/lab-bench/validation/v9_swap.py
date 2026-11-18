"""Validator's own L4 control for claim 2: a single-option swap on the two Gibson subtasks.

Pre-registered in validation/prereg_v9_swap.md (committed before any call of this script with
--run). Original Gibson options are {K, S, G, W}:
  K key; S key overlap + frame-shifted body; G key overlap + another gene's body;
  W the other site's overlap + the key's body.
swap1 replaces W only, by WS = W's overlap + S's body. K, S, G, the question, the prompt and the
option order (perm_for on the item id, identical to the auditor's forced arm) are unchanged.
W and WS both carry the wrong overlap, so either can be rejected by the same check. The only
change is whether the wrong-overlap option shares its body with K or with S.

Roles are written in the order [K, S, WS, G] -> key, d0 (=S), d1 (=WS), d2 (=G).

--build : construct, check (no inference), write data/v9_swap_options.json and
          validation/v9_build.json (ids and checks, no item text)
--run   : run forced (cached for the 50 already-run items) and swap1, write
          validation/v9_swap_runs.csv and validation/v9_swap.json
Run: data/.venv/bin/python -I validation/v9_swap.py --build | --run
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

A = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(A / "scripts"))
sys.path.insert(0, str(A.parents[0] / "tools"))
exec((A / "validation/v1_rule.py").read_text().split("if __name__")[0].replace("Path(__file__)", "Path(%r)" % str(A / "validation/v1_rule.py")))


def grams3(s):
    return {s[i:i + 3] for i in range(len(s) - 2)}


def jac_centre(opts):
    g = [grams3(o) for o in opts]
    k = len(opts)
    m = [np.mean([len(g[i] & g[j]) / len(g[i] | g[j]) for j in range(k) if j != i]) for i in range(k)]
    m = np.array(m)
    return m  # higher is more central


def csuf(a, b):
    n = 0
    while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
        n += 1
    return n


def build_one(r):
    K = [x.strip() for x in r["ideal"].split(",")]
    D = [[x.strip() for x in d.split(",")] for d in r["distractors"]]
    # W: the distractor sharing the longest suffixes (bodies) with K on both primers
    suf = [csuf(K[0], d[0]) + csuf(K[1], d[1]) for d in D]
    wi = int(np.argmax(suf))
    W = D[wi]
    pk = [len(K[t]) - csuf(K[t], W[t]) for t in (0, 1)]
    pw = [len(W[t]) - csuf(K[t], W[t]) for t in (0, 1)]
    rest = [d for i, d in enumerate(D) if i != wi]
    # both remaining options must start with K's overlap
    if not all(d[t].startswith(K[t][:pk[t]]) for d in rest for t in (0, 1)):
        return None, "rest_not_key_overlap"
    # S: remaining option with the smallest summed edit distance of bodies to K's bodies
    bd = [sum(lev(K[t][pk[t]:], d[t][pk[t]:]) for t in (0, 1)) for d in rest]
    if bd[0] == bd[1]:
        return None, "S_ambiguous"
    S, G = (rest[0], rest[1]) if bd[0] < bd[1] else (rest[1], rest[0])
    WS = [W[t][:pw[t]] + S[t][pk[t]:] for t in (0, 1)]
    opts = [", ".join(K), ", ".join(S), ", ".join(WS), ", ".join(G)]
    orig = [r["ideal"]] + list(r["distractors"])
    if len(set(opts)) < 4:
        return None, "duplicate"
    return {"orig": orig, "swap1": opts}, "ok"


def checks(o):
    out = {}
    for arm in ("orig", "swap1"):
        _, sc = scores(o[arm])
        jc = jac_centre(o[arm])
        L = [len(x) for x in o[arm]]
        out[arm] = {"lev_centre": [i for i in range(4) if sc[i] == sc.min()],
                    "jac_centre": [i for i in range(4) if jc[i] == jc.max()],
                    "key_unique_longest": L[0] == max(L) and L.count(max(L)) == 1,
                    "key_unique_shortest": L[0] == min(L) and L.count(min(L)) == 1}
    return out


def build():
    df = load("SeqQA")
    g = df[df.subtask.str.contains("gibs")]
    opts, rep = {}, []
    for _, r in g.iterrows():
        o, why = build_one(r)
        row = {"id": r["id"], "subtask": r["subtask"], "status": why}
        if o is not None:
            # orig options as stored must be K + distractors; identify W in orig ordering
            c = checks({"orig": o["orig"], "swap1": o["swap1"]})
            ok = c["swap1"]["lev_centre"] == [1] and c["swap1"]["jac_centre"] == [1]
            row.update({"checks": c, "S_unique_centre_both_rules": ok})
            if ok:
                opts[r["id"]] = o
            else:
                row["status"] = "centre_check_failed"
        rep.append(row)
    (A / "data/v9_swap_options.json").write_text(json.dumps(opts))
    summ = {"n_gibson": len(g), "n_built": len(opts),
            "status_counts": pd.Series([x["status"] for x in rep]).value_counts().to_dict(),
            "key_unique_longest_orig": float(np.mean([x["checks"]["orig"]["key_unique_longest"] for x in rep if x["id"] in opts])),
            "key_unique_longest_swap1": float(np.mean([x["checks"]["swap1"]["key_unique_longest"] for x in rep if x["id"] in opts])),
            "key_unique_shortest_swap1": float(np.mean([x["checks"]["swap1"]["key_unique_shortest"] for x in rep if x["id"] in opts])),
            "orig_key_lev_centre": float(np.mean([x["checks"]["orig"]["lev_centre"] == [0] for x in rep if x["id"] in opts])),
            "ids": sorted(opts)}
    json.dump({"summary": summ, "items": rep}, open(A / "validation/v9_build.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summ.items() if k != "ids"}, indent=1))


def run():
    import haiku  # the auditor's renderer and runner (same template, same option order)
    items = haiku.load_items().set_index("id", drop=False)
    O = json.loads((A / "data/v9_swap_options.json").read_text())
    screen = json.loads((A / "results/screen.json").read_text())
    excluded = {h["id"] for h in screen["hits"] if h["decision"] == "exclude"}
    jobs = []
    for i, o in O.items():
        assert i not in excluded
        r = items.loc[i]
        for cond, opts in (("forced", None), ("swap1", o["swap1"])):
            prompt, roles = haiku.render(r, "forced", opts)
            jobs.append({"id": i, "family": r.family, "cond": cond, "prompt": prompt, "roles": roles})
    before = haiku.Caller(str(A)).spent()
    df = haiku.run(jobs, threads=6)
    after = haiku.Caller(str(A)).spent()
    df["roles"] = df["roles"].map(json.dumps)
    df.drop(columns=["prompt"]).to_csv(A / "validation/v9_swap_runs.csv", index=False)
    d = df.copy()
    d["c"] = (d.bucket == "correct").astype(float)
    w = d.pivot_table(index="id", columns="cond", values="c")
    pk = d[d.cond == "swap1"].set_index("id").picked_role
    pf = d[d.cond == "forced"].set_index("id").picked_role
    rng = np.random.default_rng(0)
    diff = (w.forced - w.swap1).values
    bs = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
    prev50 = set(json.loads((A / "plans/b7_placebo_edit.json").read_text())["pedit"])
    res = {"n": int(len(w)), "spent_usd": round(after - before, 4), "total_usd": round(after, 4),
           "buckets": d.groupby("cond").bucket.value_counts().unstack(fill_value=0).to_dict(),
           "forced": round(float(w.forced.mean()), 3), "swap1": round(float(w.swap1.mean()), 3),
           "drop": round(float(diff.mean()), 3),
           "drop_ci": [round(float(np.quantile(bs, q)), 3) for q in (0.025, 0.975)],
           "pick_S_forced": round(float((pf == "d0").mean()), 3), "pick_S_swap1": round(float((pk == "d0").mean()), 3),
           "pick_WS_swap1": round(float((pk == "d1").mean()), 3), "pick_G_swap1": round(float((pk == "d2").mean()), 3),
           "by_subtask": {}, "fresh_vs_previous": {}}
    fam = d.drop_duplicates("id").set_index("id").family
    for f in fam.unique():
        ids = fam[fam == f].index
        res["by_subtask"][f] = {"n": len(ids), "forced": round(float(w.loc[ids].forced.mean()), 3),
                                "swap1": round(float(w.loc[ids].swap1.mean()), 3)}
    for name, ids in (("previous_50", [i for i in w.index if i in prev50]), ("fresh", [i for i in w.index if i not in prev50])):
        res["fresh_vs_previous"][name] = {"n": len(ids), "forced": round(float(w.loc[ids].forced.mean()), 3),
                                          "swap1": round(float(w.loc[ids].swap1.mean()), 3)}
    json.dump(res, open(A / "validation/v9_swap.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    build() if sys.argv[1] == "--build" else run()
