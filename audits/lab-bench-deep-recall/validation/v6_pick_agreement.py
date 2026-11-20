"""Validator v6: agreement between the auditor's blind picks and each model's no-protocol picks
(by option role, so option order does not matter), the reorder control on the paraphrase subset,
and the Sonnet paraphrase drop without the items whose paraphrase the validator judged changed.
Writes validation/v6_pick_agreement.json. Run with python3 -I.
"""
import csv
import json
import re
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
R = {r.id: r for _, r in df[df.subset == "ProtocolQA"].iterrows()}
id8 = {i[:8]: i for i in R}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


role_of = {}
for i, r in R.items():
    role_of[(i, norm(r.ideal))] = "key"
    for k, d in enumerate(r.distractors):
        role_of[(i, norm(d))] = f"d{k}"
sheet = {}
for f in sorted((AUD / "data").glob("label_sheet_*.txt")):
    cur = None
    for ln in f.read_text().split("\n"):
        m = re.match(r"#\d+ (\w{8})", ln)
        if m:
            cur = id8[m.group(1)]
            sheet[cur] = {}
            continue
        m = re.match(r"\s+\(([A-Z])\) (.*)$", ln)
        if m and cur:
            sheet[cur][m.group(1)] = role_of.get((cur, norm(m.group(2))))
lab = {id8[r["id8"]]: r for r in csv.DictReader(open(AUD / "labels" / "labels.csv"))}
apick = {i: sheet[i].get(lab[i]["pick"]) for i in lab}
assert all(v is not None for v in apick.values()), [k for k, v in apick.items() if v is None]
assert all((apick[i] == "key") == (lab[i]["pick_is_key"] == "True") for i in lab)

picks = defaultdict(dict)
cor = defaultdict(dict)
for r in csv.DictReader(open(HERE / "v2_items.csv")):
    if r["subset"] == "ProtocolQA":
        picks[(r["model"], r["style"], r["arm"])][r["id"]] = r["picked"]
        cor[(r["model"], r["style"], r["arm"])][r["id"]] = int(r["correct"])
out = {"auditor_pick_accuracy": round(np.mean([apick[i] == "key" for i in apick]), 4), "agreement": {}}
for name, cell in [("sonnet_qo", ("sonnet", "direct", "qo")), ("haiku_qo", ("haiku", "cot", "qo")),
                   ("haiku_opts", ("haiku", "cot", "opts")), ("haiku_full", ("haiku", "cot", "full"))]:
    p = picks[cell]
    ag = [apick[i] == p[i] for i in p]
    both_wrong = [i for i in p if apick[i] != "key" and p[i] != "key"]
    out["agreement"][name] = {"n": len(ag), "agree": round(float(np.mean(ag)), 4),
                              "agree_when_both_wrong": round(float(np.mean([apick[i] == p[i] for i in both_wrong])), 4) if both_wrong else None,
                              "n_both_wrong": len(both_wrong)}
hp = picks[("haiku", "cot", "qo")]; sp = picks[("sonnet", "direct", "qo")]
bw = [i for i in hp if hp[i] != "key" and sp[i] != "key"]
out["agreement"]["haiku_qo_vs_sonnet_qo"] = {"agree": round(float(np.mean([hp[i] == sp[i] for i in hp])), 4),
                                             "agree_when_both_wrong": round(float(np.mean([hp[i] == sp[i] for i in bw])), 4), "n_both_wrong": len(bw)}
# chance agreement when both wrong: 1/(k-1) averaged
out["agreement"]["chance_agree_when_both_wrong"] = round(float(np.mean([1 / (len(R[i].distractors)) for i in R if not i.startswith("bee8")])), 4)

# reorder control on the 91 paraphrase items
P = list(cor[("haiku", "cot", "opts_pa")])
o, ro = cor[("haiku", "cot", "opts")], cor[("haiku", "cot", "opts_ro")]
q, qro = cor[("haiku", "cot", "qo")], cor[("haiku", "cot", "qo_ro")]
out["reorder_on_91"] = {"opts_minus_opts_ro": round(np.mean([o[i] - ro[i] for i in P]), 4),
                        "qo_minus_qo_ro": round(np.mean([q[i] - qro[i] for i in P]), 4)}

# Sonnet paraphrase drop without the items the validator judged changed in meaning (hand read,
# NOT blind to outcome: the read sheet showed each item's Sonnet result)
DRIFT = ["36cae278", "3b5bd87a", "e8afd1c6", "abfb2fec", "520f4620", "16fc3385"]
s0, s1 = cor[("sonnet", "direct", "qo")], cor[("sonnet", "direct", "qo_pa")]
h0, h1 = cor[("haiku", "cot", "qo_ro")], cor[("haiku", "cot", "qo_pa")]
keep = [i for i in s1 if i[:8] not in DRIFT]
CL = {i: R[i].cluster for i in R}
rng = np.random.default_rng(0)


def cboot(f, ids):
    by = defaultdict(list)
    for i in ids:
        by[CL[i]].append(i)
    cs = list(by)
    v = []
    for _ in range(2000):
        s = [i for j in rng.integers(0, len(cs), len(cs)) for i in by[cs[j]]]
        v.append(f(s))
    return [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)]


out["sonnet_pa_without_drift"] = {
    "drift_items": DRIFT, "n": len(keep),
    "drop": round(float(np.mean([s0[i] - s1[i] for i in keep])), 4),
    "ci": cboot(lambda s: np.mean([s0[i] - s1[i] for i in s]), keep),
    "lost": sum(s0[i] and not s1[i] for i in keep), "gained": sum(s1[i] and not s0[i] for i in keep),
    "drift_items_sonnet_lost": [d for d in DRIFT if s0[id8[d]] and not s1[id8[d]]],
    "haiku_drop_without_drift": round(float(np.mean([h0[i] - h1[i] for i in keep])), 4),
    "haiku_ci": cboot(lambda s: np.mean([h0[i] - h1[i] for i in s]), keep),
}
json.dump(out, open(HERE / "v6_pick_agreement.json", "w"), indent=1)
print(json.dumps(out, indent=1))
