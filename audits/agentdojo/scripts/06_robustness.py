"""Robustness checks (prereg.md) and content-blind predictors of attack success.

Run: data/.venv/bin/python -I scripts/06_robustness.py
Writes the 'robustness' and 'content_blind' blocks of results.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from common import MODELS, RESULTS, load

rng = np.random.default_rng(0)
att = load()
att = att[att.pipeline.isin(MODELS)].copy()
none = load("none")
none = none[none.pipeline.isin(MODELS)]
U = none.groupby("pipeline").utility.mean()
FAMILY = {m: ("OpenAI" if m.startswith("gpt") else "Anthropic" if m.startswith("claude") else
              "Google" if m.startswith("gemini") else "Cohere" if m.startswith("command") else "Meta") for m in MODELS}
att["follow"] = att.follow_exec.astype(bool)


def per_model(df, cond=None):
    s0 = df.groupby("pipeline").security.mean()
    s1 = df[df.exposed].groupby("pipeline").security.mean()
    s3 = df[df.exposed].groupby("pipeline").follow.mean()
    return pd.DataFrame(dict(S0=s0, S1=s1, S3=s3, U=U)).loc[MODELS]


def summary(pm, models=MODELS):
    pm = pm.loc[models]
    return dict(trend_S0=round(float(spearmanr(pm.U, pm.S0).statistic), 3),
                trend_S1=round(float(spearmanr(pm.U, pm.S1).statistic), 3),
                trend_S3=round(float(spearmanr(pm.U, pm.S3).statistic), 3),
                rank_S0_S1=round(float(spearmanr(pm.S0, pm.S1).statistic), 3),
                rank_S0_S3=round(float(spearmanr(pm.S0, pm.S3).statistic), 3))


rob = {}
full = per_model(att)
rob["full"] = summary(full)
# model-level permutation p for the published trend (models are the sampled unit of the trend)
obs = spearmanr(full.U, full.S0).statistic
perm = np.array([spearmanr(rng.permutation(full.U.values), full.S0.values).statistic for _ in range(10000)])
rob["trend_S0_model_permutation_p_two_sided"] = float((np.abs(perm) >= abs(obs)).mean())
obs1 = spearmanr(full.U, full.S1).statistic
perm1 = np.array([spearmanr(rng.permutation(full.U.values), full.S1.values).statistic for _ in range(10000)])
rob["trend_S1_model_permutation_p_two_sided"] = float((np.abs(perm1) >= abs(obs1)).mean())
# 1. drop each suite
rob["drop_suite"] = {s: summary(per_model(att[att.suite != s])) for s in sorted(att.suite.unique())}
# 2. drop each family (trend)
rob["drop_family"] = {f: summary(full, [m for m in MODELS if FAMILY[m] != f]) for f in sorted(set(FAMILY.values()))}
# 3. common support: pairwise S1 on cases exposed for both models; count reversals of S0 order
key = att.ut + "|" + att.it
att["key"] = key
piv_e = att.pivot(index="key", columns="pipeline", values="exposed")
piv_s = att.pivot(index="key", columns="pipeline", values="security")
rev, tot = 0, 0
for i, a in enumerate(MODELS):
    for b in MODELS[i + 1:]:
        both = piv_e[a] & piv_e[b]
        da = piv_s.loc[both, a].mean() - piv_s.loc[both, b].mean()
        d0 = full.S0[a] - full.S0[b]
        tot += 1
        if np.sign(da) == -np.sign(d0) and d0 != 0:
            rev += 1
rob["common_support_pairs_point_reversed"] = dict(n_pairs=tot, n_reversed=rev)
# 4. placebo exposure: random flag with the model's own exposure rate within suite
pl = []
for r in range(200):
    d = att.copy()
    d["exposed"] = False
    for (p, s), g in att.groupby(["pipeline", "suite"]):
        k = int(g.exposed.sum())
        idx = rng.choice(g.index.values, k, replace=False)
        d.loc[idx, "exposed"] = True
    pl.append(summary(per_model(d)))
pl = pd.DataFrame(pl)
rob["placebo_exposure_200_draws_mean"] = pl.mean().round(3).to_dict()
# 5. Pearson on logit rates
lg = lambda x: np.log((x + 0.005) / (1 - x + 0.005))
rob["pearson_logit"] = dict(trend_S0=round(float(pearsonr(full.U, lg(full.S0)).statistic), 3),
                            trend_S1=round(float(pearsonr(full.U, lg(full.S1)).statistic), 3),
                            trend_S3=round(float(pearsonr(full.U, lg(full.S3)).statistic), 3))
# 6. multiple comparisons: Holm over the 190 x 3 pair tests from 04_effect
pairs = pd.read_csv(os.path.join(os.path.dirname(RESULTS), "results", "pairs.csv"))
holm = {}
for s in ["S0", "S1", "S3"]:
    p = np.sort(np.maximum(pairs[f"{s}_p"].values, 1 / 2000))
    m = len(p)
    adj = np.maximum.accumulate(np.minimum(1, p * (m - np.arange(m))))
    holm[s] = int((adj < 0.05).sum())
rob["holm_separated_pairs"] = holm
rob["n_tests_reported"] = dict(pair_tests=190 * 4, trend_tests=6, defence_decompositions=4,
                               note="C1 uses 190 pairs x S0,S1,S2,S3; C2 six correlations; C3 four defences")
# exposure share of the per-model ASR gap between top and bottom utility halves
hi = full.U >= full.U.median()
gap0 = full.S0[hi].mean() - full.S0[~hi].mean()
gap1 = full.S1[hi].mean() - full.S1[~hi].mean()
rob["high_vs_low_utility_half_gap"] = dict(S0=round(float(gap0), 4), S1=round(float(gap1), 4),
                                           S3=round(float(full.S3[hi].mean() - full.S3[~hi].mean()), 4))

# ---- content-blind predictors of per-case security (pooled over the 20 models)
need = none[none.utility].groupby("ut").n_tool_calls_exec.median()
d = att.copy()
d["need_calls"] = d.ut.map(need).fillna(d.ut.map(none.groupby("ut").n_tool_calls_exec.median()))
d["out_len"] = d.injected_output_len.fillna(0)
d["rel_pos"] = d.injection_rel_pos.fillna(-1)
d["n_vectors"] = d.n_vectors
feats_sets = {
    "suite": ["suite"],
    "injection_task_id": ["it"],
    "suite+structure": ["suite", "need_calls", "n_vectors"],
    "suite+structure+injection_output": ["suite", "need_calls", "n_vectors", "out_len", "rel_pos"],
    "all_plus_injection_task_id": ["it", "need_calls", "n_vectors", "out_len", "rel_pos"],
}
y = d.security.values.astype(int)
groups = d.ut.values
cb = {}


def design(cols, frame):
    X = pd.get_dummies(frame[cols], columns=[c for c in cols if not pd.api.types.is_numeric_dtype(frame[c])], dtype=float)
    return X.values


def cv_auc(X, yv):
    pred = np.zeros(len(yv))
    for tr, te in GroupKFold(5).split(X, yv, groups):
        m = HistGradientBoostingClassifier(random_state=0, max_iter=100, max_depth=3).fit(X[tr], yv[tr])
        pred[te] = m.predict_proba(X[te])[:, 1]
    return roc_auc_score(yv, pred)


for name, cols in feats_sets.items():
    X = design(cols, d)
    auc = cv_auc(X, y)
    # permutation null: shuffle labels within suite (100 shuffles; GBM refits are slow)
    null = []
    for _ in range(100):
        yp = y.copy()
        for s in d.suite.unique():
            ix = np.where(d.suite.values == s)[0]
            yp[ix] = rng.permutation(yp[ix])
        null.append(cv_auc(X, yp))
    cb[name] = dict(auc=round(float(auc), 3), null_mean=round(float(np.mean(null)), 3),
                    null_95=round(float(np.percentile(null, 95)), 3))
# model identity alone, and model + injection task (how much is item identity vs model)
d["pipe"] = d.pipeline
for name, cols in {"model_only": ["pipe"], "model+injection_task": ["pipe", "it"],
                   "model+injection_task+exposed": ["pipe", "it", "exposed"]}.items():
    X = design(cols, d.assign(exposed=d.exposed.astype(float)))
    cb[name] = dict(auc=round(float(cv_auc(X, y)), 3))
cb["note"] = "GroupKFold(5) by user task; HistGBM; null = 100 within-suite label shuffles (fewer than the 1,000 in the methodology because each null refits 5 models)"

res = json.load(open(RESULTS))
res["robustness"] = rob
res["content_blind"] = cb
json.dump(res, open(RESULTS, "w"), indent=1)
print(json.dumps(rob, indent=1))
print(json.dumps(cb, indent=1))
