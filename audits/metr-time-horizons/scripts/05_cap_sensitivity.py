"""POST-HOC (not in prereg.md): sensitivity of the E3 token-cap result to its rescoring assumption.

E3 rescored every success above the cap as a failure. Two weaker assumptions:
  (a) do not rescore RE-Bench runs (their score is the best result reached during the run, which may
      have been reached before the cap);
  (b) do not rescore runs that ended by usage limit but were scored a success (same reason).
Also a cap at 4M and 12M to show the dose-response. Point estimates and a 300-draw family bootstrap.
Output: results/cap_sensitivity.json
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import RUNS_11, doubling_time, fit_agents, invsqrt_weights, load_counts, save, sota_agents

FRONTIER = ["Claude Opus 4.6 (Inspect)", "GPT-5.2", "GPT-5.3-Codex", "Claude Opus 4.5 (Inspect)", "Gemini 3 Pro"]
N_BOOT, SEED0 = 300, 3000

counts, dates = load_counts()
counts["x"] = np.log2(counts.human_minutes)
runs = pd.read_json(RUNS_11, lines=True)
runs = runs[runs.alias != "human"].copy()
runs["tokens_count"] = runs.tokens_count.fillna(0)
agents = sorted(runs.alias.unique())
base = counts[counts.agent.isin(agents)].copy()
base["w"] = invsqrt_weights(base)
ref = fit_agents(base)
SOTA = sota_agents(ref.p50, dates)

RULES = {
    "cap8M_all": lambda r: r.tokens_count > 8e6,
    "cap8M_not_rebench": lambda r: (r.tokens_count > 8e6) & (r.task_source != "RE-Bench"),
    "cap8M_not_usage_stopped": lambda r: (r.tokens_count > 8e6) & r.fatal_error_from.ne("usageLimits"),
    "cap4M_all": lambda r: r.tokens_count > 4e6,
    "cap12M_all": lambda r: r.tokens_count > 12e6,
}
lost = {}
for name, rule in RULES.items():
    l = runs[(runs.score_binarized == 1) & rule(runs)].groupby(["alias", "task_id"]).size().rename(name)
    lost[name] = l
L = pd.concat(lost.values(), axis=1).fillna(0).astype(int).reset_index().rename(columns={"alias": "agent"})
base = base.merge(L, on=["agent", "task_id"], how="left").fillna({n: 0 for n in RULES})


def fits_for(d):
    res = {"reference": fit_agents(d)}
    for n in RULES:
        res[n] = fit_agents(d.assign(k=d.k - d[n]))
    return res


def summ(f):
    return dict(dt=doubling_time(f.p50, dates, SOTA), **{a: float(f.p50[a]) for a in FRONTIER})


point = {n: summ(f) for n, f in fits_for(base).items()}

by_task = {t: g for t, g in base.groupby("task_id")}
fam_tasks = base.drop_duplicates("task_id").groupby("family").task_id.apply(list)
boot = {n: [] for n in point}
for i in range(N_BOOT):
    rng = np.random.default_rng(SEED0 + i)
    draw = []
    for f in rng.choice(len(fam_tasks), size=len(fam_tasks), replace=True):
        tl = fam_tasks.iloc[f]
        draw += [tl[j] for j in rng.choice(len(tl), size=len(tl), replace=True)]
    b = pd.concat([by_task[t] for t in draw], ignore_index=True)  # tasks only; runs not resampled here
    for n, f in fits_for(b).items():
        boot[n].append(summ(f))
out = {"note": "post-hoc; task-level bootstrap (runs not resampled)", "n_boot": N_BOOT, "variants": {}}
R = pd.DataFrame(boot["reference"])
for n in point:
    B = pd.DataFrame(boot[n])
    out["variants"][n] = {
        k: dict(point=point[n][k], ratio=point[n][k] / point["reference"][k],
                ratio_ci=[float((B[k] / R[k]).quantile(0.025)), float((B[k] / R[k]).quantile(0.975))])
        for k in point[n]}
    out["variants"][n]["successes_removed"] = int(base[n].sum()) if n in RULES else 0
save("cap_sensitivity.json", out)
for n, v in out["variants"].items():
    print(n, v.get("successes_removed"), {k: (round(x["point"], 1), round(x["ratio"], 3), np.round(x["ratio_ci"], 3).tolist())
                                          for k, x in v.items() if k != "successes_removed"})
