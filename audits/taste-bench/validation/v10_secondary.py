"""V9: secondary claims C5-C8 re-derived from the summaries, the paper's tables and the data."""
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import AUD, CELLS, DATA, average, load, save, summaries  # noqa: E402

S = summaries()
rows = load()
N = {c: sum(r["cell"] == c for r in rows) for c in CELLS}
acc = {m: {c: s["per_cell"][c]["both_correct_rate"] * 100 for c in CELLS} for m, s in S.items()}
avg = {m: average({c: acc[m][c] / 100 for c in CELLS}, N)[0] * 100 for m in S}
out = {}

# C5: detour vs parallel per domain
for dom in ("engineering", "research"):
    d = [acc[m][f"detour_{dom}"] - acc[m][f"parallel_{dom}"] for m in S]
    out[f"C5_{dom}"] = {"model_mean_detour_minus_parallel": round(float(np.mean(d)), 2),
                        "models_detour_lower": int(sum(x < 0 for x in d)), "n_models": len(d),
                        "mean_P": round(float(np.mean([acc[m][f'parallel_{dom}'] for m in S])), 1),
                        "mean_D": round(float(np.mean([acc[m][f'detour_{dom}'] for m in S])), 1)}
out["C5_top2_research_detour_minus_parallel"] = {m: round(acc[m]["detour_research"] - acc[m]["parallel_research"], 1)
                                                 for m in ("gpt-5.6-sol", "gpt-5.5")}

# C6: adjacent gaps, repeat-run pair, task concentration
order = sorted(S, key=lambda m: -avg[m])
gaps = [round(avg[a] - avg[b], 2) for a, b in zip(order, order[1:])]
pooled = {m: S[m]["overall"]["both_correct"] / 502 * 100 for m in S}
pgaps = [round(abs(pooled[a] - pooled[b]), 2) for a, b in zip(order, order[1:])]
rerun = 58.2 - 55.6  # paper: main run pooled (CC 292/502) vs effort rerun xhigh (Table 8)
out["C6"] = {"sol_main_pooled": round(pooled["gpt-5.6-sol"], 2), "sol_rerun_xhigh_pooled_table8": 55.6,
             "rerun_diff": round(rerun, 2), "adjacent_average_gaps": gaps,
             "average_gaps_below_rerun_diff": int(sum(g < round(rerun, 2) - 1e-9 for g in gaps)),
             "average_gaps_equal_rerun_diff_at_1dp": int(sum(abs(round(g, 1) - 2.6) < 1e-9 for g in gaps)),
             "adjacent_pooled_gaps": pgaps,
             "pooled_gaps_below_rerun_diff": int(sum(g < rerun for g in pgaps)),
             "sol_main_reasoning_tokens_per_presentation": round(S["gpt-5.6-sol"]["usage"]["reasoning_tokens"] / 1004, 1),
             "gpt55_main_reasoning_tokens_per_presentation": round(S["gpt-5.5"]["usage"]["reasoning_tokens"] / 1004, 1)}
res = [r for r in rows if r["domain"] == "research"]
tc = Counter(r["task_id"] for r in res)
top, k = tc.most_common(1)[0]
out["C6"]["research_top_task_items"] = k
out["C6"]["research_top_task_by_cell"] = dict(Counter(r["cell"] for r in res if r["task_id"] == top))
out["C6"]["research_top_task_average_weight_points"] = round(k / 112 * 50, 1)
out["C6"]["research_tasks"] = len(tc)
out["C6"]["research_top3_tasks_items"] = sum(v for _, v in tc.most_common(3))


# research-domain interval for one model's accuracy, task-cluster design effect from Haiku H1 ICC
def haiku_scores(cond):
    sc = defaultdict(list)
    for l in (DATA / f"haiku_{cond}.jsonl").read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            sc[r["id"]].append(bool(r.get("ok")))
    return {i: float(all(v)) for i, v in sc.items()}  # paired correctness


hs = haiku_scores("H1")
tid = {r["id"]: r["task_id"] for r in rows}
# Haiku paired accuracy in research with a task bootstrap vs item bootstrap
rng = np.random.default_rng(1)
rid = [r["id"] for r in res]
by = defaultdict(list)
for i in rid:
    by[tid[i]].append(hs[i])
tasks = sorted(by)
tb = [np.mean([x for t in rng.choice(tasks, len(tasks)) for x in by[t]]) for _ in range(2000)]
ib = [np.mean(rng.choice([hs[i] for i in rid], len(rid))) for _ in range(2000)]
out["C6"]["haiku_H1_research_paired"] = round(float(np.mean([hs[i] for i in rid])) * 100, 1)
out["C6"]["haiku_H1_research_halfwidth_task_boot"] = round(float(np.percentile(tb, 97.5) - np.percentile(tb, 2.5)) / 2 * 100, 1)
out["C6"]["haiku_H1_research_halfwidth_item_boot"] = round(float(np.percentile(ib, 97.5) - np.percentile(ib, 2.5)) / 2 * 100, 1)
# drop the top task: Haiku research accuracy change
rest = [hs[i] for i in rid if tid[i] != top]
out["C6"]["haiku_H1_research_without_top_task"] = round(float(np.mean(rest)) * 100, 1)

# C7: horizon composition (paper tables: counts per level x cell; model-mean cell accuracy)
counts = {"parallel_engineering": [72, 45, 4, 3], "parallel_research": [11, 13, 3, 21],
          "detour_engineering": [69, 128, 36, 33], "detour_research": [6, 33, 13, 12]}
mm = {c: float(np.mean([acc[m][c] for m in S])) for c in CELLS}
pred = [sum(counts[c][l] * mm[c] for c in CELLS) / sum(counts[c][l] for c in CELLS) for l in range(4)]
obs = [62.3, 42.9, 31.5, 21.0]
more_work = [23.2, 21.7, 36.2, 24.6, 20.3, 26.1, 26.1, 14.5, 26.1, 17.4, 18.8, 15.9, 18.8, 4.3]  # Table 7
out["C7"] = {"model_mean_cell_acc": {c: round(v, 1) for c, v in mm.items()},
             "predicted_by_level": [round(p, 1) for p in pred], "observed_by_level": obs,
             "predicted_gap": round(pred[0] - pred[3], 1), "observed_gap": round(obs[0] - obs[3], 1),
             "models_below_25_more_work": int(sum(x < 25 for x in more_work)),
             "binomial_sd_one_model_69_items_at_25pct": round(float(np.sqrt(0.25 * 0.75 / 69)) * 100, 1)}

# C8: SWE-bench correlation (figure values read by the auditor; checked against paper statements)
sw = json.loads((AUD / "results/swebench_from_figure.json").read_text())
ms = [m for m in sw if not m.startswith("_")]
x = np.array([sw[m]["swebench_verified"] for m in ms])
y = np.array([avg[m] for m in ms])
eng = np.array([average({c: acc[m][c] / 100 for c in CELLS}, N)[1]["engineering"] * 100 for m in ms])
r_all = float(np.corrcoef(x, y)[0, 1])
keep = [i for i, m in enumerate(ms) if m not in ("gpt-5.6-sol", "gpt-5.5")]
r_drop = float(np.corrcoef(x[keep], y[keep])[0, 1])
drops = [float(np.corrcoef(np.delete(x, list(c)), np.delete(y, list(c)))[0, 1])
         for c in itertools.combinations(range(len(ms)), 2)]
sw_rank = sorted(ms, key=lambda m: -sw[m]["swebench_verified"])
top4 = sw_rank[:4]
out["C8"] = {"r_all": round(r_all, 3), "r_eng": round(float(np.corrcoef(x, eng)[0, 1]), 3),
             "r_without_sol_and_gpt55": round(r_drop, 3),
             "percentile_among_55_drop_two": round(float(np.mean(np.array(drops) <= r_drop)) * 100, 1),
             "gpt55_swe_rank": sw_rank.index("gpt-5.5") + 1, "deepseek_swe_rank": sw_rank.index("deepseek-v4-flash") + 1,
             "top4_swe_spread": round(float(sw[top4[0]]["swebench_verified"] - sw[top4[3]]["swebench_verified"]), 2),
             "top4_average_spread": round(float(max(avg[m] for m in top4) - min(avg[m] for m in top4)), 1)}
slope, icpt = np.polyfit(x, y, 1)
out["C8"]["residuals"] = {m: round(float(y[i] - (slope * x[i] + icpt)), 1) for i, m in enumerate(ms)}

# C10 human-review arithmetic: agreement on the 15 undecidable-removed items depends on retained count
out["C10_human"] = {"retained_total": 172, "disagreements_total": 2,
                    "agreement_lower_bound_if_k_retained_on_removed_items":
                        {k: round((k - 2) / k * 100, 1) for k in (4, 10, 20, 26, 30)}}
out["C10_e2e"] = {"14.6_of_41": round(6 / 41 * 100, 1), "39.0_of_41": round(16 / 41 * 100, 1),
                  "33.7_nearest_k_of_41": [round(13 / 41 * 100, 1), round(14 / 41 * 100, 1)],
                  "33.7_as_k_of_123": round(41.5 / 123 * 100, 1)}
save("v10_secondary.json", out)
print(json.dumps(out, indent=1))
