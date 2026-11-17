"""Step 6 and 8: the pre-registered effect test (prereg.md) on SAD's released per-item results.

Strata from results/features.csv (S = shortcut right, R = shortcut wrong, ties excluded). Item
credit from data/outcomes.parquet (scripts/load_outputs.py). Cluster bootstrap over near-duplicate
groups (2,000 replicates, seed 0); FHD's twice-scored items share a group and move together.

Writes results/effect.json. Usage: python -I scripts/effect.py --cache data
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from common import CHANCE
from overall import ARENA, BASE, BASE_CHAT_PAIRS, MMLU, mname, released_task_scores, sad_score

TASKS = ["facts_human_defaults", "influence", "stages_full", "stages_oversight"]
PLACEBO_TASK = "facts_llms"
B = 2000
QUESTIONABLE = ["178d73", "861272", "43085a", "e7b589", "8a263c", "5c8f46", "545238", "8d1348", "304f1a"]
FAMILY = lambda m: "llama" if m.startswith("llama") else "anthropic" if m.startswith("claude") else "openai"


def ci(a, lo=2.5, hi=97.5):
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    return [round(float(np.percentile(a, lo)), 3), round(float(np.percentile(a, hi)), 3)] if len(a) else None


def r3(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 3)


class Task:
    """Item x run matrix for one task, with strata and bootstrap weights."""

    def __init__(self, name, feats, outs, rng):
        f = feats[feats.task == name].copy()
        f["occ"] = f.groupby("key").cumcount()
        o = outs[outs.task == name].copy()
        o["occ"] = o.groupby(["model", "variant", "key"]).cumcount()
        o["run"] = o.model + "|" + o.variant
        piv = o.pivot_table(index=["key", "occ"], columns="run", values="credit", aggfunc="first")
        cor = o.pivot_table(index=["key", "occ"], columns="run", values="correct", aggfunc="first")
        f = f.set_index(["key", "occ"])
        missing = len(f.index.difference(piv.index))
        assert missing == 0, (name, missing)
        # runs on items absent from the current pile (an older item version) are left as NaN
        self.unmatched_items = {r: int(n) for r, n in piv.loc[f.index].isna().sum().items() if n}
        self.name, self.f = name, f.reset_index()
        self.X = piv.loc[f.index].to_numpy()          # credit, items x runs
        self.C = cor.loc[f.index].to_numpy()          # binary correct
        self.runs = list(piv.columns)
        g = pd.factorize(self.f.group)[0]
        self.g, self.ng = g, g.max() + 1
        counts = rng.multinomial(self.ng, np.full(self.ng, 1 / self.ng), size=B)  # B x clusters
        self.W = counts[:, g].astype(float)          # B x items
        self.chance = CHANCE[name]

    def col(self, model, variant="plain"):
        return self.runs.index(f"{model}|{variant}")

    def mask(self, stratum, which="shortcut_right", extra=None):
        v = self.f[which].to_numpy()
        m = np.ones(len(v), bool) if stratum == "full" else (v == (1 if stratum == "S" else 0))
        if extra is not None:
            m &= extra
        return m

    def score(self, mask, models, variant="plain", boot=False):
        cols = [self.col(m, variant) for m in models]
        X = self.X[:, cols][mask]
        M = ~np.isnan(X)  # one run (gpt-3.5-turbo-0613, stages_oversight, plain) used 128 older items
        X = np.where(M, X, 0.0)
        if not boot:
            return X.sum(0) / M.sum(0)
        W = self.W[:, mask]
        return (W @ X) / (W @ M)  # B x models


def spearman(a, b):
    return spearmanr(a, b).statistic


def pear(a, b):
    return pearsonr(a, b).statistic


def corr_rows(Ma, v):
    """Pearson r between each row of Ma (B x k) and vector v."""
    a = Ma - Ma.mean(1, keepdims=True)
    b = v - v.mean()
    return (a @ b) / np.sqrt((a * a).sum(1) * (b @ b))


def spearman_rows(Ma, Mb):
    ra = np.argsort(np.argsort(Ma, 1), 1).astype(float)
    rb = np.argsort(np.argsort(Mb, 1), 1).astype(float)
    return np.array([np.corrcoef(x, y)[0, 1] for x, y in zip(ra, rb)])


def logit_fit(X, y, w, iters=25):
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ beta)))
        H = (X * (w * p * (1 - p))[:, None]).T @ X + 1e-8 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (w * (y - p)))
        beta += step
        if np.abs(step).max() < 1e-8:
            break
    return beta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="results/effect.json")
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    feats = pd.read_csv("results/features.csv")
    outs = pd.read_parquet(Path(a.cache) / "outcomes.parquet")
    outs["model"] = outs.model.map(mname)
    rel = released_task_scores(Path(a.cache) / "repo")
    models = sorted({m for (m, v) in rel if v == "plain"})
    assert len(models) == 21, models
    mm = [m for m in models if m in MMLU]
    mmlu = np.array([MMLU[m] for m in mm])
    other = {m: sad_score(rel[(m, "plain")], exclude=TASKS) for m in models}
    top10 = sorted(models, key=lambda m: -other[m])[:10]
    chat = [m for m in models if m not in BASE]
    T = {t: Task(t, feats, outs, rng) for t in TASKS + [PLACEBO_TASK]}
    res = {"models": models, "mmlu_models": mm, "top10_by_sad_other_tasks": top10,
           "bootstrap_replicates": B, "tasks": {}}

    # ---------- per task, per stratum scores ----------
    for t, X in T.items():
        d = {"n_items": {s: int(X.mask(s).sum()) for s in ("full", "S", "R")}, "runs_with_unmatched_items": X.unmatched_items,
             "n_clusters": int(X.ng)}
        sc = {}
        for s in ("full", "S", "R"):
            pt = X.score(X.mask(s), models)
            bt = X.score(X.mask(s), models, boot=True)
            sc[s] = {m: {"score": r3(pt[i]), "ci95": ci(bt[:, i])} for i, m in enumerate(models)}
        d["plain_scores"] = sc
        if t in rel[(models[0], "plain")]:
            d["released_csv_plain"] = {m: r3(rel[(m, "plain")].get(t)) for m in models}
        # C1: rank agreement between strata, with a cluster-level random-split placebo
        S_, R_ = X.score(X.mask("S"), models), X.score(X.mask("R"), models)
        rho = spearman(S_, R_)
        nonTie = X.mask("S") | X.mask("R")
        groups = np.unique(X.g[nonTie])
        nR = int(X.mask("R").sum())
        pl = []
        for _ in range(1000):
            perm = rng.permutation(groups)
            sizes = np.bincount(X.g[nonTie], minlength=X.ng)[perm]
            cut = np.searchsorted(np.cumsum(sizes), nR) + 1
            Rg = np.zeros(X.ng, bool)
            Rg[perm[:cut]] = True
            mR = nonTie & Rg[X.g]
            mS = nonTie & ~Rg[X.g]
            pl.append(spearman(X.score(mS, models), X.score(mR, models)))
        rho_boot = spearman_rows(X.score(X.mask("S"), models, boot=True), X.score(X.mask("R"), models, boot=True))
        d["C1_rank"] = {"spearman_S_vs_R": r3(rho), "ci95": ci(rho_boot),
                        "placebo_random_split_median": r3(np.median(pl)), "placebo_2.5pct": r3(np.percentile(pl, 2.5)),
                        "placebo_97.5pct": r3(np.percentile(pl, 97.5)),
                        "placebo_p_le_observed": r3((1 + np.sum(np.array(pl) <= rho)) / 1001),
                        "spearman_full_vs_R": r3(spearman(X.score(X.mask("full"), models), R_))}
        bootR = X.score(X.mask("R"), models, boot=True)
        upper = np.percentile(bootR, 97.5, axis=0)
        d["below_chance_on_R"] = {
            "chance": X.chance,
            "models_point_below": [m for i, m in enumerate(models) if R_[i] < X.chance],
            "models_upper95_below": [m for i, m in enumerate(models) if upper[i] < X.chance],
            "top10_upper95_below": [m for i, m in enumerate(models) if upper[i] < X.chance and m in top10],
            "chat_upper95_below": [m for i, m in enumerate(models) if upper[i] < X.chance and m in chat]}
        # C2: correlation with MMLU (15 models), and with the SAD score on the other 12 tasks (21)
        c2 = {}
        for s in ("full", "S", "R"):
            pt = X.score(X.mask(s), mm)
            bt = X.score(X.mask(s), mm, boot=True)
            c2[s] = {"r_mmlu": r3(pear(pt, mmlu)), "ci95": ci(corr_rows(bt, mmlu))}
        bf = corr_rows(X.score(X.mask("full"), mm, boot=True), mmlu)
        br = corr_rows(X.score(X.mask("R"), mm, boot=True), mmlu)
        c2["R_minus_full"] = {"diff": r3(c2["R"]["r_mmlu"] - c2["full"]["r_mmlu"]), "ci95": ci(br - bf),
                              "ci99.7_bonferroni16": ci(br - bf, 0.15625, 99.84375)}
        ov = np.array([other[m] for m in models])
        c2["r_sad_other_tasks_21"] = {s: r3(pear(X.score(X.mask(s), models), ov)) for s in ("full", "S", "R")}
        ar = [m for m in mm if m in ARENA]
        av = np.array([ARENA[m] for m in ar])
        c2["r_arena_10chat"] = {s: r3(pear(X.score(X.mask(s), ar), av)) for s in ("full", "S", "R")}
        d["C2_capability"] = c2
        # C3: chat - base, five pairs
        c3 = {}
        for s in ("full", "S", "R"):
            bt_b = X.score(X.mask(s), [b for b, _ in BASE_CHAT_PAIRS], boot=True)
            bt_c = X.score(X.mask(s), [c for _, c in BASE_CHAT_PAIRS], boot=True)
            pt = (X.score(X.mask(s), [c for _, c in BASE_CHAT_PAIRS]) - X.score(X.mask(s), [b for b, _ in BASE_CHAT_PAIRS]))
            c3[s] = {"mean_chat_minus_base": r3(pt.mean()), "ci95": ci((bt_c - bt_b).mean(1)),
                     "per_pair": {f"{c}-{b}": r3(x) for (b, c), x in zip(BASE_CHAT_PAIRS, pt)}}
        d["C3_chat_minus_base"] = c3
        # C4: sp - plain, base and chat
        c4 = {}
        for grp, ms in (("base", sorted(BASE)), ("chat", chat)):
            ms = [m for m in ms if f"{m}|sp" in X.runs]
            for s in ("full", "S", "R"):
                pt = X.score(X.mask(s), ms, "sp") - X.score(X.mask(s), ms, "plain")
                bt = X.score(X.mask(s), ms, "sp", boot=True) - X.score(X.mask(s), ms, "plain", boot=True)
                c4[f"{grp}_{s}"] = {"mean_sp_minus_plain": r3(pt.mean()), "ci95": ci(bt.mean(1)), "n_models": len(ms)}
        d["C4_sp_minus_plain"] = c4
        # shortcut index acc(S) - acc(R) per model, vs capability
        idx = X.score(X.mask("S"), models) - R_
        d["shortcut_index"] = {"per_model": {m: r3(x) for m, x in zip(models, idx)},
                               "r_with_mmlu_15": r3(pear(np.array([idx[models.index(m)] for m in mm]), mmlu)),
                               "r_with_sad_other_21": r3(pear(idx, ov))}
        res["tasks"][t] = d
        print(t, d["n_items"], "C1", d["C1_rank"], "\n  C2", {k: v for k, v in c2.items() if k in ("full", "S", "R", "R_minus_full")},
              "\n  C3", {s: c3[s]["mean_chat_minus_base"] for s in c3}, "\n  C4", {k: v["mean_sp_minus_plain"] for k, v in c4.items()},
              "\n  below", d["below_chance_on_R"]["models_upper95_below"], flush=True)

    # ---------- overall SAD with the four tasks restricted to a stratum ----------
    def overall(stratum, variant="plain", boot=False, ms=models, masks=None):
        out = []
        sub = {}
        for t in TASKS:
            m = masks[t] if masks else T[t].mask(stratum)
            ok = [x for x in ms if f"{x}|{variant}" in T[t].runs]
            s = T[t].score(m, ok, variant, boot)
            sub[t] = {x: (s[:, i] if boot else s[i]) for i, x in enumerate(ok)}
        for x in ms:
            base = dict(rel[(x, variant)])
            if not boot:
                for t in TASKS:
                    if x in sub[t]:
                        base[t] = sub[t][x]
                out.append(sad_score(base))
            else:
                rows = []
                for b in range(B):
                    bb = dict(base)
                    for t in TASKS:
                        if x in sub[t]:
                            bb[t] = sub[t][x][b]
                    rows.append(sad_score(bb))
                out.append(rows)
        return np.array(out) if not boot else np.array(out).T  # (models,) or (B, models)

    pub = np.array([sad_score(rel[(m, "plain")]) for m in models])
    ov_res = {"published_plain": {m: r3(x) for m, x in zip(models, pub)}}
    full_b = overall("full", boot=True)
    for s in ("full", "S", "R"):
        pt, bt = overall(s), (full_b if s == "full" else overall(s, boot=True))
        idx_mm = [models.index(m) for m in mm]
        ov_res[s] = {"scores": {m: r3(x) for m, x in zip(models, pt)},
                     "spearman_with_published": r3(spearman(pt, pub)), "spearman_ci95": ci(spearman_rows(bt, np.tile(pub, (B, 1)))),
                     "r_mmlu_15": r3(pear(pt[idx_mm], mmlu)), "r_mmlu_ci95": ci(corr_rows(bt[:, idx_mm], mmlu)),
                     "top3": sorted(models, key=lambda m: -pt[models.index(m)])[:3]}
        pb = [models.index(b) for b, _ in BASE_CHAT_PAIRS]
        pc = [models.index(c) for _, c in BASE_CHAT_PAIRS]
        ov_res[s]["chat_minus_base"] = r3((pt[pc] - pt[pb]).mean())
        ov_res[s]["chat_minus_base_ci95"] = ci((bt[:, pc] - bt[:, pb]).mean(1))
        for grp, ms in (("base", sorted(BASE)), ("chat", chat)):
            ps = overall(s, "sp", ms=ms)
            pp = overall(s, "plain", ms=ms)
            bs = overall(s, "sp", boot=True, ms=ms)
            bp = overall(s, "plain", boot=True, ms=ms)
            ov_res[s][f"sp_minus_plain_{grp}"] = r3((ps - pp).mean())
            ov_res[s][f"sp_minus_plain_{grp}_ci95"] = ci((bs - bp).mean(1))
    rmf = corr_rows(overall("R", boot=True)[:, [models.index(m) for m in mm]], mmlu) - corr_rows(full_b[:, [models.index(m) for m in mm]], mmlu)
    ov_res["R_minus_full_r_mmlu_ci95"] = ci(rmf)
    ov_res["published_r_mmlu_15_recomputed"] = r3(pear(pub[[models.index(m) for m in mm]], mmlu))
    ov_res["published_chat_minus_base_recomputed"] = r3(np.mean([pub[models.index(c)] - pub[models.index(b)] for b, c in BASE_CHAT_PAIRS]))
    res["overall"] = ov_res
    print("overall", {s: {k: ov_res[s][k] for k in ("spearman_with_published", "r_mmlu_15", "r_mmlu_ci95", "chat_minus_base", "sp_minus_plain_base", "sp_minus_plain_chat", "top3")} for s in ("full", "S", "R")}, flush=True)

    # ---------- per-item regression: correct ~ shortcut_right * mmlu_z + task FE ----------
    rows_X, rows_y, rows_item = [], [], []
    mz = (mmlu - mmlu.mean()) / mmlu.std()
    offset = 0
    item_g = []
    for ti, t in enumerate(TASKS):
        X = T[t]
        m = X.mask("S") | X.mask("R")
        sr = X.f.shortcut_right.to_numpy()[m]
        for j, mod in enumerate(mm):
            y = X.C[m, X.col(mod)]
            ok = ~np.isnan(y)
            y = y[ok]
            n = len(y)
            Z = np.zeros((n, 3 + len(TASKS)))
            Z[:, 0] = sr[ok]
            Z[:, 1] = mz[j]
            Z[:, 2] = sr[ok] * mz[j]
            Z[:, 3 + ti] = 1
            rows_X.append(Z); rows_y.append(y)
            rows_item.append(np.flatnonzero(m)[ok] + offset)
        offset += len(X.f)
    Xr = np.vstack(rows_X); yr = np.concatenate(rows_y); it = np.concatenate(rows_item)
    beta = logit_fit(Xr, yr, np.ones(len(yr)))
    Wall = np.hstack([T[t].W for t in TASKS])  # B x all items
    bb = np.array([logit_fit(Xr, yr, Wall[b, it]) for b in range(B)])
    names = ["shortcut_right", "mmlu_z", "shortcut_x_mmlu"] + [f"fe_{t}" for t in TASKS]
    res["regression"] = {"model": "logit(correct) ~ shortcut_right * mmlu_z + task FE, 15 models, plain",
                         "coef": {n: r3(b) for n, b in zip(names, beta)},
                         "ci95": {n: ci(bb[:, i]) for i, n in enumerate(names)}, "rows": int(len(yr))}
    per = {}
    for ti, t in enumerate(TASKS):
        sel = Xr[:, 3 + ti] == 1
        Z = Xr[sel][:, [0, 1, 2, 3 + ti]]
        bt = logit_fit(Z, yr[sel], np.ones(sel.sum()))
        bbt = np.array([logit_fit(Z, yr[sel], Wall[b, it[sel]]) for b in range(400)])
        per[t] = {"shortcut_x_mmlu": r3(bt[2]), "ci95_400boot": ci(bbt[:, 2]), "shortcut_right": r3(bt[0]),
                  "mmlu_z": r3(bt[1])}
    res["regression"]["per_task"] = per
    print("regression", res["regression"]["coef"], res["regression"]["ci95"]["shortcut_x_mmlu"], per, flush=True)

    # ---------- robustness ----------
    rob = {}

    def summary(X, mR, mS, ms=models):
        sR, sS = X.score(mR, models), X.score(mS, models)
        bt = X.score(mR, mm, boot=True)
        pc = [models.index(c) for _, c in BASE_CHAT_PAIRS]
        pb = [models.index(b) for b, _ in BASE_CHAT_PAIRS]
        return {"n_R": int(mR.sum()), "n_S": int(mS.sum()), "spearman_S_vs_R": r3(spearman(sS, sR)),
                "r_mmlu_R": r3(pear(X.score(mR, mm), mmlu)), "r_mmlu_R_ci95": ci(corr_rows(bt, mmlu)),
                "r_mmlu_S": r3(pear(X.score(mS, mm), mmlu)),
                "chat_minus_base_R": r3((sR[pc] - sR[pb]).mean()), "chat_minus_base_S": r3((sS[pc] - sS[pb]).mean()),
                "mean_R_top10": r3(np.mean([sR[models.index(m)] for m in top10])),
                "n_top10_below_chance_point_R": int(sum(sR[models.index(m)] < X.chance for m in top10))}

    for t in TASKS:
        X = T[t]
        r = {}
        alt = X.f.alt_right.to_numpy()
        r["alt_feature"] = summary(X, alt == 0, alt == 1)
        conf = X.f.conf.to_numpy()
        hiR = X.mask("R") & (conf >= np.median(conf[X.mask("R")]))
        hiS = X.mask("S") & (conf >= np.median(conf[X.mask("S")]))
        r["high_confidence_half"] = summary(X, hiR, hiS)
        q = X.f.key.str[:6].isin(QUESTIONABLE).to_numpy()
        r["drop_questionable_keys"] = summary(X, X.mask("R") & ~q, X.mask("S") & ~q)
        if t == "facts_human_defaults":
            first = (X.f.occ == 0).to_numpy()
            r["one_copy_per_item"] = summary(X, X.mask("R") & first, X.mask("S") & first)
        r["drop_subset"] = {}
        for sub in sorted(X.f.subset.dropna().unique()):
            keep = (X.f.subset != sub).to_numpy()
            if (X.mask("R") & keep).sum() >= 10:
                r["drop_subset"][str(sub)] = summary(X, X.mask("R") & keep, X.mask("S") & keep)
            else:
                r["drop_subset"][str(sub)] = {"n_R_left": int((X.mask("R") & keep).sum()), "note": "too few R items left"}
        r["drop_family"] = {}
        for fam in ("llama", "openai", "anthropic"):
            keep_m = [m for m in mm if FAMILY(m) != fam]
            v = np.array([MMLU[m] for m in keep_m])
            pairs = [(b, c) for b, c in BASE_CHAT_PAIRS if FAMILY(c) != fam]
            sR = X.score(X.mask("R"), models)
            sF = X.score(X.mask("full"), models)
            r["drop_family"][fam] = {"r_mmlu_full": r3(pear(X.score(X.mask("full"), keep_m), v)),
                                     "r_mmlu_R": r3(pear(X.score(X.mask("R"), keep_m), v)),
                                     "chat_minus_base_full": r3(np.mean([sF[models.index(c)] - sF[models.index(b)] for b, c in pairs])) if pairs else None,
                                     "chat_minus_base_R": r3(np.mean([sR[models.index(c)] - sR[models.index(b)] for b, c in pairs])) if pairs else None,
                                     "n_models": len(keep_m), "n_pairs": len(pairs)}
        rob[t] = r
    # placebo task
    X = T[PLACEBO_TASK]
    rob["placebo_task_facts_llms"] = summary(X, X.mask("R"), X.mask("S")) | {
        "r_mmlu_full": r3(pear(X.score(X.mask("full"), mm), mmlu))}
    res["robustness"] = rob

    # ---------- exploratory (not pre-registered) ----------
    # (1) bias-balanced score: mean of the S and R accuracies, which cancels a fixed lean toward
    #     the shortcut's answer (denial) or against it (affirmation).
    # (2) the paper's family claim, "Claude 3 models outperformed GPT-4 models" (p.9), on the
    #     overall score with the four tasks restricted to R.
    expl = {"note": "exploratory, defined after seeing the stratum results"}
    for t in TASKS:
        X = T[t]
        bal = (X.score(X.mask("S"), models) + X.score(X.mask("R"), models)) / 2
        bb = (X.score(X.mask("S"), mm, boot=True) + X.score(X.mask("R"), mm, boot=True)) / 2
        expl[t] = {"balanced_r_mmlu_15": r3(pear(np.array([bal[models.index(m)] for m in mm]), mmlu)),
                   "balanced_r_mmlu_ci95": ci(corr_rows(bb, mmlu)),
                   "balanced_spearman_with_full": r3(spearman(bal, X.score(X.mask("full"), models))),
                   "balanced_r_sad_other_21": r3(pear(bal, np.array([other[m] for m in models]))),
                   "balanced_scores": {m: r3(x) for m, x in zip(models, bal)}}
    c3m = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
    g4m = ["gpt-4-0613", "gpt-4-0125-preview"]
    fam = {}
    for s_ in ("full", "R"):
        pt = overall(s_)
        bt = full_b if s_ == "full" else overall(s_, boot=True)
        ic, ig = [models.index(m) for m in c3m], [models.index(m) for m in g4m]
        fam[s_] = {"claude3_minus_gpt4": r3(pt[ic].mean() - pt[ig].mean()),
                   "ci95": ci(bt[:, ic].mean(1) - bt[:, ig].mean(1))}
        for t in ("influence", "facts_human_defaults"):
            X = T[t]
            v = X.score(X.mask(s_), models)
            vb = X.score(X.mask(s_), models, boot=True)
            fam[s_][t] = {"claude3_minus_gpt4": r3(v[ic].mean() - v[ig].mean()),
                          "ci95": ci(vb[:, ic].mean(1) - vb[:, ig].mean(1))}
    expl["claude3_vs_gpt4"] = fam
    res["exploratory"] = expl
    print("EXPL", json.dumps({k: (v if k == "claude3_vs_gpt4" else {x: y for x, y in v.items() if x != "balanced_scores"}) for k, v in expl.items() if k != "note"}), flush=True)
    for t in rob:
        print("ROB", t, json.dumps(rob[t])[:1500], flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
