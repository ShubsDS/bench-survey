"""Prereg A1: content-blind answer-surface rules on ProtocolQA (and CloningScenarios) options.

Each feature f gives two rules: pick argmax f, pick argmin f (ties split evenly). Selection on a
random half of the protocol clusters, scored on the other half, 1,000 halves. A conditional-logit
over all features (standardised within item) fitted on the training half is scored the same way.
Null: the same procedure after shuffling the key position within items (1,000 shuffles, each with
a fresh split). Also scored on the paraphrased options (for R1's "cue preserved" check).
Writes results/cues.json and results/cues_items.csv (per-item rule pick correctness; ids only).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import DATA, RESULTS, key_hash, load  # noqa: E402

HEDGE = re.compile(r"\b(may|might|could|possibly|likely|perhaps|should)\b", re.I)
UNIT = re.compile(r"(µl|μl|ul\b|ml\b|\bl\b|min|minutes?|hours?|hrs?\b|\bh\b|°c|\bc\b|x ?g\b|\bg\b|rpm|\bm\b|mm\b|%|µm|um\b|nm\b|ng|µg|μg|mg)", re.I)
STEP = re.compile(r"\bsteps?\s*[a-z]?\d+", re.I)
NUMR = re.compile(r"\d+(?:\.\d+)?")
WORD = re.compile(r"[a-z]+", re.I)
STOP = set("the a an of in to for and or at by with on is be use step steps from into as instead not do than".split())

FEATS = ["len", "words", "numerals", "steps", "hedge", "units", "unique_words", "centroid"]


def grams(s):
    s = re.sub(r"\s+", " ", s.lower())
    return {s[i:i + 3] for i in range(len(s) - 2)}


def feats(options):
    w = [set(x.lower() for x in WORD.findall(o)) - STOP for o in options]
    g = [grams(o) for o in options]
    rows = []
    for i, o in enumerate(options):
        others = set().union(*[w[j] for j in range(len(options)) if j != i]) if len(options) > 1 else set()
        cen = np.mean([len(g[i] & g[j]) / max(1, len(g[i] | g[j])) for j in range(len(options)) if j != i])
        rows.append([len(o), len(o.split()), len(NUMR.findall(o)), len(STEP.findall(o)),
                     len(HEDGE.findall(o)), len(UNIT.findall(o)), len(w[i] - others), cen])
    return np.array(rows, float)


def rule_score(F, key, f, sign):
    v = sign * F[:, f]
    best = np.flatnonzero(v == v.max())
    return (key in best) / len(best)


def build(df, para=None):
    X, K, C, ids = [], [], [], []
    for _, r in df.iterrows():
        opts = [r.ideal] + list(r.distractors) if para is None else para[r.id]["options"]
        X.append(feats([o.strip() for o in opts]))
        K.append(0)
        C.append(r.cluster)
        ids.append(r.id)
    return X, np.array(K), np.array(C), ids


def rule_matrix(X, K):
    # item x rule accuracy (rules: feature f, sign +/-)
    out = np.zeros((len(X), 2 * len(FEATS)))
    for i, F in enumerate(X):
        for f in range(len(FEATS)):
            out[i, 2 * f] = rule_score(F, K[i], f, 1)
            out[i, 2 * f + 1] = rule_score(F, K[i], f, -1)
    return out


def clogit_fit(X, K, idx, l2=1.0, iters=300, lr=0.1):
    w = np.zeros(len(FEATS))
    Z = [((X[i] - X[i].mean(0)) / (X[i].std(0) + 1e-9)) for i in range(len(X))]
    for _ in range(iters):
        g = -l2 * w
        for i in idx:
            s = Z[i] @ w
            p = np.exp(s - s.max()); p /= p.sum()
            g += Z[i][K[i]] - p @ Z[i]
        w += lr * g / max(1, len(idx))
    return w, Z


def clogit_acc(Z, K, w, idx):
    acc = []
    for i in idx:
        s = Z[i] @ w
        best = np.flatnonzero(np.isclose(s, s.max()))
        acc.append((K[i] in best) / len(best))
    return float(np.mean(acc))


def split_eval(X, K, C, rng, n_splits, do_logit=True):
    R = rule_matrix(X, K)
    uc = np.unique(C)
    rule_held, logit_held, chosen = [], [], []
    for _ in range(n_splits):
        tr_c = rng.choice(uc, len(uc) // 2, replace=False)
        tr = np.isin(C, tr_c)
        best = int(np.argmax(R[tr].mean(0)))
        chosen.append(best)
        rule_held.append(R[~tr, best].mean())
        if do_logit:
            w, Z = clogit_fit(X, K, np.flatnonzero(tr), iters=60, lr=0.3)
            logit_held.append(clogit_acc(Z, K, w, np.flatnonzero(~tr)))
    return R, np.array(rule_held), np.array(logit_held), chosen


def shuffle_keys(X, rng):
    Xs, Ks = [], []
    for F in X:
        Ks.append(int(rng.integers(len(F))))
        Xs.append(F)
    return Xs, np.array(Ks)


def main():
    rng = np.random.default_rng(0)
    items = load()
    res = {}
    per_item = []
    para_path = DATA / "paraphrases.json"
    para = json.loads(para_path.read_text()) if para_path.exists() else None
    for sub in ["ProtocolQA", "CloningScenarios"]:
        df = items[items.subset == sub]
        X, K, C, ids = build(df)
        chance = float(np.mean([1 / len(F) for F in X]))
        R, rh, lh, chosen = split_eval(X, K, C, rng, 1000 if sub == "ProtocolQA" else 300)
        null_r, null_l = [], []
        for _ in range(300):
            Xs, Ks = shuffle_keys(X, rng)
            _, a, b, _ = split_eval(Xs, Ks, C, rng, 3)
            null_r.append(a.mean()); null_l.append(b.mean())
        full_best = int(np.argmax(R.mean(0)))
        names = [f"{'max' if j % 2 == 0 else 'min'}_{FEATS[j // 2]}" for j in range(R.shape[1])]
        out = {"n": len(X), "clusters": int(len(np.unique(C))), "chance": chance,
               "rule_in_sample": {names[j]: float(R[:, j].mean()) for j in range(R.shape[1])},
               "rule_heldout_mean": float(rh.mean()), "rule_heldout_p2.5_97.5": np.percentile(rh, [2.5, 97.5]).tolist(),
               "logit_heldout_mean": float(lh.mean()),
               "null_rule_heldout_mean": float(np.mean(null_r)),
               "p_rule": float((np.sum(np.array(null_r) >= rh.mean()) + 1) / (len(null_r) + 1)),
               "p_logit": float((np.sum(np.array(null_l) >= lh.mean()) + 1) / (len(null_l) + 1)),
               "chosen_rules_freq": {names[k]: chosen.count(k) for k in set(chosen)},
               "best_rule_all_items": names[full_best], "best_rule_all_items_acc": float(R[:, full_best].mean()),
               "null_shuffles": 300}
        if sub == "ProtocolQA" and para:
            keep = [i for i, x in enumerate(ids) if x in para]
            Xp, Kp, Cp, idp = build(df.loc[[ids[i] for i in keep]], para)
            Rp = rule_matrix(Xp, Kp)
            Ro = R[keep]
            out["paraphrase"] = {"n": len(keep),
                                 "orig_rules": {names[j]: float(Ro[:, j].mean()) for j in range(R.shape[1])},
                                 "para_rules": {names[j]: float(Rp[:, j].mean()) for j in range(R.shape[1])},
                                 "max_abs_rule_change": float(np.max(np.abs(Rp.mean(0) - Ro.mean(0)))),
                                 "best_rule_orig": float(Ro[:, full_best].mean()), "best_rule_para": float(Rp[:, full_best].mean())}
        res[sub] = out
        for i, x in enumerate(ids):
            per_item.append({"id": x, "subset": sub, "cluster": key_hash(C[i]), "best_rule": names[full_best],
                             "best_rule_correct": R[i, full_best], "max_len_correct": R[i, 0]})
    (RESULTS / "cues.json").write_text(json.dumps(res, indent=1))
    pd.DataFrame(per_item).to_csv(RESULTS / "cues_items.csv", index=False)
    print(json.dumps({s: {k: v for k, v in d.items() if k not in ("rule_in_sample", "paraphrase")} for s, d in res.items()}, indent=1))
    if "paraphrase" in res["ProtocolQA"]:
        print("paraphrase", {k: v for k, v in res["ProtocolQA"]["paraphrase"].items() if "rules" not in k})


if __name__ == "__main__":
    main()
