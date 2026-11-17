"""Step 3-4: data inventory and L1 confound checks (no stratified model outcomes).

- task source and human-time source against human minutes;
- elicitation against release date: scaffold, token budget (inferred from where usage-limit runs stop),
  usage-limit termination rate, runs per task;
- consistency of runs.jsonl with the published per-task counts.
Output: results/inventory.json
"""
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import RUNS_11, load_counts, save

runs = pd.read_json(RUNS_11, lines=True)
runs = runs[runs.alias != "human"].copy()
runs["scaffold"] = runs.scaffold.fillna("NA")
counts, dates = load_counts()

# 1. consistency: runs.jsonl vs task_results_1_1.yaml
rk = runs.groupby(["alias", "task_id"]).agg(k_runs=("score_binarized", "sum"), n_runs=("run_id", "size")).reset_index()
m = counts.merge(rk, left_on=["agent", "task_id"], right_on=["alias", "task_id"], how="inner")
consistency = dict(pairs_compared=len(m), agents=int(m.agent.nunique()),
                   k_mismatch=int((m.k != m.k_runs).sum()), n_mismatch=int((m.n != m.n_runs).sum()))

# 2. task source / human source vs length
tasks = counts.drop_duplicates("task_id")[["task_id", "family", "source", "human_source", "human_minutes"]]
bins = [0, 1, 4, 15, 60, 240, 480, 960, 4000]
tasks["bin"] = pd.cut(tasks.human_minutes, bins).astype(str)
ct = pd.crosstab(tasks.bin, [tasks.source, tasks.human_source])
by_src = tasks.groupby("source").human_minutes.agg(["count", "min", "median", "max"])
fam_src = tasks.groupby("source").family.nunique()
long = tasks[tasks.human_minutes >= 480]
est_round = tasks[tasks.human_source == "estimate"].human_minutes
base = tasks[tasks.human_source == "baseline"].human_minutes
inv_src = dict(
    n_tasks=len(tasks), n_families=int(tasks.family.nunique()),
    by_source={s: dict(n=int(r["count"]), min=r["min"], median=r["median"], max=r["max"],
                       families=int(fam_src[s])) for s, r in by_src.iterrows()},
    crosstab={str(k): {str(c): int(v) for c, v in row.items()} for k, row in ct.iterrows()},
    tasks_ge_480min=dict(n=len(long), estimated=int((long.human_source == "estimate").sum()),
                         by_source=long.source.value_counts().to_dict()),
    spearman_estimate_vs_minutes_hcast=float(spearmanr(
        tasks[tasks.source == "HCAST"].human_source.eq("estimate"),
        tasks[tasks.source == "HCAST"].human_minutes).statistic),
    median_minutes_hcast=dict(estimate=float(tasks[(tasks.source == "HCAST") & (tasks.human_source == "estimate")].human_minutes.median()),
                              baseline=float(tasks[(tasks.source == "HCAST") & (tasks.human_source == "baseline")].human_minutes.median())),
    estimates_whole_minutes=float((est_round % 1 == 0).mean()),
    baselines_whole_minutes=float((base % 1 == 0).mean()),
    swaa_overlap_hcast=int(((tasks.source == "HCAST") & (tasks.human_minutes <= tasks[tasks.source == "SWAA"].human_minutes.max())).sum()),
)

# 3. elicitation vs release date (non-SWAA runs; SWAA is single-turn)
nr = runs[runs.task_source != "SWAA"].copy()
nr["usage_limit"] = nr.fatal_error_from.eq("usageLimits")
lim = nr[nr.usage_limit].groupby("alias").tokens_count.median()
agents = []
for a, g in nr.groupby("alias"):
    stop_med = float(lim.get(a, np.nan) / 1e6) if a in lim else np.nan
    long_g = g[g.human_minutes >= 240]
    agents.append(dict(
        agent=a, date=str(dates[a].date()),
        scaffold=sorted({s.split(",")[-1] for s in g.scaffold}),
        max_tokens_M=float(g.tokens_count.max() / 1e6),  # largest run; the budget is at or just above this
        median_tokens_at_usage_stop_M=stop_med,
        share_success_runs_over_8M=float((g.score_binarized.eq(1) & (g.tokens_count > 8e6)).sum() / max(g.score_binarized.sum(), 1)),
        share_success_runs_over_1M=float((g.score_binarized.eq(1) & (g.tokens_count > 0.8e6)).sum() / max(g.score_binarized.sum(), 1)),
        usage_limit_rate=float(g.usage_limit.mean()),
        usage_limit_rate_ge240=float(long_g.usage_limit.mean()),
        median_tokens=float(g.tokens_count.median()),
        runs_per_task=float(g.groupby("task_id").size().mean()),
    ))
el = pd.DataFrame(agents).sort_values("date")
el["date_num"] = pd.to_datetime(el.date).map(pd.Timestamp.toordinal)
rho = {c: float(spearmanr(el.date_num, el[c], nan_policy="omit").statistic)
       for c in ["max_tokens_M", "share_success_runs_over_8M", "usage_limit_rate", "usage_limit_rate_ge240", "median_tokens", "runs_per_task"]}
pd.set_option("display.width", 200)
print(consistency)
print(by_src, "\n", ct)
print(inv_src["tasks_ge_480min"], inv_src["median_minutes_hcast"], inv_src["estimates_whole_minutes"], inv_src["baselines_whole_minutes"])
print(el.drop(columns="date_num").round(3).to_string())
print("spearman with release date:", rho)

save("inventory.json", dict(consistency=consistency, tasks=inv_src,
                            elicitation=el.drop(columns="date_num").to_dict(orient="records"),
                            spearman_with_date=rho))
