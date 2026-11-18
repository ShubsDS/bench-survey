"""Part A of prereg.md: every test that runs on released aggregates.

Inputs: data/repo/results/*/summary.json (repo commit b636e868), paper_numbers.py,
results/swebench_from_figure.json (from read_figures.py). Output: results/part_a.json.
Run: data/.venv/bin/python -I scripts/a_aggregate.py
"""
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import paper_numbers as P  # noqa: E402

PUBLISHED = {  # README leaderboard at b636e868: Average, D-Eng, D-Res, P-Eng, P-Res, Unparsed
    "gpt-5.6-sol": (59.7, 48.1, 67.2, 75.8, 56.2, 0), "gpt-5.5": (59.5, 47.4, 68.8, 73.4, 56.2, 0),
    "claude-opus-5": (55.5, 35.3, 64.1, 71.0, 64.6, 0), "grok-4.5": (54.6, 47.7, 57.8, 61.3, 56.2, 10),
    "gpt-5.6-terra": (54.0, 40.6, 57.8, 70.2, 58.3, 0), "glm-5.2": (53.9, 40.2, 59.4, 64.5, 60.4, 17),
    "claude-sonnet-5": (51.6, 36.1, 60.9, 62.1, 56.2, 0), "gpt-5.6-luna": (49.0, 32.3, 57.8, 67.7, 50.0, 0),
    "minimax-m3": (45.3, 34.6, 39.1, 64.5, 56.2, 3), "deepseek-v4-flash": (43.3, 29.3, 46.9, 58.1, 50.0, 2),
    "gpt-5.4-mini": (40.1, 25.2, 54.7, 26.6, 54.2, 112), "mistral-medium-3.5": (37.7, 40.6, 28.1, 43.5, 41.7, 24),
    "gpt-5.4-nano": (36.6, 25.6, 39.1, 46.0, 43.8, 93), "grok-4.20-reasoning": (15.7, 19.9, 9.4, 28.2, 8.3, 459),
}
ORDER = list(PUBLISHED)  # published rank order
DOMAINS = {"engineering": ("detour_engineering", "parallel_engineering"),
           "research": ("detour_research", "parallel_research")}


def load():
    out = {}
    for path in sorted((ROOT / "data/repo/results").glob("*/summary.json")):
        out[path.parent.name] = json.loads(path.read_text())
    return out


def average(cc, n):
    """cc, n: dict cell -> count. Headline Average = mean of item-weighted domain rates."""
    doms = [sum(cc[c] for c in cs) / sum(n[c] for c in cs) for cs in DOMAINS.values()]
    return 100 * sum(doms) / 2, [100 * d for d in doms]


def pearson(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def main():
    S = load()
    R = {}

    # A1 reproduce ------------------------------------------------------------------
    a1, worst = {}, 0.0
    for m in ORDER:
        pc = S[m]["per_cell"]
        cc = {c: pc[c]["both_correct"] for c in pc}
        n = {c: pc[c]["seeded"]["n"] for c in pc}
        avg, (eng, res) = average(cc, n)
        cells = [100 * pc[c]["both_correct_rate"] for c in
                 ("detour_engineering", "detour_research", "parallel_engineering", "parallel_research")]
        unp = sum(S[m]["overall"][o]["unparsed"] + S[m]["overall"][o]["errors"] for o in ("seeded", "reversed"))
        mine = [avg, *cells, unp]
        diff = max(abs(a - b) for a, b in zip(mine[:5], PUBLISHED[m][:5]))
        worst = max(worst, diff)
        a1[m] = {"average": round(avg, 2), "eng": round(eng, 2), "res": round(res, 2),
                 "cells": [round(c, 1) for c in cells], "unparsed_plus_errors": unp,
                 "errors": sum(S[m]["overall"][o]["errors"] for o in ("seeded", "reversed")),
                 "max_abs_diff_vs_published": round(diff, 3), "unparsed_match": unp == PUBLISHED[m][5],
                 "truncated_presentations": S[m]["input"]["truncated_presentations"],
                 "pooled_both_correct": S[m]["overall"]["both_correct"]}
    R["A1_reproduce"] = {"rows": a1, "max_abs_diff": round(worst, 3),
                         "holds": worst <= 0.05 and all(v["unparsed_match"] for v in a1.values())}

    # A2 unparsed bucket -------------------------------------------------------------
    a2 = {}
    for m in ORDER:
        pc = S[m]["per_cell"]
        cc, n, klo, khi, single = {}, {}, {}, {}, {}
        for c, b in pc.items():
            nn = b["seeded"]["n"]
            bs, br = nn - b["seeded"]["parsed"], nn - b["reversed"]["parsed"]
            cc[c], n[c] = b["both_correct"], nn
            klo[c], khi[c] = max(bs, br), min(nn - b["both_correct"], bs + br)
            parsed = b["seeded"]["parsed"] + b["reversed"]["parsed"]
            single[c] = round(100 * (b["seeded"]["correct"] + b["reversed"]["correct"]) / parsed, 1) if parsed else None
        lo, _ = average(cc, {c: n[c] - klo[c] for c in n})
        hi, _ = average(cc, {c: n[c] - khi[c] for c in n})
        par = sum(pc[c]["seeded"]["parsed"] + pc[c]["reversed"]["parsed"] for c in pc)
        cor = sum(pc[c]["seeded"]["correct"] + pc[c]["reversed"]["correct"] for c in pc)
        a2[m] = {"published_average": PUBLISHED[m][0], "parsed_only_average_bounds": [round(lo, 1), round(hi, 1)],
                 "single_order_acc_parsed_by_cell": single,
                 "single_order_acc_all": round(100 * cor / 1004, 1),
                 "single_order_acc_parsed": round(100 * cor / par, 1),
                 "unparsed_by_cell": {c: (pc[c]["seeded"]["n"] * 2 - pc[c]["seeded"]["parsed"] - pc[c]["reversed"]["parsed"]) for c in pc}}
    moves = []
    for i, m in enumerate(ORDER):
        lo = a2[m]["parsed_only_average_bounds"][0]
        passed = [ORDER[j] for j in range(i - 1) if PUBLISHED[ORDER[j]][0] < lo]  # >=2 places above
        if passed:
            moves.append({"model": m, "lower_bound": lo, "passes_models_ranked_2plus_above": passed})
        nearer = [ORDER[j] for j in range(i) if PUBLISHED[ORDER[j]][0] < lo]
        a2[m]["passes_published_models_above"] = nearer
    below_chance = {m: a2[m]["parsed_only_average_bounds"] for m in ORDER if PUBLISHED[m][0] < 25}
    below50 = {m: {c: v for c, v in a2[m]["single_order_acc_parsed_by_cell"].items() if v is not None and v < 50}
               for m in ORDER}
    R["A2_unparsed"] = {"per_model": a2, "moves_2plus": moves, "published_below_25": below_chance,
                        "cells_below_50_single_order_parsed": {m: v for m, v in below50.items() if v},
                        "changes": bool(moves) or any(b[0] > 25 for b in below_chance.values())}

    # A2b below-chance cells: single-order parsed accuracy with a task-cluster CI, and CC vs WW
    tasks = {c: v["tasks"] for c, v in P.CELL_SIZES.items()}
    a2b = {}
    for m in ORDER:
        for c, b in S[m]["per_cell"].items():
            parsed = b["seeded"]["parsed"] + b["reversed"]["parsed"]
            acc = (b["seeded"]["correct"] + b["reversed"]["correct"]) / parsed
            se = math.sqrt(acc * (1 - acc) / tasks[c])  # conservative: one effective draw per task
            po = b["paired_outcomes"]
            a2b.setdefault(c, {})[m] = {"single_parsed": round(100 * acc, 1),
                                        "ci95_task_conservative": [round(100 * (acc - 1.96 * se), 1), round(100 * (acc + 1.96 * se), 1)],
                                        "CC": po["CC"], "WW": po["WW"], "CW+WC": po["CW"] + po["WC"]}
    R["A2b_below_chance"] = {
        "by_cell": a2b,
        "ci_excludes_50_below": {c: [m for m, v in d.items() if v["ci95_task_conservative"][1] < 50] for c, d in a2b.items()},
        "point_below_50": {c: [m for m, v in d.items() if v["single_parsed"] < 50] for c, d in a2b.items()},
        "WW_gt_CC": {c: [m for m, v in d.items() if v["WW"] > v["CC"]] for c, d in a2b.items()},
    }

    # A3 options-only signal --------------------------------------------------------
    fun = {c: {"rubric": a, "survive_trivial": b, "released": r,
               "dropped_trivial_share": round(100 * (a - b) / a, 1),
               "dropped_undecidable_share_of_survivors": round(100 * (b - r) / b, 1)}
           for c, (a, b, r) in P.FUNNEL.items()}
    tot = [sum(v[i] for v in P.FUNNEL.values()) for i in range(3)]
    gpt41 = P.JUDGES_PENG["GPT-4.1"][1]
    peng = {m: round(100 * S[m]["per_cell"]["parallel_engineering"]["two_order_mean_accuracy"], 1) for m in ORDER}
    peng_parsed = {m: a2[m]["single_order_acc_parsed_by_cell"]["parallel_engineering"] for m in ORDER}
    R["A3_options_only"] = {
        "funnel": fun, "totals": tot, "unanimous_options_only_share_of_rubric_passing": round(100 * (tot[0] - tot[1]) / tot[0], 1),
        "judges_parallel_engineering": P.JUDGES_PENG, "judge_mean_released": round(sum(v[1] for v in P.JUDGES_PENG.values()) / 4, 1),
        "gpt41_options_only_released_peng": gpt41,
        "model_peng_single_order_mean_all": peng, "model_peng_single_order_parsed": peng_parsed,
        "models_at_or_below_gpt41": [m for m in ORDER if peng[m] <= gpt41],
        "models_at_or_below_gpt41_parsed": [m for m in ORDER if peng_parsed[m] <= gpt41],
    }

    # A4 test-retest ----------------------------------------------------------------
    lev_n = [sum(v[i] for v in P.HORIZON_COUNTS.values()) for i in range(4)]
    main_levels = P.HORIZON_ACC["gpt-5.6-sol"]
    main_pooled_from_levels = sum(a * k for a, k in zip(main_levels, lev_n)) / 502
    main_pooled = 100 * S["gpt-5.6-sol"]["overall"]["both_correct_rate"]
    rerun = P.EFFORT[("gpt-5.6-sol", "xhigh")]
    diff = main_pooled - rerun[0]
    gaps = [round(PUBLISHED[ORDER[i]][0] - PUBLISHED[ORDER[i + 1]][0], 1) for i in range(len(ORDER) - 1)]
    R["A4_retest"] = {
        "sol_main_pooled": round(main_pooled, 2), "sol_main_pooled_from_level_table": round(main_pooled_from_levels, 2),
        "sol_rerun_xhigh_pooled": rerun[0], "difference_points": round(diff, 2),
        "difference_items": round(diff * 5.02, 1),
        "per_level_main_minus_rerun": [round(a - b, 1) for a, b in zip(main_levels, rerun[1:])],
        "adjacent_average_gaps": gaps, "adjacent_pairs_with_gap_below_difference": sum(g < abs(diff) for g in gaps),
        "changes": sum(g < abs(diff) for g in gaps) >= 5,
    }

    # A5 clusters -------------------------------------------------------------------
    a5 = {}
    for m in ORDER:
        pc = S[m]["per_cell"]
        out = {}
        for icc in (0.0, 0.1, 0.3):
            var = 0.0
            for dom, cs in DOMAINS.items():
                nd = sum(pc[c]["seeded"]["n"] for c in cs)
                for c in cs:
                    nc = pc[c]["seeded"]["n"]
                    p = pc[c]["both_correct_rate"]
                    mc = P.CELL_SIZES[c]["questions"] / P.CELL_SIZES[c]["tasks"]
                    deff = 1 + (mc - 1) * icc
                    var += (0.5 * nc / nd) ** 2 * p * (1 - p) / nc * deff
            out[f"icc_{icc}"] = round(100 * 1.96 * math.sqrt(var), 1)
        a5[m] = out
    pres_items_per_task = P.CELL_SIZES["parallel_research"]["questions"] / P.CELL_SIZES["parallel_research"]["tasks"]
    R["A5_clusters"] = {
        "cell_sizes": P.CELL_SIZES,
        "items_per_task": {c: round(v["questions"] / v["tasks"], 2) for c, v in P.CELL_SIZES.items()},
        "weight_per_item_in_average_pts": {"engineering": round(50 / 390, 3), "research": round(50 / 112, 3)},
        "one_mean_pres_task_all_flipped_moves_average_pts": round(pres_items_per_task * 50 / 112, 2),
        "half_width_95_average_pts": a5,
        "adjacent_gaps_below_item_level_half_width_of_upper_model": sum(
            g < a5[ORDER[i]]["icc_0.0"] for i, g in enumerate(gaps)),
    }

    # A6 horizon vs cell composition ------------------------------------------------
    cells = list(P.HORIZON_COUNTS)
    pred = []
    for lev in range(4):
        vals = []
        for m in ORDER:
            pc = S[m]["per_cell"]
            vals.append(sum(P.HORIZON_COUNTS[c][lev] * 100 * pc[c]["both_correct_rate"] for c in cells) / lev_n[lev])
        pred.append(round(sum(vals) / len(vals), 1))
    obs = [round(sum(P.HORIZON_ACC[m][lev] for m in ORDER) / len(ORDER), 1) for lev in range(4)]
    R["A6_horizon_composition"] = {
        "level_n": lev_n, "observed_mean": obs, "published_mean": list(P.HORIZON_MEAN_PUBLISHED),
        "predicted_from_cell_only": pred, "observed_gap": round(obs[0] - obs[3], 1),
        "predicted_gap": round(pred[0] - pred[3], 1),
        "changes": (pred[0] - pred[3]) >= 0.5 * (obs[0] - obs[3]),
        "share_by_cell_of_level": {c: [round(100 * P.HORIZON_COUNTS[c][i] / lev_n[i], 1) for i in range(4)] for c in cells},
        "models_below_25_more_work": [m for m in ORDER if P.HORIZON_ACC[m][3] < 25],
    }

    # A7 detour vs parallel by domain ----------------------------------------------
    a7 = {}
    for dom, (dcell, pcell) in DOMAINS.items():
        d = [100 * S[m]["per_cell"][dcell]["both_correct_rate"] for m in ORDER]
        p = [100 * S[m]["per_cell"][pcell]["both_correct_rate"] for m in ORDER]
        md, mp = sum(d) / len(d), sum(p) / len(p)
        nd, npp = S[ORDER[0]]["per_cell"][dcell]["seeded"]["n"], S[ORDER[0]]["per_cell"][pcell]["seeded"]["n"]
        se_hi = 100 * math.sqrt((md / 100) * (1 - md / 100) / nd + (mp / 100) * (1 - mp / 100) / npp)
        a7[dom] = {"mean_detour": round(md, 1), "mean_parallel": round(mp, 1), "d_minus_p": round(md - mp, 1),
                   "ci95_if_models_perfectly_correlated": [round(md - mp - 1.96 * se_hi, 1), round(md - mp + 1.96 * se_hi, 1)],
                   "ci95_if_models_independent": [round(md - mp - 1.96 * se_hi / math.sqrt(14), 1), round(md - mp + 1.96 * se_hi / math.sqrt(14), 1)],
                   "models_detour_lower": sum(a < b for a, b in zip(d, p)), "n_models": len(d),
                   "per_model_d_minus_p": {m: round(a - b, 1) for m, a, b in zip(ORDER, d, p)}}
        a7[dom]["holds"] = a7[dom]["ci95_if_models_perfectly_correlated"][1] < 0
        a7[dom]["fails"] = abs(md - mp) <= 2 or a7[dom]["models_detour_lower"] <= 9
    R["A7_detour_vs_parallel"] = a7

    # A8 SWE-bench relation ---------------------------------------------------------
    swe = json.loads((ROOT / "results/swebench_from_figure.json").read_text())
    ms = [m for m in ORDER if m in swe]
    x = [swe[m]["swebench_verified"] for m in ms]
    y = [a1[m]["average"] for m in ms]
    ye = [a1[m]["eng"] for m in ms]
    r_all, r_eng = pearson(x, y), pearson(x, ye)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sum((a - mx) ** 2 for a in x)
    resid = {m: round(yy - (my + b * (xx - mx)), 1) for m, xx, yy in zip(ms, x, y)}
    drops = {}
    for pair in itertools.combinations(ms, 2):
        keep = [i for i, m in enumerate(ms) if m not in pair]
        drops[pair] = pearson([x[i] for i in keep], [y[i] for i in keep])
    construction = ("gpt-5.6-sol", "gpt-5.5")
    r_drop = drops[construction]
    pct = sum(v < r_drop for v in drops.values()) / len(drops)
    drops_eng = {}
    for pair in itertools.combinations(ms, 2):
        keep = [i for i, m in enumerate(ms) if m not in pair]
        drops_eng[pair] = pearson([x[i] for i in keep], [ye[i] for i in keep])
    keep1 = [i for i, m in enumerate(ms) if m != "gpt-5.5"]
    R["A8_swebench"] = {
        "n_models": len(ms), "swebench_read_from_figure": {m: swe[m]["swebench_verified"] for m in ms},
        "r_average": round(r_all, 3), "r_engineering": round(r_eng, 3),
        "published_r": [P.SWE_R_PUBLISHED, P.SWE_R_ENG_PUBLISHED],
        "residual_average_pts": resid,
        "r_drop_sol_and_gpt55": round(r_drop, 3), "percentile_among_55_drop_pairs": round(100 * pct, 1),
        "top_drop_pairs": [[list(k), round(v, 3)] for k, v in sorted(drops.items(), key=lambda t: -t[1])[:5]],
        "r_drop_gpt55_only": round(pearson([x[i] for i in keep1], [y[i] for i in keep1]), 3),
        "r_eng_drop_sol_and_gpt55": round(drops_eng[construction], 3),
        "percentile_eng_among_55": round(100 * sum(v < drops_eng[construction] for v in drops_eng.values()) / 55, 1),
        "changes": pct >= 0.9,
    }

    # A9 domain gap by family (exploratory) ----------------------------------------
    gap = {m: round(a1[m]["res"] - a1[m]["eng"], 1) for m in ms}
    claude = ("claude-opus-5", "claude-sonnet-5")
    stat = lambda grp: sum(gap[m] for m in grp) / len(grp) - sum(gap[m] for m in ms if m not in grp) / (len(ms) - len(grp))
    obs_stat = stat(claude)
    perm = [stat(g) for g in itertools.combinations(ms, 2)]
    gpt = ("gpt-5.6-sol", "gpt-5.5", "gpt-5.6-terra", "gpt-5.6-luna")
    perm4 = [stat(g) for g in itertools.combinations(ms, 4)]
    R["A9_family_domain_gap_exploratory"] = {
        "res_minus_eng": gap, "claude_minus_rest": round(obs_stat, 1),
        "exact_p_claude_pair_ge": round(sum(v >= obs_stat - 1e-9 for v in perm) / len(perm), 3),
        "gpt_minus_rest": round(stat(gpt), 1),
        "exact_p_gpt_quad_le": round(sum(v <= stat(gpt) + 1e-9 for v in perm4) / len(perm4), 3),
        "note": "noticed before prereg; exploratory",
    }

    # A10 human review and end-to-end arithmetic -----------------------------------
    h = P.HUMAN
    disagree = h["explicit"] - h["agree"]
    retention = h["explicit"] / h["max_judgments"]
    exp_ret = retention * 2 * h["undecidable_removed"]
    e = P.E2E
    whole = {k: [round(100 * x_ / e["tasks"], 2) for x_ in range(e["tasks"] + 1) if abs(100 * x_ / e["tasks"] - e[k]) < 0.05]
             for k in ("no_advice", "correct_advice", "student_advice")}
    runs_needed = next(k for k in range(1, 50) if any(abs(100 * x_ / (41 * k) - e["student_advice"]) < 0.05 for x_ in range(41 * k + 1)))
    R["A10_human_e2e"] = {
        "human_total_disagreements": disagree, "human_retention_overall": round(retention, 3),
        "undecidable_removed_judgments_if_same_retention": round(exp_ret, 1),
        "agreement_lower_bound_on_undecidable_removed_if_same_retention": round(100 * (exp_ret - disagree) / exp_ret, 1),
        "e2e_whole_task_fractions_matching": whole,
        "student_advice_min_runs_per_task_for_rate": runs_needed,
        "student_fork_accuracy": round(100 * e["student_correct_forks"] / e["forks"], 1),
        "distill_mcnemar_discordant": [P.DISTILL["student_only"], P.DISTILL["base_only"]],
    }

    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/part_a.json").write_text(json.dumps(R, indent=1, default=str))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("rows", "per_model", "funnel")} for k, v in R.items()}, indent=1, default=str)[:12000])


if __name__ == "__main__":
    main()
