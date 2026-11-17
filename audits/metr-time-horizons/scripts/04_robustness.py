"""E4 family influence, E5 content-blind predictor, E6 multiverse, placebo half-splits, token-cap
diagnostics (prereg.md). Output: results/robustness.json
"""
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import C, RUNS_11, SIXTEEN_H, doubling_time, fit_agents, invsqrt_weights, load_counts, save, sota_agents

PUB_CI = (104.428, 158.012)
FRONTIER = ["Claude Opus 4.6 (Inspect)", "GPT-5.2", "GPT-5.3-Codex", "Claude Opus 4.5 (Inspect)", "Gemini 3 Pro"]

df, dates = load_counts()
df["x"] = np.log2(df.human_minutes)
df["w"] = invsqrt_weights(df)
ref = fit_agents(df)
SOTA = sota_agents(ref.p50, dates)
REF_DT = doubling_time(ref.p50, dates, SOTA)
out = {"reference_dt": REF_DT}


def refit(sub):
    sub = sub.copy()
    sub["w"] = invsqrt_weights(sub)
    return fit_agents(sub)


# ---- E4 drop one family -------------------------------------------------------------------
rows = []
for fam in sorted(df.family.unique()):
    f = refit(df[df.family != fam])
    rows.append(dict(family=fam, n_tasks=int(df[df.family == fam].task_id.nunique()),
                     source=df[df.family == fam].source.iloc[0],
                     dt=doubling_time(f.p50, dates, SOTA),
                     top=max(FRONTIER, key=lambda a: f.p50[a]),
                     **{"p50|" + a: float(f.p50[a]) for a in FRONTIER}))
e4 = pd.DataFrame(rows)
e4["dt_change_pct"] = 100 * (e4.dt / REF_DT - 1)
e4["opus46_change_pct"] = 100 * (e4["p50|Claude Opus 4.6 (Inspect)"] / ref.p50["Claude Opus 4.6 (Inspect)"] - 1)
out["E4"] = dict(
    n_families=len(e4), dt_min=float(e4.dt.min()), dt_max=float(e4.dt.max()),
    n_outside_pub_ci=int(((e4.dt < PUB_CI[0]) | (e4.dt > PUB_CI[1])).sum()),
    n_top_changes=int((e4.top != "Claude Opus 4.6 (Inspect)").sum()),
    top_changes=e4[e4.top != "Claude Opus 4.6 (Inspect)"][["family", "top"]].to_dict(orient="records"),
    most_influential_dt=e4.reindex(e4.dt_change_pct.abs().sort_values(ascending=False).index).head(6)[
        ["family", "source", "n_tasks", "dt", "dt_change_pct"]].to_dict(orient="records"),
    most_influential_opus46=e4.reindex(e4.opus46_change_pct.abs().sort_values(ascending=False).index).head(6)[
        ["family", "source", "n_tasks", "p50|Claude Opus 4.6 (Inspect)", "opus46_change_pct"]].to_dict(orient="records"),
    frontier_p50_range={a: [float(e4["p50|" + a].min()), float(e4["p50|" + a].max())] for a in FRONTIER},
)

# ---- E5 content-blind predictor -----------------------------------------------------------
avg = df.assign(r=df.k / df.n.clip(lower=1)).groupby("agent").apply(lambda g: np.average(g.r, weights=g.w), include_groups=False)
rho = spearmanr(avg[ref.index], ref.p50).statistic
# leave-one-out-free mapping: logit(avg) -> log p50 linear fit R^2
lg = np.log(avg[ref.index] / (1 - avg[ref.index]))
coef = np.polyfit(lg, np.log(ref.p50), 1)
pred = np.polyval(coef, lg)
r2 = 1 - np.sum((np.log(ref.p50) - pred) ** 2) / np.sum((np.log(ref.p50) - np.log(ref.p50).mean()) ** 2)
order_same = int((np.argsort(np.argsort(-avg[ref.index].to_numpy())) == np.argsort(np.argsort(-ref.p50.to_numpy()))).sum())


def fit_glm(X, k, n, w, pen):
    w = np.where(n > 0, w / np.maximum(n, 1), 0.0)
    ws, wt = w * k, w * n
    beta = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-(X @ beta)))
        g = X.T @ (ws - wt * p) - pen * beta
        H = (X * (wt * p * (1 - p))[:, None]).T @ X + np.diag(pen)
        step = np.linalg.solve(H, g)
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    return beta


agents = sorted(df.agent.unique())
A = np.eye(len(agents))[df.agent.map({a: i for i, a in enumerate(agents)})]
fams = sorted(df.family.unique())
rng = np.random.default_rng(7)
fold_of_fam = dict(zip(fams, rng.permutation(np.arange(len(fams)) % 5)))
fold = df.family.map(fold_of_fam).to_numpy()


def design(kind, src):
    cols = [A]
    if kind in ("source", "both"):
        cols += [(src == "SWAA").astype(float)[:, None], (src == "RE-Bench").astype(float)[:, None]]
    if kind in ("time", "both"):
        cols += [A * df.x.to_numpy()[:, None]]
    return np.hstack(cols)


def cv_auc(kind, src):
    X = design(kind, src)
    pen = np.r_[np.zeros(len(agents)), np.full(X.shape[1] - len(agents), 1 / C)]
    p = np.zeros(len(df))
    for f in range(5):
        tr, te = fold != f, fold == f
        b = fit_glm(X[tr], df.k.to_numpy(float)[tr], df.n.to_numpy(float)[tr], df.w.to_numpy(float)[tr], pen)
        p[te] = 1 / (1 + np.exp(-(X[te] @ b)))
    y = np.r_[np.ones(len(df)), np.zeros(len(df))]
    sw = np.r_[df.k, df.n - df.k]
    return float(roc_auc_score(y, np.r_[p, p], sample_weight=sw))


src = df.source.to_numpy()
auc = {k: cv_auc(k, src) for k in ["source", "time", "both"]}
fam_src = df.drop_duplicates("family").set_index("family").source
null = []
for i in range(1000):
    r = np.random.default_rng(10_000 + i)
    perm = dict(zip(fam_src.index, r.permutation(fam_src.to_numpy())))
    null.append(cv_auc("source", df.family.map(perm).to_numpy()))
null = np.array(null)
out["E5"] = dict(spearman_p50_vs_weighted_success=float(rho), r2_logp50_on_logit_success=float(r2),
                 rank_positions_identical=order_same, n_agents=len(ref),
                 cv_auroc=auc, source_null_mean=float(null.mean()), source_null_q975=float(np.percentile(null, 97.5)),
                 source_null_p=float((np.sum(null >= auc["source"]) + 1) / (len(null) + 1)))

# ---- E6 multiverse ------------------------------------------------------------------------
eq = df.copy()
eq["w"] = 1.0
eq["w"] = eq.w / eq.groupby("agent").w.transform("sum")
fits = {"invsqrt": ref, "equal": fit_agents(eq)}
specs = []
for start in ["2023-01-01", "2024-01-01", "2025-01-01"]:
    for aset in ["sota", "all"]:
        for excl in [True, False]:
            for wname, f in fits.items():
                p50 = f.p50
                if aset == "sota":
                    ag = sota_agents(p50, dates, after=start, max_p50=SIXTEEN_H if excl else None)
                else:
                    ag = [a for a in p50.index if dates[a] >= pd.Timestamp(start) and (not excl or p50[a] <= SIXTEEN_H)]
                specs.append(dict(start=start, agents=aset, excl16h=excl, weighting=wname, n_agents=len(ag),
                                  dt=doubling_time(p50, dates, ag)))
e6 = pd.DataFrame(specs)
out["E6"] = dict(specs=specs, median=float(e6.dt.median()), min=float(e6.dt.min()), max=float(e6.dt.max()),
                 share_inside_pub_ci=float(((e6.dt >= PUB_CI[0]) & (e6.dt <= PUB_CI[1])).mean()),
                 by_start=e6.groupby("start").dt.agg(["median", "min", "max"]).to_dict(orient="index"))

# ---- Placebo: random halves of HCAST families (plus all SWAA and RE-Bench) ------------------
hf = sorted(df[df.source == "HCAST"].family.unique())
pl = []
for i in range(200):
    r = np.random.default_rng(20_000 + i)
    half = set(r.choice(hf, size=len(hf) // 2, replace=False))
    for keep in (half, set(hf) - half):
        sub = df[(df.source != "HCAST") | df.family.isin(keep)]
        f = refit(sub)
        pl.append(dict(dt=doubling_time(f.p50, dates, SOTA), opus46=float(f.p50["Claude Opus 4.6 (Inspect)"]),
                       n_tasks=int(sub.task_id.nunique())))
pl = pd.DataFrame(pl)
pl["ratio"] = pl.dt / REF_DT
out["placebo_half_hcast"] = dict(n=len(pl), dt_ratio_q=[float(pl.ratio.quantile(q)) for q in (0.025, 0.5, 0.975)],
                                 opus46_ratio_q=[float((pl.opus46 / ref.p50["Claude Opus 4.6 (Inspect)"]).quantile(q))
                                                 for q in (0.025, 0.5, 0.975)],
                                 mean_tasks=float(pl.n_tasks.mean()))

# ---- Token-cap diagnostics -----------------------------------------------------------------
runs = pd.read_json(RUNS_11, lines=True)
runs = runs[(runs.alias != "human")]
runs["tokens_count"] = runs.tokens_count.fillna(0)
succ = runs[runs.score_binarized == 1]
diag = {}
for cap in (8e6, 0.8e6):
    over = succ[succ.tokens_count > cap]
    diag[f"{cap/1e6:g}M"] = dict(
        successes_over_cap=int(len(over)),
        by_source=over.task_source.value_counts().to_dict(),
        by_agent=over.alias.value_counts().to_dict(),
        median_human_minutes=float(over.human_minutes.median()) if len(over) else None,
        usage_limit_terminated_but_scored_success=int(over.fatal_error_from.eq("usageLimits").sum()),
    )
out["token_cap_diagnostics"] = diag

save("robustness.json", out)
print("E4", {k: v for k, v in out["E4"].items() if k not in ("most_influential_dt", "most_influential_opus46")})
print(pd.DataFrame(out["E4"]["most_influential_dt"]).round(2).to_string())
print(pd.DataFrame(out["E4"]["most_influential_opus46"]).round(2).to_string())
print("E5", out["E5"])
print("E6", {k: v for k, v in out["E6"].items() if k != "specs"})
print(e6.round(1).to_string())
print("placebo", out["placebo_half_hcast"])
print("diag", diag)
