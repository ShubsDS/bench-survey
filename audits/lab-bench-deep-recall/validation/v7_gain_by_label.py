"""Validator v7: protocol gain (full minus qo) by label set, with cluster intervals; checks the
auditor's exploratory "the protocol adds little on standard-key items" under key-blind labels.
Writes validation/v7_gain_by_label.json. Run with python3 -I.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
sys.path.insert(0, str(AUD.parent / "lab-bench" / "scripts"))
from common import load_items, clusters  # noqa: E402

df = load_items()
df["cluster"] = clusters(df)
pq = df[(df.subset == "ProtocolQA") & (~df.id.str.startswith("bee8b322"))]
CL = dict(zip(pq.id, pq.cluster))
id8 = {i[:8]: i for i in CL}
cor = defaultdict(dict)
for r in csv.DictReader(open(HERE / "v2_items.csv")):
    if r["subset"] == "ProtocolQA":
        cor[(r["model"], r["arm"], r["style"])][r["id"]] = int(r["correct"])
mine = {id8[r["id8"]]: r for r in csv.DictReader(open(HERE / "v1_labels.csv"))}
aud = {id8[r["id8"]]: r for r in csv.DictReader(open(AUD / "labels" / "labels.csv"))}
SETS = {
    "validator_K": {i for i, r in mine.items() if r["U"] == "1" and r["S"] == "1" and r["T"] != "NUM"},
    "auditor_G_keyblind": {i for i, r in aud.items() if r["class"] == "G"},
    "auditor_standard_key": {i for i, r in aud.items() if r["standard_key"] == "True"},
}
rng = np.random.default_rng(0)


def cboot(f, ids):
    by = defaultdict(list)
    for i in ids:
        by[CL[i]].append(i)
    cs = list(by)
    v = [f([i for j in rng.integers(0, len(cs), len(cs)) for i in by[cs[j]]]) for _ in range(2000)]
    return [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]


out = {}
for model, style in [("haiku", "cot"), ("sonnet", "direct")]:
    full, qo = cor[(model, "full", style)], cor[(model, "qo", style)]
    for name, S in SETS.items():
        for side, sel in [("in", True), ("out", False)]:
            ids = [i for i in full if (i in S) == sel]
            out[f"{model}|{name}|{side}"] = {
                "n": len(ids), "full": round(float(np.mean([full[i] for i in ids])), 3),
                "qo": round(float(np.mean([qo[i] for i in ids])), 3),
                "gain": round(float(np.mean([full[i] - qo[i] for i in ids])), 3),
                "gain_ci": cboot(lambda s: np.mean([full[i] - qo[i] for i in s]), ids)}
json.dump(out, open(HERE / "v7_gain_by_label.json", "w"), indent=1)
for k, v in out.items():
    print(k, v)

# R3 check: no-protocol accuracy on the auditor's D items against the plausible-set ceiling mean(1/m)
D = [i for i, r in aud.items() if r["class"] == "D"]
ceil = float(np.mean([1 / int(aud[i]["m"]) for i in D]))
r3 = {"n_D": len(D), "ceiling": round(ceil, 3)}
for model, style in [("haiku", "cot"), ("sonnet", "direct")]:
    qo = cor[(model, "qo", style)]
    r3[model] = {"acc": round(float(np.mean([qo[i] for i in D])), 3),
                 "minus_ceiling_ci": cboot(lambda s: np.mean([qo[i] for i in s]) - np.mean([1 / int(aud[i]["m"]) for i in s]), D)}
out["R3"] = r3
json.dump(out, open(HERE / "v7_gain_by_label.json", "w"), indent=1)
print(r3)
