"""Analyse the validator's blind hand labels (prereg_validator.md). Reads handlabels_validator_raw.csv
(item, label), the key data/val_hl_key.csv, and the auditor's key and labels. Writes
handlabels_validator.csv (ids, strata and labels only) and handlabels_validator.json.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rederive import D, OPUS, paired  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
lab = pd.read_csv(os.path.join(HERE, "handlabels_validator_raw.csv"))
key = pd.read_csv(os.path.join(DATA, "val_hl_key.csv"))
h = key.merge(lab, on="item")
ak = pd.read_csv(os.path.join(DATA, "handlabel_key.csv"))
al = pd.read_csv(os.path.join(HERE, "..", "results", "handlabels.csv"))
aud = ak.merge(al, on="item")[["item", "hand"]].rename(columns={"item": "auditor_item", "hand": "auditor_hand"})
h = h.merge(aud, on="auditor_item", how="left")
h[["item", "src", "auditor_item", "variant", "tier", "qid", "cat", "hand", "disclaimer", "empty_output", "auditor_hand"]].to_csv(
    os.path.join(HERE, "handlabels_validator.csv"), index=False)


def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a) | set(b))
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


out = {"n": len(h), "by_stratum": {}}
for (t, c), g in h.groupby(["tier", "cat"]):
    out["by_stratum"][f"{t}|cat{c}"] = dict(n=len(g), F=int((g.hand == "F").sum()), F_no_disclaimer=int(((g.hand == "F") & (g.disclaimer == 0)).sum()),
                                           P=int((g.hand == "P").sum()), R=int((g.hand == "R").sum()), empty=int(g.empty_output.sum()))
o = h[h.src == "auditor"]
out["vs_auditor"] = dict(n=len(o), agreement=float((o.hand == o.auditor_hand).mean()), kappa=float(kappa(o.hand, o.auditor_hand)),
                         crosstab={f"{a}|{b}": int(((o.hand == a) & (o.auditor_hand == b)).sum()) for a in "FPR" for b in "FPR"})
# classifier vs hand (all 80)
fi = (h.cat == 4); c34 = h.cat >= 3
F = (h.hand == "F"); Fs = F & (h.disclaimer == 0)
out["vs_classifier"] = dict(
    kappa_F_vs_cat34=float(kappa(F, c34)), agree_F_vs_cat34=float((F == c34).mean()),
    kappa_Fstrict_vs_cat4=float(kappa(Fs, fi)), agree_Fstrict_vs_cat4=float((Fs == fi).mean()),
    kappa_F_vs_cat4=float(kappa(F, fi)), agree_F_vs_cat4=float((F == fi).mean()),
    kappa_4way=float(kappa(np.where(h.hand == "R", 1, np.where(h.hand == "P", 2, np.where(h.disclaimer == 1, 3, 4))), h.cat)))

# released counts per (tier, cat) among PM compliers
def counts(vs):
    x = D[D.variant.isin(vs) & D.pm_score.notna() & D.c_pm].copy()
    x["cat"] = np.where(x.refuses, 1, np.where(x.compr, 2, np.where(x.ui, 3, 4)))
    return {(t, c): int(((x.tier == t) & (x.cat == c)).sum()) for t in ("train", "deploy") for c in (1, 2, 3, 4)}


def npairs(vs):
    return sum(len(paired(v, "c_pm")[2]) for v in vs)


rng = np.random.default_rng(12345)
NDRAW = 4000
post = {}
for which, mask in (("F", F), ("F_strict", Fs)):
    post[which] = {}
    for t in ("train", "deploy"):
        for c in (1, 2, 3, 4):
            g = (h.tier == t) & (h.cat == c)
            k, n = int((mask & g).sum()), int(g.sum())
            post[which][(t, c)] = rng.beta(1 + k, 1 + n - k, NDRAW)
res = {}
for nm, vs in (("default", ["atn_honly"]), ("pooled44", OPUS)):
    cn, N = counts(vs), npairs(vs)
    pm_gap = (sum(cn[("train", c)] for c in range(1, 5)) - sum(cn[("deploy", c)] for c in range(1, 5))) / N
    r = {"pairs": N, "pm_gap": 100 * pm_gap, "counts": {f"{t}|cat{c}": v for (t, c), v in cn.items()}}
    for which in ("F", "F_strict"):
        free = sum(cn[("train", c)] * post[which][("train", c)] for c in range(1, 5))
        paid = sum(cn[("deploy", c)] * post[which][("deploy", c)] for c in range(1, 5))
        gap = (free - paid) / N
        npaid = sum(cn[("deploy", c)] for c in range(1, 5))
        r[which] = dict(gap=float(100 * np.median(gap)), gap_ci=list(100 * np.percentile(gap, [2.5, 97.5])),
                        ratio=float(np.median(gap / pm_gap)), ratio_ci=list(np.percentile(gap / pm_gap, [2.5, 97.5])),
                        paid_not_full_share=float(np.median(1 - paid / npaid)),
                        paid_not_full_share_ci=list(np.percentile(1 - paid / npaid, [2.5, 97.5])))
    res[nm] = r
out["calibrated"] = res
json.dump(out, open(os.path.join(HERE, "handlabels_validator.json"), "w"), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
