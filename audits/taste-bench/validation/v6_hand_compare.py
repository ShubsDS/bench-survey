"""V6: compare the validator's blind labels (committed in 300a7ca before this script ran) with the key."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import DATA, HERE, SEED, features, load, save  # noqa: E402

rows = {r["id"]: r for r in load()}
F = {f["id"]: f for f in features(list(rows.values()))}
labs = list(csv.DictReader((HERE / "v6_blind_labels.csv").open()))


def haiku(cond):
    out = defaultdict(dict)
    for l in (DATA / f"haiku_{cond}.jsonl").read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            out[r["id"]][r["order"]] = r
    return out


H = {c: haiku(c) for c in ("H0", "H1")}
recs = []
for l in labs:
    i = l["id"]
    r = rows[i]
    key = "AB"[r["answer_index"]]
    f = F[i]
    d = f["cont"][1] - f["cont"][0]
    lower_cont = None if d == 0 else ("A" if d > 0 else "B")  # lower cont = the option with the smaller value
    dg = f["ground"][1] - f["ground"][0]
    lower_ground = None if dg == 0 else ("A" if dg > 0 else "B")
    hk = {}
    for c in H:
        s = H[c].get(i, {}).get("seeded")
        hk[c] = None if s is None or s.get("pred") is None else s["pred"]  # seeded order = published order
    recs.append({"id": i, "task": r["task_id"], "me": l["validator_choice_published_order"],
                 "conf": int(l["confidence"]), "key": key, "lower_cont": lower_cont, "lower_ground": lower_ground,
                 "haiku_H0_seeded": hk["H0"], "haiku_H1_seeded": hk["H1"]})


def agree(sub, a, b):
    v = [x[a] == x[b] for x in sub if x[a] is not None and x[b] is not None]
    return len(v), sum(v)


rng = np.random.default_rng(SEED)


def boot(sub, a, b, n=2000):
    tasks = sorted({x["task"] for x in sub})
    by = defaultdict(list)
    for x in sub:
        by[x["task"]].append(x)
    vals = []
    for _ in range(n):
        pick = rng.choice(len(tasks), len(tasks), replace=True)
        s = [y for k in pick for y in by[tasks[k]]]
        m, k = agree(s, a, b)
        vals.append(k / m if m else np.nan)
    return [round(float(np.nanpercentile(vals, 2.5)) * 100, 1), round(float(np.nanpercentile(vals, 97.5)) * 100, 1)]


out = {"n": len(recs), "n_tasks": len({x['task'] for x in recs}),
       "confidence_counts": {str(c): sum(x["conf"] == c for x in recs) for c in (1, 2, 3)}}
for name, sub in (("all", recs), ("conf_ge2", [x for x in recs if x["conf"] >= 2]),
                  ("conf3", [x for x in recs if x["conf"] == 3]), ("conf1", [x for x in recs if x["conf"] == 1])):
    blk = {}
    for a, b in (("me", "key"), ("me", "lower_cont"), ("lower_cont", "key"), ("lower_ground", "key"),
                 ("me", "lower_ground"), ("haiku_H0_seeded", "key"), ("me", "haiku_H0_seeded"),
                 ("haiku_H1_seeded", "key")):
        m, k = agree(sub, a, b)
        blk[f"{a}_vs_{b}"] = {"n": m, "agree": k, "rate": round(k / m * 100, 1) if m else None}
    blk["me_vs_key_ci_task_boot"] = boot(sub, "me", "key") if len(sub) >= 10 else None
    out[name] = blk
# exact binomial two-sided p for me vs key against 0.5
from scipy.stats import binomtest  # noqa: E402
m, k = agree(recs, "me", "key")
out["all"]["me_vs_key_binom_p_vs_50"] = round(binomtest(k, m, 0.5).pvalue, 4)
# among items where I agree with the key vs not: is the key's option the lower-cont one?
out["per_item"] = [{"id": x["id"], "me": x["me"], "conf": x["conf"], "key": x["key"],
                    "lower_cont": x["lower_cont"]} for x in recs]
save("v6_hand_compare.json", out)
print(json.dumps({k: v for k, v in out.items() if k != "per_item"}, indent=1))
