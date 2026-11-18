"""V2: can the construction (detour vs parallel) be inferred from what the evaluated model sees?

Logistic regression (L2, scipy L-BFGS) on binary word presence in query + both options, fitted
within domain, 5-fold cross-validation grouped by task. Then the floor rule with the inferred cell.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import CELLS, SEED, average, features, load, save, toks  # noqa: E402

rows = load()
F = features(rows)
rng = np.random.default_rng(SEED)


def fit(X, y, lam=1.0):
    n, p = X.shape

    def obj(w):
        z = X @ w[:-1] + w[-1]
        ll = np.logaddexp(0, z) - y * z
        return ll.sum() + lam * (w[:-1] ** 2).sum() / 2

    def grad(w):
        z = X @ w[:-1] + w[-1]
        r = 1 / (1 + np.exp(-z)) - y
        return np.concatenate([X.T @ r + lam * w[:-1], [r.sum()]])

    w = minimize(obj, np.zeros(p + 1), jac=grad, method="L-BFGS-B", options={"maxiter": 500}).x
    return w


def auc(score, y):
    order = np.argsort(score)
    ranks = np.empty(len(score))
    ranks[order] = np.arange(1, len(score) + 1)
    n1 = y.sum()
    n0 = len(y) - n1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def group_folds(groups, k=5):
    g = np.unique(groups)
    rng.shuffle(g)
    fold_of = {t: i % k for i, t in enumerate(g)}
    return np.array([fold_of[t] for t in groups])


out = {}
pred_detour = {}
for dom in ("engineering", "research"):
    idx = [i for i, r in enumerate(rows) if r["domain"] == dom]
    docs = [set(toks(rows[i]["query"] + " " + " ".join(rows[i]["choices"]), 3)) for i in idx]
    df = {}
    for d in docs:
        for w in d:
            df[w] = df.get(w, 0) + 1
    vocab = sorted(w for w, c in df.items() if c >= 5)
    col = {w: j for j, w in enumerate(vocab)}
    X = np.zeros((len(idx), len(vocab)))
    for a, d in enumerate(docs):
        for w in d:
            if w in col:
                X[a, col[w]] = 1
    y = np.array([1 if rows[i]["cell"].startswith("detour") else 0 for i in idx])
    groups = np.array([rows[i]["task_id"] for i in idx])
    steps = np.array([rows[i]["prefix_steps"] for i in idx], float)
    res = {"n": len(idx), "n_detour": int(y.sum()), "vocab": len(vocab),
           "tasks_with_both_constructions": int(sum(len({y[a] for a in np.where(groups == t)[0]}) > 1
                                                   for t in np.unique(groups)))}
    for lam in (1.0, 10.0):
        oof = np.zeros(len(idx))
        oof_steps = np.zeros(len(idx))
        folds = group_folds(groups)
        for k in range(5):
            tr, te = folds != k, folds == k
            w = fit(X[tr], y[tr], lam)
            oof[te] = X[te] @ w[:-1] + w[-1]
            # crude: prefix steps threshold, direction and cut chosen on training folds
            best = (0, 0, 1)
            for c in np.unique(steps[tr]):
                for s in (1, -1):
                    a = ((s * (steps[tr] - c) > 0).astype(int) == y[tr]).mean()
                    if a > best[0]:
                        best = (a, c, s)
            oof_steps[te] = best[2] * (steps[te] - best[1])
        acc = float(((oof > 0).astype(int) == y).mean())
        res[f"lam{lam:g}"] = {"oof_accuracy": round(acc, 4), "oof_auc": round(auc(oof, y), 4),
                              "majority_baseline": round(max(y.mean(), 1 - y.mean()), 4)}
        if lam == 1.0:
            res["steps_only_oof_accuracy"] = round(float(((oof_steps > 0).astype(int) == y).mean()), 4)
            for a, i in enumerate(idx):
                pred_detour[i] = oof[a] > 0
    out[dom] = res

# floor rule with inferred cell, own cont feature
for name in ("cont", "ground"):
    accs, ns = {}, {}
    accs_true = {}
    for c in CELLS:
        ii = [i for i, f in enumerate(F) if f["cell"] == c]
        cor, cor_t = [], []
        for i in ii:
            f = F[i]
            d = f[name][1] - f[name][0]
            yy = 1 if f["ans"] == 1 else -1
            s_inf = -1 if pred_detour[i] else 1
            s_true = -1 if c.startswith("detour") else 1
            cor.append(d * yy * s_inf > 0)
            cor_t.append(d * yy * s_true > 0)
        accs[c], accs_true[c], ns[c] = float(np.mean(cor)), float(np.mean(cor_t)), len(ii)
    avg_inf, dom_inf = average(accs, ns)
    avg_true, _ = average(accs_true, ns)
    out[f"floor_{name}"] = {"average_inferred_cell": round(avg_inf * 100, 1),
                            "average_true_cell": round(avg_true * 100, 1),
                            "cells_inferred": {c: round(v * 100, 1) for c, v in accs.items()}}
# cell-blind version: one sign for everything per domain (the best one in hindsight)
for name in ("cont",):
    best = {}
    for dom in ("engineering", "research"):
        ii = [i for i, f in enumerate(F) if f["domain"] == dom]
        for s in (1, -1):
            a = np.mean([(F[i][name][1] - F[i][name][0]) * (1 if F[i]["ans"] == 1 else -1) * s > 0 for i in ii])
            best[(dom, s)] = round(float(a) * 100, 1)
    out["cell_blind_cont_accuracy_by_domain_and_sign"] = {f"{d}_{'higher' if s == 1 else 'lower'}": v
                                                          for (d, s), v in best.items()}
save("v2_cell_inference.json", out)
print(__import__("json").dumps(out, indent=1))
