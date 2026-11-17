"""Independent validation of the METR time-horizon audit (claims 1 and 2, plus token-budget attacks).

Written from scratch by the validator. It does not import anything from ../scripts. It reads:
  - data/eval-analysis-public/reports/time-horizon-1-1/data/raw/runs.jsonl   (TH1.1 runs)
  - data/eval-analysis-public/reports/time-horizon-1-0/data/raw/runs.jsonl   (TH1.0 runs, natural experiment)
  - data/published/benchmark_results_1_1.yaml, task_results_1_1.yaml         (METR's published numbers)
The fit is METR's own choice of estimator (sklearn LogisticRegression, C = 1/1e-5, sample weights =
invsqrt task weights normalised per agent), called directly rather than through the auditor's Newton
solver. Weights, SOTA set, bootstrap and rescoring are re-implemented here.

Run:  data/.venv/bin/python -I validation/validate.py      (about 5 minutes)
Output: validation/validation.json
"""
import json
import pathlib
import warnings

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
D = ROOT / "data"
R11 = D / "eval-analysis-public/reports/time-horizon-1-1/data/raw/runs.jsonl"
R10 = D / "eval-analysis-public/reports/time-horizon-1-0/data/raw/runs.jsonl"
PB = D / "published/benchmark_results_1_1.yaml"
PT = D / "published/task_results_1_1.yaml"
N_BOOT = int(__import__("os").environ.get("N_BOOT", 1000))  # override only for smoke tests
SEED = 777
O46, O45, G52, G53 = "Claude Opus 4.6 (Inspect)", "Claude Opus 4.5 (Inspect)", "GPT-5.2", "GPT-5.3-Codex"
FRONT = [O46, G52, G53, O45, "Gemini 3 Pro"]
OUT = {}

# ---------------------------------------------------------------- data
runs = pd.read_json(R11, lines=True)
runs = runs[runs.alias != "human"].reset_index(drop=True)
runs["tok"] = runs.tokens_count.fillna(0.0)
OUT["n_runs_no_tokens"] = {f"{a}|{s}": int(v) for (a, s), v in
                            runs[runs.tokens_count.isna()].groupby(["alias", "task_source"]).size().items()}
pt = yaml.safe_load(PT.read_text())
pb = yaml.safe_load(PB.read_text())
dates = {a: pd.Timestamp(str(v["release_date"])) for a, v in pt["agents"].items()}
meta = runs.groupby("task_id").agg(family=("task_family", "first"), source=("task_source", "first"),
                                   hsrc=("human_source", "first"), minutes=("human_minutes", "first"))


def weights(df):
    """invsqrt: task weight 1/sqrt(#tasks of that family the agent ran), normalised to 1 per agent."""
    f = df.groupby(["agent", "family"]).task_id.transform("nunique")
    w = 1 / np.sqrt(f)
    return w / w.groupby(df.agent).transform("sum")


def fit_one(x, k, n, w):
    """Weighted logistic on run outcomes, aggregated to a success row and a failure row per task."""
    ws, wf = w * k / n, w * (n - k) / n
    X = np.r_[x, x][:, None]
    y = np.r_[np.ones(len(x)), np.zeros(len(x))]
    sw = np.r_[ws, wf]
    keep = sw > 0
    if y[keep].min() == y[keep].max():
        return np.nan, np.nan
    m = LogisticRegression(C=1e5).fit(X[keep], y[keep], sample_weight=sw[keep])
    return m.intercept_[0], m.coef_[0][0]


def p50s(df, kcol="k"):
    out = {}
    for a, g in df.groupby("agent", sort=False):
        b0, b1 = fit_one(np.log2(g.minutes.to_numpy()), g[kcol].to_numpy(float), g.n.to_numpy(float),
                         g.w.to_numpy(float))
        out[a] = 2 ** (-b0 / b1) if np.isfinite(b1) and b1 < 0 else np.nan
    return pd.Series(out)


def dt(p, agents):
    x = np.array([(dates[a] - pd.Timestamp("2000-01-01")).days for a in agents], float)
    y = np.log(np.array([p[a] for a in agents], float))
    ok = np.isfinite(y)
    return float(np.log(2) / np.polyfit(x[ok], y[ok], 1)[0])


# ---------------------------------------------------------------- claim 1: reproduction
# (i) counts from runs.jsonl (20 agents), (ii) counts from task_results_1_1.yaml (23 agents)
cnt_runs = runs.groupby(["alias", "task_id"]).agg(k=("score_binarized", "sum"), n=("run_id", "size")).reset_index()
cnt_runs = cnt_runs.rename(columns={"alias": "agent"}).join(meta, on="task_id")
cnt_runs["w"] = weights(cnt_runs)
rows = [(a, t["task_id"], t["n_successes"], t["n_runs"]) for a, v in pt["agents"].items() for t in v["tasks"]]
cnt_pub = pd.DataFrame(rows, columns=["agent", "task_id", "k", "n"]).join(meta, on="task_id")
cnt_pub["w"] = weights(cnt_pub)
mm = cnt_runs.merge(cnt_pub, on=["agent", "task_id"], suffixes=("_r", "_p"))
# check our weights against METR's precomputed invsqrt_task_weight column
wm = runs.groupby(["alias", "task_id"]).invsqrt_task_weight.sum().rename("w_metr").reset_index()
wm = cnt_runs.merge(wm, left_on=["agent", "task_id"], right_on=["alias", "task_id"])
OUT["counts_check"] = dict(pairs=len(mm), k_mismatch=int((mm.k_r != mm.k_p).sum()),
                           n_mismatch=int((mm.n_r != mm.n_p).sum()),
                           max_abs_weight_diff_vs_metr_column=float((wm.w - wm.w_metr).abs().max()))

# published p50 per alias: use the coefficient/intercept METR printed in task_results_1_1.yaml, and
# cross-match to benchmark_results_1_1.yaml for is_sota and the headline p50.
pub_p50 = {a: 2 ** (-v["intercept"] / v["coefficient"]) for a, v in pt["agents"].items()}
bench = {k: (v["metrics"]["p50_horizon_length"]["estimate"], v["metrics"]["is_sota"], str(v["release_date"]))
         for k, v in pb["results"].items()}
alias2key = {}
for a, p in pub_p50.items():
    cands = [k for k, (e, s, d) in bench.items() if d == str(dates[a].date())]
    alias2key[a] = min(cands, key=lambda k: abs(np.log(bench[k][0] / p)))
p_pub = p50s(cnt_pub)
p_run = p50s(cnt_runs)
rep = pd.DataFrame({"mine_taskyaml": p_pub, "mine_runs": p_run.reindex(p_pub.index),
                    "published": {a: bench[alias2key[a]][0] for a in p_pub.index}})
rep["logratio_taskyaml"] = np.log(rep.mine_taskyaml / rep.published)
rep["logratio_runs"] = np.log(rep.mine_runs / rep.published)
SOTA = [a for a in p_pub.index if bench[alias2key[a]][1] and dates[a] >= pd.Timestamp("2023-01-01")
        and bench[alias2key[a]][0] <= 960]
OUT["claim1"] = dict(
    per_agent=rep.round(6).reset_index(names="agent").to_dict(orient="records"),
    max_abs_logratio_taskyaml=float(rep.logratio_taskyaml.abs().max()),
    max_abs_logratio_runs=float(rep.logratio_runs.abs().max()),
    sota_2023=SOTA, n_sota=len(SOTA),
    dt_taskyaml=dt(p_pub, SOTA), dt_runs=dt(p_run, SOTA),
    dt_published_p50s=dt(rep.published, SOTA), dt_published=128.744)

# ---------------------------------------------------------------- run table for cap work (20 agents)
RA = sorted(runs.alias.unique())
rt = runs[["alias", "task_id", "score_binarized", "tok", "task_source", "fatal_error_from"]].rename(
    columns={"alias": "agent", "score_binarized": "s"})
CAPS_M = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 20]


def agg(rt_, cap=None, spare_rebench=False):
    s = rt_.s.to_numpy().astype(bool)
    if cap is not None:
        over = rt_.tok.to_numpy() > cap
        if spare_rebench:
            over &= rt_.task_source.to_numpy() != "RE-Bench"
        s = s & ~over
    g = rt_.assign(kk=s.astype(int)).groupby(["agent", "task_id"]).agg(k=("kk", "sum"), n=("kk", "size")).reset_index()
    return g.join(meta, on="task_id")


base = agg(rt)
base["w"] = weights(base)
W = base.set_index(["agent", "task_id"]).w


def with_w(g):
    return g.assign(w=W.reindex(pd.MultiIndex.from_frame(g[["agent", "task_id"]])).to_numpy())


ref = p50s(base)
trace = {}
for c in CAPS_M:
    p = p50s(with_w(agg(rt, c * 1e6)))
    trace[f"{c}M"] = dict(dt=dt(p, SOTA), dt_ratio=dt(p, SOTA) / dt(ref, SOTA),
                          **{a: float(p[a]) for a in FRONT}, **{"ratio|" + a: float(p[a] / ref[a]) for a in FRONT},
                          opus46_over_opus45=float(p[O46] / p[O45]),
                          opus45_above_gpt52_and_gpt53=bool(p[O45] > p[G52] and p[O45] > p[G53]))
trace["uncapped"] = dict(dt=dt(ref, SOTA), **{a: float(ref[a]) for a in FRONT}, opus46_over_opus45=float(ref[O46] / ref[O45]))
OUT["cap_trace_point"] = trace
p_sp = p50s(with_w(agg(rt, 8e6, spare_rebench=True)))
OUT["cap8M_spare_rebench_point"] = {a: float(p_sp[a] / ref[a]) for a in FRONT} | {"dt_ratio": dt(p_sp, SOTA) / dt(ref, SOTA)}

# ---------------------------------------------------------------- paired bootstrap: family -> task -> run
fam_tasks = meta.groupby("family").apply(lambda g: list(g.index), include_groups=False)
rt_idx = {k: v.to_numpy() for k, v in rt.groupby(["agent", "task_id"]).groups.items()}
rt_s, rt_tok, rt_src = rt.s.to_numpy().astype(bool), rt.tok.to_numpy(), rt.task_source.to_numpy()
pairs_by_task = rt.groupby("task_id").agent.unique()
VARS = {"ref": None, "cap8": 8e6, "cap8_spare_rebench": "spare", "cap4": 4e6, "cap12": 12e6}
boot = {v: [] for v in VARS}
for i in range(N_BOOT):
    rng = np.random.default_rng(SEED + i)
    rows = []
    for f in rng.choice(len(fam_tasks), len(fam_tasks)):
        tl = fam_tasks.iloc[f]
        for t in rng.choice(len(tl), len(tl)):
            tid = tl[t]
            for a in pairs_by_task[tid]:
                idx = rt_idx[(a, tid)]
                pick = idx[rng.integers(0, len(idx), len(idx))]
                s, tk, sr = rt_s[pick], rt_tok[pick], rt_src[pick]
                rows.append((a, tid, len(pick), s.sum(), (s & (tk <= 8e6)).sum(),
                             (s & ((tk <= 8e6) | (sr == "RE-Bench"))).sum(), (s & (tk <= 4e6)).sum(),
                             (s & (tk <= 12e6)).sum()))
    b = pd.DataFrame(rows, columns=["agent", "task_id", "n", "ref", "cap8", "cap8_spare_rebench", "cap4", "cap12"])
    b = b.join(meta, on="task_id")
    b["w"] = W.reindex(pd.MultiIndex.from_frame(b[["agent", "task_id"]])).to_numpy()  # carried, not renormalised
    for v in VARS:
        p = p50s(b, kcol=v)
        boot[v].append(dict(dt=dt(p, SOTA), **{a: p[a] for a in FRONT}))
    if i % 100 == 0:
        print("draw", i, flush=True)


def q(a, lo=2.5, hi=97.5):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return [None, None]
    return [float(np.percentile(a, lo)), float(np.percentile(a, hi))]


B = {v: pd.DataFrame(boot[v]) for v in VARS}
bs = {}
for v in VARS:
    if v == "ref":
        bs[v] = dict(dt_ci=q(B[v].dt), **{a + "_ci": q(B[v][a]) for a in FRONT},
                     opus46_over_opus45_ci=q(B[v][O46] / B[v][O45]),
                     p_opus45_above_gpt52=float((B[v][O45] > B[v][G52]).mean()),
                     p_opus45_above_both_gpt=float(((B[v][O45] > B[v][G52]) & (B[v][O45] > B[v][G53])).mean()))
        continue
    r = B[v].div(B["ref"])
    bs[v] = dict(
        dt_ci=q(B[v].dt), dt_ratio_ci=q(r.dt), dt_ratio_ci_98_3=q(r.dt, 100 * 0.05 / 6, 100 * (1 - 0.05 / 6)),
        p_dt_ratio_le_1=float((r.dt <= 1).mean()),
        **{"ratio_ci|" + a: q(r[a]) for a in FRONT},
        **{"ratio_ci_bonf10|" + a: q(r[a], 0.25, 99.75) for a in [O46, G52, G53]},
        **{"p_ratio_ge_1|" + a: float((r[a] >= 1).mean()) for a in [O46, G52, G53]},
        **{a + "_ci": q(B[v][a]) for a in FRONT},
        opus46_over_opus45_ci=q(B[v][O46] / B[v][O45]),
        p_opus46_top=float((B[v][[O46, G52, G53, O45, "Gemini 3 Pro"]].idxmax(axis=1) == O46).mean()),
        p_opus45_above_gpt52=float((B[v][O45] > B[v][G52]).mean()),
        p_opus45_above_gpt53=float((B[v][O45] > B[v][G53]).mean()),
        p_opus45_above_both_gpt=float(((B[v][O45] > B[v][G52]) & (B[v][O45] > B[v][G53])).mean()),
    )
OUT["bootstrap"] = dict(n_boot=N_BOOT, seed0=SEED, unit="family->task->run (runs resampled jointly across variants)",
                        stats=bs)

# ---------------------------------------------------------------- token-budget attacks
nr = runs[runs.task_source != "SWAA"].copy()
nr["dur_h"] = (nr.completed_at - nr.started_at) / 3.6e6
nr["scaffold_last"] = nr.scaffold.str.split(",").str[-1]
budget = {}
for a, g in nr.groupby("alias"):
    u = g[g.fatal_error_from.eq("usageLimits")]
    budget[a] = dict(scaffold=sorted(g.scaffold_last.unique()), max_tokens_M=float(g.tok.max() / 1e6),
                     n_usage_stops=int(len(u)),
                     n_usage_stops_within_2pct_of_max=int((u.tok >= 0.98 * g.tok.max()).sum()),
                     usage_stop_tokens_M_median=float(u.tok.median() / 1e6) if len(u) else None,
                     usage_stop_hours_median=float(u.dur_h.median()) if len(u) else None,
                     usage_stops_scored_success=int(u.score_binarized.sum()))
OUT["budget_evidence"] = budget

# pacing: share of successes in the last quarter of the (inferred) budget
pace = {}
for a, bud in [(O45, 8e6), ("Gemini 3 Pro", 8e6), ("Claude 3.5 Sonnet (New) (Inspect)", 8e6), (O46, 16e6),
               (G52, 16e6), (G53, 16e6), ("GPT-5.1-Codex-Max (Inspect)", 16e6), ("o3 (Inspect)", 16e6)]:
    g = nr[nr.alias == a]
    s = g[g.score_binarized == 1]
    pace[a] = dict(assumed_budget_M=bud / 1e6, n_success=int(len(s)),
                   share_success_last_quarter=float((s.tok > 0.75 * bud).mean()),
                   share_success_over_half=float((s.tok > 0.5 * bud).mean()),
                   share_runs_last_quarter=float((g.tok > 0.75 * bud).mean()),
                   tokens_M_q50_q90_q99=[float(x / 1e6) for x in g.tok.quantile([.5, .9, .99])])
OUT["pacing"] = pace

# over-cap successes: is the over-cap success the only success on that task?
only = {}
for a in [O46, G52, G53, "GPT-5.1-Codex-Max (Inspect)", "o3 (Inspect)", "GPT-5 (Inspect)"]:
    g = runs[runs.alias == a]
    s = g[g.score_binarized == 1]
    t_over = set(s[s.tok > 8e6].task_id)
    t_under = set(s[s.tok <= 8e6].task_id)
    only_t = sorted(t_over - t_under)
    only[a] = dict(successes_over_8M=int((s.tok > 8e6).sum()), tasks_with_over_8M_success=len(t_over),
                   tasks_also_solved_under_8M=len(t_over & t_under), tasks_only_solved_over_8M=len(only_t),
                   only_over_by_source=meta.loc[only_t].source.value_counts().to_dict(),
                   only_over_median_minutes=float(meta.loc[only_t].minutes.median()) if only_t else None,
                   runs_on_only_over_tasks=int(g.task_id.isin(only_t).sum()),
                   successes_on_only_over_tasks=int(s.task_id.isin(only_t).sum()))
OUT["over_cap_only_success"] = only

# Opus 4.6's over-8M successes task by task, next to Opus 4.5 (8M budget) on the same task
o46 = runs[runs.alias == O46]
o45 = runs[runs.alias == O45]
tl = []
for t in sorted(o46[(o46.score_binarized == 1) & (o46.tok > 8e6)].task_id.unique()):
    x, y = o46[o46.task_id == t], o45[o45.task_id == t]
    tl.append(dict(task=t, source=meta.loc[t, "source"], minutes=float(meta.loc[t, "minutes"]),
                   opus46_success_all=f"{int(x.score_binarized.sum())}/{len(x)}",
                   opus46_success_le8M=f"{int(((x.score_binarized == 1) & (x.tok <= 8e6)).sum())}/{len(x)}",
                   opus46_over8M_successes=int(((x.score_binarized == 1) & (x.tok > 8e6)).sum()),
                   opus46_tokens_M_min_max=[float(x.tok.min() / 1e6), float(x.tok.max() / 1e6)],
                   opus45_success=f"{int(y.score_binarized.sum())}/{len(y)}", opus45_max_tokens_M=float(y.tok.max() / 1e6)))
OUT["opus46_over8M_tasks"] = tl
s46 = o46[(o46.score_binarized == 1) & (o46.tok > 8e6)]
OUT["opus46_over8M_successes_by_source"] = s46.task_source.value_counts().to_dict()

# Length-matched placebo: per agent, remove as many successes as the 8M cap removes, drawn at random
# from that agent's successes on tasks of >= 240 human minutes (where over-cap successes sit).
sc = runs[runs.score_binarized == 1]
m_rem = sc[sc.tok > 8e6].groupby("alias").size()
OUT["share_over8M_successes_on_ge240min"] = float((sc[sc.tok > 8e6].human_minutes >= 240).mean())
plc = []
key = pd.MultiIndex.from_frame(base[["agent", "task_id"]])
for i in range(200):
    rng = np.random.default_rng(90_000 + i)
    drop = []
    for a, m in m_rem.items():
        pool = sc[(sc.alias == a) & (sc.human_minutes >= 240)]
        drop.append(pool.iloc[rng.choice(len(pool), size=min(m, len(pool)), replace=False)])
    lost = pd.concat(drop).groupby(["alias", "task_id"]).size()
    lost.index.names = ["agent", "task_id"]
    p = p50s(base.assign(k=base.k.to_numpy() - lost.reindex(key).fillna(0).to_numpy()))
    plc.append(dict(dt_ratio=dt(p, SOTA) / dt(ref, SOTA), **{a: p[a] / ref[a] for a in [O46, G52, G53]}))
plc = pd.DataFrame(plc)
OUT["placebo_length_matched"] = {c: [float(plc[c].quantile(x)) for x in (0.025, 0.5, 0.975)] for c in plc.columns}

# within-task relation between tokens and success: mean over tasks with mixed outcomes of
# [mean log tokens of successes - mean log tokens of failures]; task-bootstrap CI
wt = {}
for a in [O46, O45, G52, G53, "Gemini 3 Pro", "o3 (Inspect)"]:
    for src in ["HCAST", "RE-Bench"]:
        g = nr[(nr.alias == a) & (nr.task_source == src) & (nr.tok > 0)]
        diffs = []
        for t, h in g.groupby("task_id"):
            if 0 < h.score_binarized.sum() < len(h):
                lt = np.log(h.tok)
                diffs.append(lt[h.score_binarized == 1].mean() - lt[h.score_binarized == 0].mean())
        diffs = np.array(diffs)
        rng = np.random.default_rng(5)
        bm = [rng.choice(diffs, len(diffs)).mean() for _ in range(2000)] if len(diffs) > 1 else [np.nan]
        wt[f"{a}|{src}"] = dict(n_mixed_tasks=len(diffs), mean_logtok_diff=float(diffs.mean()) if len(diffs) else None,
                                ratio=float(np.exp(diffs.mean())) if len(diffs) else None, ci_ratio=[float(np.exp(c)) if c is not None else None for c in q(bm)])
OUT["within_task_tokens_success_vs_failure"] = wt

# token rate by scaffold (are tokens comparable?): tokens per hour of wall-clock on HCAST runs that were
# not usage-stopped. Wall-clock includes waiting for tools/API, so this is only indicative.
h = nr[(nr.task_source == "HCAST") & nr.fatal_error_from.isna() & (nr.dur_h > 0.05)]
OUT["tokens_per_wallclock_hour_M"] = {a: dict(scaffold=g.scaffold_last.iloc[0], median=float((g.tok / g.dur_h).median() / 1e6))
                                      for a, g in h.groupby("alias")}

# ---------------------------------------------------------------- natural experiment: same model, two budgets
r10 = pd.read_json(R10, lines=True)
r10 = r10[(r10.alias != "human") & (r10.task_source != "SWAA")]
nat = {}
for a11, a10, cap in [("GPT-5 (Inspect)", "GPT-5", 8e6), ("GPT-5.1-Codex-Max (Inspect)", "GPT-5.1-Codex-Max", 16e6)]:
    x11 = runs[(runs.alias == a11) & (runs.task_source != "SWAA")]
    x10 = r10[r10.alias == a10].copy()
    x10["tok"] = x10.tokens_count.fillna(0)
    shared = sorted(set(x11.task_id) & set(x10.task_id))
    res = dict(th10_max_tokens_M=float(x10.tok.max() / 1e6), th11_max_tokens_M=float(x11.tok.max() / 1e6),
               n_shared_tasks=len(shared), th10_scaffold=str(x10.scaffold.iloc[0]), th11_scaffold=str(x11.scaffold.iloc[0]))
    fr = []
    for lab, d, c in [("th11_actual", x11, None), (f"th11_rescored_at_{cap/1e6:g}M", x11, cap),
                      ("th10_actual", x10, None), (f"th10_rescored_at_{cap/1e6:g}M", x10, cap)]:
        d = d[d.task_id.isin(shared)]
        s = d.score_binarized.eq(1) & ((d.tok <= c) if c else True)
        g = d.assign(s=s.astype(int)).groupby("task_id").agg(k=("s", "sum"), n=("s", "size")).reset_index().join(meta, on="task_id")
        g["agent"] = lab
        fr.append(g)
    g = pd.concat(fr)
    g["w"] = weights(g)
    p = p50s(g)
    sr = g.groupby("agent").apply(lambda z: np.average(z.k / z.n, weights=z.w), include_groups=False)
    res["p50"] = {k: float(v) for k, v in p.items()}
    res["weighted_success"] = {k: float(v) for k, v in sr.items()}
    nat[a11] = res
OUT["natural_experiment_th10_vs_th11"] = nat

# ---------------------------------------------------------------- R spot-check: HCAST-only DT
hc = base[base.source == "HCAST"].copy()
hc["w"] = weights(hc)
ph = p50s(hc)
OUT["R_spotcheck_hcast_only"] = dict(dt=dt(ph, SOTA), ratio=dt(ph, SOTA) / dt(ref, SOTA),
                                     opus46=float(ph[O46]), gpt52=float(ph[G52]))

(HERE / "validation.json").write_text(json.dumps(OUT, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
print(json.dumps({k: OUT[k] for k in ["counts_check", "cap8M_spare_rebench_point", "R_spotcheck_hcast_only"]}, indent=1))
print({k: v for k, v in OUT["claim1"].items() if k != "per_agent"})
print(json.dumps(OUT["bootstrap"]["stats"]["cap8"], indent=1))
