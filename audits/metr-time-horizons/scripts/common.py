"""Shared loaders and a re-implementation of METR's time-horizon fit.

Re-implemented from the pinned METR/eval-analysis-public code (read as text, never run):
  - src/horizon/utils/logistic.py:7-55   weighted logistic of success on log2(human_minutes),
                                          sklearn LogisticRegression(C=1/regularization)
  - reports/time-horizon-1-1/fig_params/figs.yaml:73-82  weighting invsqrt_task_weight,
                                          regularization 1e-5, bootstrap categories f,t,r
  - src/horizon/compute_task_weights.py:15-56  run weight = 1/(n_runs_in_task*sqrt(n_tasks_in_family)),
                                          normalised to sum 1 per agent
  - src/horizon/wrangle/bootstrap.py:72-176  hierarchical bootstrap family -> task -> run;
                                          weights are carried, not renormalised
  - src/horizon/plot/bootstrap_ci.py:429-506  doubling time = ln2 / slope of OLS(ln p50 ~ date)
                                          over SOTA agents (running max of p50 by release date)

Data: per-task success counts for 23 agents from METR's published task_results_1_1.yaml, joined
to task family / source / human_source from runs.jsonl at the pinned repo commit.
All randomness takes an explicit seed.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPO = DATA / "eval-analysis-public"
RUNS_11 = REPO / "reports/time-horizon-1-1/data/raw/runs.jsonl"
RUNS_10 = REPO / "reports/time-horizon-1-0/data/raw/runs.jsonl"
REL_DATES = REPO / "data/external/release_dates.yaml"
PUB_BENCH = DATA / "published/benchmark_results_1_1.yaml"
PUB_TASKS = DATA / "published/task_results_1_1.yaml"
RESULTS = ROOT / "results"
REG = 1e-5  # figs.yaml:79
C = 1.0 / REG
SIXTEEN_H = 16 * 60  # benchmark_results_1_1.yaml: doubling time "excludes points with central estimate p50 > 16 hrs"


def load_task_meta() -> pd.DataFrame:
    d = pd.read_json(RUNS_11, lines=True)
    d = d[d.alias != "human"]
    t = d.groupby("task_id").agg(
        family=("task_family", "first"),
        source=("task_source", "first"),
        human_source=("human_source", "first"),
        human_minutes=("human_minutes", "first"),
    )
    return t.reset_index()


def load_counts() -> tuple[pd.DataFrame, dict]:
    """Long table: agent, task_id, k (successes), n (runs), plus task metadata; and agent dates."""
    pub = yaml.safe_load(PUB_TASKS.read_text())
    rows, dates = [], {}
    for agent, v in pub["agents"].items():
        dates[agent] = pd.Timestamp(str(v["release_date"]))
        for t in v["tasks"]:
            rows.append((agent, t["task_id"], t["n_successes"], t["n_runs"], t["human_minutes"]))
    df = pd.DataFrame(rows, columns=["agent", "task_id", "k", "n", "hm_pub"])
    meta = load_task_meta()
    df = df.merge(meta, on="task_id", how="left", validate="many_to_one")
    assert df.family.notna().all(), "task without metadata"
    # task_results_1_1.yaml rounds minutes to 3 dp; use runs.jsonl values (differ only for SWAA rounding)
    assert np.allclose(df.hm_pub, df.human_minutes, atol=6e-4), "human minutes disagree beyond rounding"
    return df, dates


def invsqrt_weights(df: pd.DataFrame) -> pd.Series:
    """Per-task total weight for each agent (sum over its runs), normalised to 1 per agent.

    Run weight = 1/(n_runs*sqrt(F)), so a task's total = 1/sqrt(F); F = tasks in family for that agent.
    Families are counted within whatever subset df holds (as METR recompute weights per file).
    """
    fam_size = df.groupby(["agent", "family"]).task_id.transform("count")
    w = 1.0 / np.sqrt(fam_size)
    return w / w.groupby(df.agent).transform("sum")


def fit_logistic(x, k, n, wtask, c=C, iters=100):
    """Weighted logistic, intercept unpenalised, slope penalised 0.5*b^2/c (sklearn lbfgs convention).

    Rows are tasks; each task carries k successes and n-k failures, each run weighted wtask/n.
    Returns (intercept, slope) on log2 minutes.
    """
    x = np.asarray(x, float)
    k = np.asarray(k, float)
    n = np.asarray(n, float)
    w = np.where(n > 0, np.asarray(wtask, float) / np.maximum(n, 1), 0.0)
    ws, wf = w * k, w * (n - k)  # weight on y=1 rows and y=0 rows
    wt = ws + wf
    a, b = 0.0, 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(a + b * x)))
        g0 = np.sum(ws - wt * p)
        g1 = np.sum((ws - wt * p) * x) - b / c
        h = wt * p * (1 - p)
        H = np.array([[h.sum(), (h * x).sum()], [(h * x).sum(), (h * x * x).sum() + 1 / c]])
        step = np.linalg.solve(H + 1e-12 * np.eye(2), np.array([g0, g1]))
        a, b = a + step[0], b + step[1]
        if np.max(np.abs(step)) < 1e-10:
            break
    return a, b


def horizon(a, b, q=0.5):
    """Minutes at which predicted success = q (utils/logistic.py:58)."""
    return float(np.exp2((np.log(q / (1 - q)) - a) / b))


def fit_agents(df: pd.DataFrame, weight_col="w", x_col="x") -> pd.DataFrame:
    out = []
    for agent, g in df.groupby("agent", sort=False):
        if g.k.sum() == 0 or g.k.sum() == g.n.sum():
            out.append((agent, np.nan, np.nan, np.nan, np.nan))
            continue
        a, b = fit_logistic(g[x_col], g.k, g.n, g[weight_col])
        out.append((agent, a, b, horizon(a, b, 0.5), horizon(a, b, 0.8)))
    return pd.DataFrame(out, columns=["agent", "intercept", "slope", "p50", "p80"]).set_index("agent")


def sota_agents(p50: pd.Series, dates: dict, after="2023-01-01", before="2030-01-01", max_p50=SIXTEEN_H):
    """bootstrap_ci.py:448-506 plus the >16h exclusion stated in the published yaml."""
    rows = [(a, dates[a], v) for a, v in p50.items() if np.isfinite(v)]
    df = pd.DataFrame(rows, columns=["agent", "date", "p50"]).sort_values("date")
    df = df[(df.date >= pd.Timestamp(after)) & (df.date < pd.Timestamp(before))]
    keep, best = [], -np.inf
    for d, g in df.groupby("date", sort=True):
        best = max(best, g.p50.max())
        keep += [a for a, v in zip(g.agent, g.p50) if v >= best]
    if max_p50 is not None:
        keep = [a for a in keep if p50[a] <= max_p50]
    return keep


def doubling_time(p50: pd.Series, dates: dict, agents: list) -> float:
    """ln2 / OLS slope of ln(p50) on days (plot/logistic.py:410-436, bootstrap_ci.py:429-445)."""
    y = np.array([p50[a] for a in agents], float)
    x = np.array([(dates[a] - pd.Timestamp("1970-01-01")).days for a in agents], float)
    ok = np.isfinite(y) & (y >= 1e-3)
    if ok.sum() < 2:
        return np.nan
    slope = np.polyfit(x[ok], np.log(np.clip(y[ok], 1e-3, None)), 1)[0]
    return float(np.log(2) / slope)


def bootstrap_index(df: pd.DataFrame, rng: np.random.Generator, cluster="family"):
    """Hierarchical resample family -> task (bootstrap.py:72-176). Returns list of task_id draws.

    The same task draw is shared by all agents, as in METR's code (resampling is done on the
    whole run table before the per-agent fits).
    """
    fam_tasks = df.drop_duplicates("task_id").groupby(cluster).task_id.apply(list)
    fams = fam_tasks.index.to_numpy()
    draw = []
    for f in rng.choice(len(fams), size=len(fams), replace=True):
        tasks = fam_tasks.iloc[f]
        draw += [tasks[i] for i in rng.choice(len(tasks), size=len(tasks), replace=True)]
    return draw


def bootstrap_fits(df: pd.DataFrame, n_boot: int, seed: int, weight_col="w", runs=True, cluster="family",
                   extra=None):
    """Returns DataFrame (n_boot x agents) of p50 and of p80; extra(df_boot) may return a dict per draw."""
    by_task = {t: g for t, g in df.groupby("task_id")}
    p50s, p80s, extras = [], [], []
    for i in range(n_boot):
        rng = np.random.default_rng(seed + i)
        draw = bootstrap_index(df, rng, cluster)
        b = pd.concat([by_task[t] for t in draw], ignore_index=True)
        if runs:  # resample runs within task-agent = binomial with the observed rate
            b = b.copy()
            b["k"] = rng.binomial(b.n.to_numpy(), np.where(b.n > 0, b.k / b.n.clip(lower=1), 0))
        f = fit_agents(b, weight_col=weight_col)
        p50s.append(f.p50)
        p80s.append(f.p80)
        if extra is not None:
            extras.append(extra(b))
    return pd.DataFrame(p50s).reset_index(drop=True), pd.DataFrame(p80s).reset_index(drop=True), extras


def doubling_ci(p50_boot: pd.DataFrame, dates: dict, agents: list):
    dts = []
    for _, r in p50_boot.iterrows():
        dt = doubling_time(r, dates, [a for a in agents if a in r.index and np.isfinite(r[a]) and r[a] >= 1e-3])
        if np.isfinite(dt) and dt > 0:
            dts.append(dt)
    dts = np.array(dts)
    return float(np.percentile(dts, 2.5)), float(np.percentile(dts, 97.5)), dts


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["x"] = np.log2(df.human_minutes)
    df["w"] = invsqrt_weights(df)
    return df


def save(name: str, obj) -> None:
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / name).write_text(json.dumps(obj, indent=2, default=float))
