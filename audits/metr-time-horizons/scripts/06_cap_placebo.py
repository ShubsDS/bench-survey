"""POST-HOC placebo for E3: remove, per agent, as many successes as the 8M cap removes, but chosen at
random among that agent's successful runs (ignoring tokens). If the cap's effect were just "fewer
successes for recent models", this placebo would move horizons and the DT as much as the cap does.
Output: results/cap_placebo.json
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import RUNS_11, doubling_time, fit_agents, invsqrt_weights, load_counts, save, sota_agents

FRONTIER = ["Claude Opus 4.6 (Inspect)", "GPT-5.2", "GPT-5.3-Codex"]
counts, dates = load_counts()
counts["x"] = np.log2(counts.human_minutes)
runs = pd.read_json(RUNS_11, lines=True)
runs = runs[runs.alias != "human"].copy()
runs["tokens_count"] = runs.tokens_count.fillna(0)
base = counts[counts.agent.isin(runs.alias.unique())].copy()
base["w"] = invsqrt_weights(base)
ref = fit_agents(base)
SOTA = sota_agents(ref.p50, dates)
ref_dt = doubling_time(ref.p50, dates, SOTA)

succ = runs[runs.score_binarized == 1]
n_remove = succ[succ.tokens_count > 8e6].groupby("alias").size()
key = base.set_index(["agent", "task_id"]).index
res = []
for i in range(200):
    rng = np.random.default_rng(40_000 + i)
    drop = []
    for a, m in n_remove.items():
        s = succ[succ.alias == a]
        drop.append(s.iloc[rng.choice(len(s), size=m, replace=False)])
    lost = pd.concat(drop).groupby(["alias", "task_id"]).size()
    lost.index.names = ["agent", "task_id"]
    k = base.k.to_numpy() - lost.reindex(key).fillna(0).to_numpy()
    f = fit_agents(base.assign(k=k))
    res.append(dict(dt_ratio=doubling_time(f.p50, dates, SOTA) / ref_dt,
                    **{a: f.p50[a] / ref.p50[a] for a in FRONTIER}))
r = pd.DataFrame(res)
out = {"n": len(r), "removed_per_agent": n_remove.to_dict(),
       "quantiles": {c: [float(r[c].quantile(q)) for q in (0.025, 0.5, 0.975)] for c in r.columns}}
save("cap_placebo.json", out)
print(out)
