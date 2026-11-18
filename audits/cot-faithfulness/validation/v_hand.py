"""H1 analysis of the validator's blind labels (run after labelling was committed)."""
import os, sys, csv, json
import numpy as np
from collections import Counter, defaultdict
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
key = {r["item"]: r for r in csv.DictReader(open(os.path.join(HERE, "hand_key.csv")))}
lab = {r["item"]: r["label"] for r in csv.DictReader(open(os.path.join(HERE, "hand_labels.csv")))}
items = [dict(key[i], label=lab[i]) for i in key]
ext = json.load(open(os.path.join(ROOT, "data/val_extract.json")))
POP = {m: sum(v["n_wrong"] for v in ext[m].values()) for m in ext}
NOTJ = {"FLIP", "GUESS", "RULE"}
out = {}

def wilson(k, n, z=1.96):
    if n == 0: return [None, None]
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]

by = defaultdict(list)
for it in items: by[it["model"]].append(it)
out["per_model"] = {m: dict(n=len(v), **Counter(x["label"] for x in v)) for m, v in sorted(by.items())}
s37 = by["son37"]; k = sum(x["label"] == "FLIP" for x in s37)
out["son37_flip"] = dict(k=k, n=len(s37), share=k / len(s37), wilson=wilson(k, len(s37)))
sd = by["son37_dropped"]; kd = sum(x["label"] == "FLIP" for x in sd)
out["son37_dropped_flip"] = dict(k=kd, n=len(sd), share=kd / len(sd), wilson=wilson(kd, len(sd)))
kk = k + kd; out["son37_all90_flip"] = dict(k=kk, n=len(s37) + len(sd), wilson=wilson(kk, len(s37) + len(sd)))

# agreement with the authors' autorater on FLIP vs not (items with an autorater label)
a = [(x["label"] == "FLIP", x["auto_flip"] == "YES") for x in items if x["auto_flip"] in ("YES", "NO")]
tp = sum(m and r for m, r in a); fp = sum((not m) and r for m, r in a); fn = sum(m and not r for m, r in a); tn = sum((not m) and (not r) for m, r in a)
n = len(a); po = (tp + tn) / n; pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / n ** 2
out["vs_autorater"] = dict(n=n, both_flip=tp, auto_only=fp, me_only=fn, neither=tn,
                           auto_precision=tp / (tp + fp), auto_recall=tp / (tp + fn), kappa=(po - pe) / (1 - pe))
s37a = [(x["label"], x["auto_flip"]) for x in s37]
out["son37_vs_autorater"] = Counter(f"{l}|auto={r}" for l, r in s37a)

# pooled shares reweighted to the flagged-pair population of wrong answers (main sample only)
main = [x for x in items if x["model"] != "son37_dropped"]
models = sorted({x["model"] for x in main})
rng = np.random.default_rng(11)
def pooled(sample_by_model, cats):
    num = den = 0.0
    for m in models:
        v = sample_by_model[m]
        if not v: continue
        num += POP[m] * np.mean([x in cats for x in v]); den += POP[m]
    return num / den
labs = {m: [x["label"] for x in main if x["model"] == m] for m in models}
res = {}
for name, cats in {"not_justification(FLIP+GUESS+RULE)": NOTJ, "FLIP": {"FLIP"}, "GUESS": {"GUESS"},
                   "RULE": {"RULE"}, "FACT": {"FACT"}, "LOGIC": {"LOGIC"}}.items():
    pt = pooled(labs, cats)
    bs = [pooled({m: list(rng.choice(labs[m], len(labs[m]))) for m in models}, cats) for _ in range(2000)]
    res[name] = dict(est=pt, ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
out["pooled_reweighted"] = res
# unweighted (model-balanced) shares too
out["unweighted_main"] = dict(Counter(x["label"] for x in main), n=len(main))

# 3.7 Sonnet flip share with label disagreement propagated (mine vs autorater, 1/2 each where they differ)
mine = np.array([x["label"] == "FLIP" for x in s37]); auto = np.array([x["auto_flip"] == "YES" for x in s37])
bs = []
for _ in range(5000):
    idx = rng.integers(0, len(s37), len(s37))
    pick = rng.random(len(s37)) < .5
    bs.append(np.mean(np.where(pick, mine[idx], auto[idx])))
out["son37_flip_label_uncertainty"] = dict(mine=float(mine.mean()), auto=float(auto.mean()),
                                           ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
# authors' own lack_of_information label (stated guess) share among wrong answers, by model
lack = {}
for m in ext:
    L = [r.get("lack") for v in ext[m].values() for r in v["wrong"].values() if r.get("lack") in ("YES", "NO")]
    F = [r.get("flip") for v in ext[m].values() for r in v["wrong"].values() if r.get("flip") in ("YES", "NO")]
    lack[m] = dict(n=len(L), lack_yes=sum(x == "YES" for x in L), flip_yes=sum(x == "YES" for x in F), n_flip=len(F))
out["autorater_lack_of_information"] = lack
tot = {k: sum(v[k] for v in lack.values()) for k in ["n", "lack_yes"]}
out["autorater_lack_pooled"] = tot
json.dump(out, open(os.path.join(HERE, "v_hand.json"), "w"), indent=1, default=str)
for k, v in out.items():
    if k != "autorater_lack_of_information": print(k, v)

# weighting sensitivity: by autorater-labelled wrong answers (the auditor's 15,461) and by flagged pairs
LABN = {m: sum(1 for v in ext[m].values() for r in v["wrong"].values() if r.get("flip") in ("YES", "NO")) for m in ext}
PAIRS = {m: len(ext[m]) for m in ext}
sens = {}
for wname, Wt in {"all_wrong_answers": POP, "autorater_labelled_wrong_answers": LABN, "flagged_pairs": PAIRS}.items():
    def pooledw(sbm, cats):
        num = sum(Wt[m] * np.mean([x in cats for x in sbm[m]]) for m in models)
        return num / sum(Wt[m] for m in models)
    r = {}
    for name, cats in {"not_justification": NOTJ, "FLIP": {"FLIP"}, "GUESS": {"GUESS"}, "RULE": {"RULE"}, "FACT": {"FACT"}}.items():
        bs = [pooledw({m: list(rng.choice(labs[m], len(labs[m]))) for m in models}, cats) for _ in range(2000)]
        r[name] = [round(pooledw(labs, cats), 3), round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]
    sens[wname] = r
out["weighting_sensitivity"] = sens
# label-disagreement propagation for the pooled not-justification share: in each replicate, flip each
# item's not-justification membership with the observed validator-vs-auditor disagreement rate (4/30)
dis = 4 / 30
bs = []
for _ in range(2000):
    s = {}
    for m in models:
        v = list(rng.choice(labs[m], len(labs[m])))
        s[m] = [("FLIP" if (x not in NOTJ) else "FACT") if rng.random() < dis else x for x in v]
    num = sum(LABN[m] * np.mean([x in NOTJ for x in s[m]]) for m in models)
    bs.append(num / sum(LABN[m] for m in models))
out["not_justification_with_label_noise_labelledweights"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
json.dump(out, open(os.path.join(HERE, "v_hand.json"), "w"), indent=1, default=str)
print(sens); print(out["not_justification_with_label_noise_labelledweights"])
