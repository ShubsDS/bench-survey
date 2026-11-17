"""Effect tests E1-E3 (prereg.md), with paired family->task->run bootstrap.

Output: results/effects.json
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import (C, RUNS_11, doubling_time, fit_agents, invsqrt_weights, load_counts, save, sota_agents)

N_BOOT = int(__import__("os").environ.get("N_BOOT", 1000))  # override only for smoke tests
SEED0 = 1000
PUB_CI = (104.428, 158.012)
FRONTIER = ["Claude Opus 4.6 (Inspect)", "GPT-5.2", "GPT-5.3-Codex", "Claude Opus 4.5 (Inspect)", "Gemini 3 Pro"]
CAP_HI, CAP_LO = 8e6, 0.8e6

counts, dates = load_counts()
counts["x"] = np.log2(counts.human_minutes)

# Run-level token split: A success <=0.8M, B success (0.8M, 8M], Cc success > 8M, F failure.
runs = pd.read_json(RUNS_11, lines=True)
runs = runs[runs.alias != "human"]
s = runs.score_binarized.eq(1)
# 1,056 SWAA runs (GPT-4 0314, o1-preview; single-turn, seconds long) have no token count: treat as 0.
runs["tokens_count"] = runs.tokens_count.fillna(0)
runs["A"] = s & (runs.tokens_count <= CAP_LO)
runs["B"] = s & (runs.tokens_count > CAP_LO) & (runs.tokens_count <= CAP_HI)
runs["Cc"] = s & (runs.tokens_count > CAP_HI)
tok = runs.groupby(["alias", "task_id"])[["A", "B", "Cc"]].sum().reset_index().rename(columns={"alias": "agent"})
df = counts.merge(tok, on=["agent", "task_id"], how="left")
df["has_runs"] = df.A.notna()
# Agents without run data: put all successes in A (never used for the cap variants).
df["A"] = np.where(df.has_runs, df.A, df.k).astype(int)
df[["B", "Cc"]] = df[["B", "Cc"]].fillna(0).astype(int)
assert (df.A + df.B + df.Cc == df.k).all()
df["F"] = df.n - df.k
RUN_AGENTS = sorted(df[df.has_runs].agent.unique())

# Variants: (row mask, success column, agent subset, weighting)
def eq_weights(d):
    w = pd.Series(1.0, index=d.index)
    return w / w.groupby(d.agent).transform("sum")

VARIANTS = {
    "reference": (lambda d: d.index == d.index, "k", None, "invsqrt"),
    "E1b_hcast_only": (lambda d: d.source == "HCAST", "k", None, "invsqrt"),
    "E1c_no_swaa": (lambda d: d.source != "SWAA", "k", None, "invsqrt"),
    "E2b_baselined_only": (lambda d: d.human_source == "baseline", "k", None, "invsqrt"),
    "E2c_hcast_baselined": (lambda d: (d.source == "HCAST") & (d.human_source == "baseline"), "k", None, "invsqrt"),
    "E3_cap_8M": (lambda d: d.index == d.index, "k8", RUN_AGENTS, "invsqrt"),
    "E3_cap_0.8M": (lambda d: d.index == d.index, "k08", RUN_AGENTS, "invsqrt"),
    "R_hcast_only_equalw": (lambda d: d.source == "HCAST", "k", None, "equal"),
    "R_baselined_only_equalw": (lambda d: d.human_source == "baseline", "k", None, "equal"),
}

# Precompute weights for each variant on the original data (carried through the bootstrap, as METR does).
for name, (mask, kcol, agents, wt) in VARIANTS.items():
    sub = df[mask(df) & (df.agent.isin(agents) if agents else True)]
    w = invsqrt_weights(sub) if wt == "invsqrt" else eq_weights(sub)
    df["w_" + name] = w.reindex(df.index)

pub_sota = sota_agents(fit_agents(df.assign(w=df.w_reference)).p50, dates)


def variant_fits(d):
    d = d.assign(k8=d.A + d.B, k08=d.A)
    out = {}
    for name, (mask, kcol, agents, wt) in VARIANTS.items():
        sub = d[mask(d)]
        if agents:
            sub = sub[sub.agent.isin(agents)]
        sub = sub.assign(k=sub[kcol], w=sub["w_" + name])
        out[name] = fit_agents(sub)
    return out


# ---- joint models (E1a, E2a) -------------------------------------------------------------
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


def joint(d, dummies, agent_specific=False):
    agents = sorted(d.agent.unique())
    ai = d.agent.map({a: i for i, a in enumerate(agents)}).to_numpy()
    na = len(agents)
    cols = [np.eye(na)[ai], np.eye(na)[ai] * d.x.to_numpy()[:, None]]
    names = []
    for dm in dummies:
        v = dm[1](d).to_numpy().astype(float)
        if agent_specific:
            cols.append(np.eye(na)[ai] * v[:, None])
            names += [f"{dm[0]}|{a}" for a in agents]
        else:
            cols.append(v[:, None])
            names.append(dm[0])
    X = np.hstack(cols)
    pen = np.r_[np.zeros(na), np.full(X.shape[1] - na, 1 / C)]
    beta = fit_glm(X, d.k.to_numpy(float), d.n.to_numpy(float), d.w.to_numpy(float), pen)
    return dict(zip(names, beta[2 * na:]))


SWAA = ("SWAA", lambda d: d.source == "SWAA")
REB = ("RE-Bench", lambda d: d.source == "RE-Bench")
EST = ("estimate", lambda d: d.human_source == "estimate")


def joint_stats(d):
    out = {}
    out.update({"E1a_" + k: v for k, v in joint(d.assign(w=d.w_reference), [SWAA, REB]).items()})
    ns = d[d.source != "SWAA"]
    ns = ns.assign(w=ns.w_E1c_no_swaa)
    out.update({"E2a_" + k: v for k, v in joint(ns, [REB, EST]).items()})
    mid = ns[(ns.human_minutes >= 60) & (ns.human_minutes <= 1000)]
    out.update({"E2a_60to1000min_" + k: v for k, v in joint(mid, [REB, EST]).items()})
    hc = d[d.source == "HCAST"]
    out.update({"E2a_hcast_" + k: v for k, v in joint(hc.assign(w=hc.w_E1b_hcast_only), [EST]).items()})
    fr = d[d.agent.isin(FRONTIER)]
    out.update({"E1a_agent_" + k: v for k, v in
                joint(fr.assign(w=fr.w_reference), [SWAA, REB], agent_specific=True).items() if k.startswith("RE-Bench")})
    return out


# ---- point estimates ---------------------------------------------------------------------
point_fits = variant_fits(df)
point_joint = joint_stats(df)


def summarize_point(fits):
    p50 = fits.p50
    sota_fixed = [a for a in pub_sota if a in p50.index and np.isfinite(p50[a])]
    resel = sota_agents(p50, dates)
    return dict(
        dt_fixed=doubling_time(p50, dates, sota_fixed),
        dt_reselected=doubling_time(p50, dates, resel), reselected_sota=resel,
        p50={a: float(p50[a]) for a in p50.index}, p80={a: float(fits.p80[a]) for a in p50.index},
        frontier_top=max(FRONTIER, key=lambda a: p50.get(a, -1)),
    )


point = {name: summarize_point(f) for name, f in point_fits.items()}

# ---- paired bootstrap --------------------------------------------------------------------
by_task = {t: g for t, g in df.groupby("task_id")}
fam_tasks = df.drop_duplicates("task_id").groupby("family").task_id.apply(list)
boot_dt = {n: [] for n in VARIANTS}
boot_dt_resel = {n: [] for n in VARIANTS}
boot_p50 = {n: [] for n in VARIANTS}
boot_joint = []
for i in range(N_BOOT):
    rng = np.random.default_rng(SEED0 + i)
    draw = []
    for f in rng.choice(len(fam_tasks), size=len(fam_tasks), replace=True):
        tl = fam_tasks.iloc[f]
        draw += [tl[j] for j in rng.choice(len(tl), size=len(tl), replace=True)]
    b = pd.concat([by_task[t] for t in draw], ignore_index=True)
    nn = b.n.to_numpy()
    probs = np.stack([b.A, b.B, b.Cc, b.F], 1) / np.maximum(nn, 1)[:, None]
    probs[nn == 0] = [0, 0, 0, 1]
    m = rng.multinomial(nn, probs)
    b = b.assign(A=m[:, 0], B=m[:, 1], Cc=m[:, 2], F=m[:, 3])
    b["k"] = b.A + b.B + b.Cc
    fits = variant_fits(b)
    for name, f in fits.items():
        p50 = f.p50
        sf = [a for a in pub_sota if a in p50.index and np.isfinite(p50[a]) and p50[a] >= 1e-3]
        boot_dt[name].append(doubling_time(p50, dates, sf))
        rs = sota_agents(p50.dropna(), dates)
        boot_dt_resel[name].append(doubling_time(p50, dates, rs))
        boot_p50[name].append(p50.reindex(FRONTIER))
    boot_joint.append(joint_stats(b))
    if i % 100 == 0:
        print("draw", i, flush=True)


def ci(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def ci_bonf(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return [float(np.percentile(a, 100 * 0.05 / 6)), float(np.percentile(a, 100 * (1 - 0.05 / 6)))]


ref_dt = np.array(boot_dt["reference"])
out = {"n_boot": N_BOOT, "seed0": SEED0, "published_sota_set": pub_sota, "variants": {}}
for name in VARIANTS:
    dt = np.array(boot_dt[name])
    ok = (dt > 0) & (ref_dt > 0)
    ratio = dt[ok] / ref_dt[ok]
    P = point[name]
    ratio_point = P["dt_fixed"] / point["reference"]["dt_fixed"]
    rci = ci(ratio)
    outside = not (PUB_CI[0] <= P["dt_fixed"] <= PUB_CI[1])
    verdict = ("changes" if (rci[0] > 1 or rci[1] < 1) and outside else
               "shifts" if (rci[0] > 1 or rci[1] < 1) else "holds")
    hp = pd.DataFrame(boot_p50[name])
    hr = pd.DataFrame(boot_p50["reference"])
    horizons = {}
    for a in FRONTIER:
        if a not in P["p50"] or not np.isfinite(P["p50"][a]):
            continue
        r = (hp[a] / hr[a]).to_numpy()
        rp = P["p50"][a] / point["reference"]["p50"][a]
        rc = ci(r)
        horizons[a] = dict(p50=P["p50"][a], p50_ci=ci(hp[a]), p80=P["p80"][a], ratio=rp, ratio_ci=rc,
                           verdict="changes" if (rc[0] > 1 or rc[1] < 1) and not (0.8 <= rp <= 1.25) else "holds")
    out["variants"][name] = dict(
        n_tasks=int(df[VARIANTS[name][0](df)].task_id.nunique()),
        n_families=int(df[VARIANTS[name][0](df)].family.nunique()),
        dt=P["dt_fixed"], dt_ci=ci(dt[dt > 0]), dt_ratio=ratio_point, dt_ratio_ci=rci,
        dt_ratio_ci_bonferroni3=ci_bonf(ratio), dt_verdict=verdict,
        n_boot_valid=int(ok.sum()),
        dt_reselected_sota=P["dt_reselected"], dt_reselected_ci=ci([d for d in boot_dt_resel[name] if d > 0]),
        reselected_sota=P["reselected_sota"], frontier_top=P["frontier_top"], horizons=horizons,
        p50_all=P["p50"],
    )
bj = pd.DataFrame(boot_joint)
out["joint"] = {k: dict(point=float(v), ci=ci(bj[k])) for k, v in point_joint.items()}

save("effects.json", out)
for name, v in out["variants"].items():
    print(f"{name:28s} tasks={v['n_tasks']:3d} DT={v['dt']:7.1f} {np.round(v['dt_ci'],1)} ratio={v['dt_ratio']:.3f} "
          f"{np.round(v['dt_ratio_ci'],3)} -> {v['dt_verdict']}; resel DT={v['dt_reselected_sota']:.1f}; top={v['frontier_top']}")
    for a, h in v["horizons"].items():
        print(f"     {a:28s} p50={h['p50']:8.1f} {np.round(h['p50_ci'],1)} ratio={h['ratio']:.3f} {np.round(h['ratio_ci'],3)} {h['verdict']}")
for k, v in out["joint"].items():
    print(f"{k:45s} {v['point']:+.3f} {np.round(v['ci'],3)}")
