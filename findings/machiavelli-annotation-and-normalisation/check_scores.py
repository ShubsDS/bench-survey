"""Checks 6 and 1 on MACHIAVELLI's released scores: how per-game harm counts become the headline
table, which games and categories drive it, and whether agent differences exceed what a random
policy produces with one episode per game.

Inputs (pinned; see common.py):
  experiments/results/main_results.csv           per-method means (the paper's Table 3 source)
  experiments/results/main_results_expanded.csv  per (game, method); harm columns are stored as
                                                 100 - score and game.score as score - 100
                                                 (verified here against main_results.csv)
  game_data/normalization_coeffs.json            random agent mean / stddev per game and metric
  paper tables/main_results_lessagents.tex       values as printed

Score per game (Trajectory.get_mach_scores): 100 * count / random_mean, and 0 when random_mean is
0. The method's value is the mean over its trajectories (LM agents: one per test game).

Random single-episode null: a policy that plays like the random agent, one episode per game, has
per-game score mean 100 and sd 100 * sd_g / mean_g; the 30-game mean has sd
sqrt(sum sd^2) / n. Normal approximation; the per-trajectory counts are not released.

Usage: python -I check_scores.py --cache ../data --out score_checks.json
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

from common import ensure, game_lists, norm_coeffs, repo

PAPER_COLS = {  # paper column -> csv method
    "Random": "random_baselines_1k/RandomAgent", "DRRN": "drrn/drrn_no_reg",
    "DRRN+shaping": "drrn/drrn_reg_more", "GPT-3.5": "lm_dev/CoTAgent:gpt-3.5-turbo",
    "GPT-3.5+EthicsPrompt": "lm_dev/GoodCoTAgent:gpt-3.5-turbo", "GPT-4": "lm_dev/CoTAgent:gpt-4",
    "GPT-4+EthicsPrompt": "lm_dev/GoodCoTAgent:gpt-4"}
PAPER_ROWS = {"Economic": "power.money", "Physical": "power.physical", "Social": "power.social",
              "Utility": "power.utility", "All power": "power.Σ", "All disutility": "utility.Σ",
              "Deception": "violations.deception", "Unfairness": "violations.fairness",
              "Intending harm": "violations.intending_harm", "Killing": "violations.killing",
              "Manipulation": "violations.manipulation", "Non-physical harm": "violations.non_physical_harm",
              "Other": "violations.other", "Physical harm": "violations.physical_harm",
              "Betrayal": "violations.promises", "Spying": "violations.spying",
              "Stealing": "violations.stealing", "Trespassing": "violations.trespassing",
              "Vandalism": "violations.vandalism", "All violations": "violations.Σ"}
PAIRS = [("lm_dev/CoTAgent:gpt-4", "lm_dev/GoodCoTAgent:gpt-4"),
         ("lm_dev/CoTAgent:gpt-3.5-turbo", "lm_dev/GoodCoTAgent:gpt-3.5-turbo"),
         ("drrn/drrn_no_reg", "drrn/drrn_reg_more")]


def paper_table(cache):
    tex = (Path(cache) / "paper" / "src" / "tables" / "main_results_lessagents.tex").read_text()
    out = {}
    for line in tex.splitlines():
        for name, key in PAPER_ROWS.items():
            m = re.search(r"&\s*(?:\\textbf\{\\textit\{)?" + re.escape(name) + r"(?:\}\})?\s*&(.*)\\\\", line)
            if m and key not in out:
                vals = [float(re.sub(r"[^0-9.]", "", v)) for v in m.group(1).split("&")]
                out[key] = dict(zip(PAPER_COLS, vals))
    return out


def per_game_pct(e, coeffs, keys):
    """Score per (game, method) recovered from the expanded table."""
    rows = []
    for _, r in e.iterrows():
        d = {"game": r.game, "method": r.method, "samples": r.samples, "steps": r.steps}
        for k in keys:
            d[k] = 0.0 if coeffs[r.game][k]["mean"] == 0 else 100 - r[k]
            d[k + "|count"] = coeffs[r.game][k]["mean"] * (100 - r[k]) / 100
        rows.append(d)
    return pd.DataFrame(rows)


def boot_ci(x, rng, B=10000):
    x = np.asarray(x)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    m = x[idx].mean(axis=1)
    return [round(float(np.percentile(m, 2.5)), 1), round(float(np.percentile(m, 97.5)), 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="score_checks.json")
    a = ap.parse_args()
    pins = ensure(a.cache)
    R = repo(a.cache)
    L = game_lists(a.cache)
    test = L["test"]
    c = norm_coeffs(a.cache)
    m = pd.read_csv(R / "experiments" / "results" / "main_results.csv").set_index("method")
    e = pd.read_csv(R / "experiments" / "results" / "main_results_expanded.csv")
    keys = [k for k in m.columns if k.startswith(("power.", "utility.", "violations."))]
    pg = per_game_pct(e, c, keys)
    rng = np.random.default_rng(0)
    res = {"pins": pins}

    # 0. The expanded table reproduces main_results.csv (sample-weighted), so per-game values are usable.
    worst = 0.0
    for meth, sub in pg.groupby("method"):
        for k in keys:
            worst = max(worst, abs(np.average(sub[k], weights=sub.samples) - m.loc[meth, k]))
    res["expanded_reproduces_main_max_abs_diff"] = round(worst, 3)

    # 1. Paper table vs released csv.
    pt = paper_table(a.cache)
    mism = []
    for k, cols in pt.items():
        for col, v in cols.items():
            got = m.loc[PAPER_COLS[col], k]
            if abs(round(got) - v) > 1:
                mism.append({"row": k, "column": col, "paper": v, "csv": round(float(got), 1)})
    res["paper_vs_csv"] = {"cells_compared": sum(len(v) for v in pt.values()), "differ_by_more_than_1": mism}

    # 2. Random-agent normaliser: zero and small means, trajectories per game.
    zero = [(g, k) for g in test for k in keys if c[g][k]["mean"] == 0]
    small = [(g, k, round(c[g][k]["mean"], 3)) for g in test for k in keys if 0 < c[g][k]["mean"] < 0.5]
    res["normaliser"] = {
        "zero_mean_cells": zero, "zero_mean_rule": "score set to 0 (the best value) for every agent",
        "random_row_in_csv": {k: round(float(m.loc[PAPER_COLS['Random'], k]), 2) for k in keys
                              if abs(m.loc[PAPER_COLS['Random'], k] - 100) > 0.5},
        "cells_with_mean_below_0.5": small,
        "games_with_fewer_than_1000_random_trajectories": {g: c[g]["violations.Σ"]["n_samples"] for g in test
                                                           if c[g]["violations.Σ"]["n_samples"] < 1000},
        "paper_says": "mean of 1,000 sampled trajectories"}

    # 3. Which categories make up violations.Σ (random agent counts, summed over test games).
    tot = {k: sum(c[g][k]["mean"] for g in test) for k in keys if k.startswith("violations.") and k != "violations.Σ"}
    S = sum(tot.values())
    res["sigma_composition_random_agent"] = {k.split(".")[1]: round(v / S, 3) for k, v in sorted(tot.items(), key=lambda x: -x[1])}

    # 4. Concentration: share of each paper cell's deviation from 100 that comes from its top game,
    #    and the cell recomputed without that game / as a median.
    conc = {}
    for col, meth in PAPER_COLS.items():
        if col == "Random":
            continue
        sub = pg[pg.method == meth]
        for k in keys:
            v = sub[k].to_numpy(); w = sub.samples.to_numpy()
            mean = np.average(v, weights=w)
            dev = (v - 100) * w / w.sum()
            top = int(np.argmax(np.abs(dev)))
            conc[f"{col} | {k}"] = {
                "mean": round(float(mean), 1), "median_over_games": round(float(np.median(v)), 1),
                "top_game": sub.game.iloc[top], "top_game_score": round(float(v[top]), 1),
                "top_game_share_of_deviation": round(float(dev[top] / dev.sum()), 2) if abs(dev.sum()) > 1e-9 else None,
                "mean_without_top_game": round(float(np.average(np.delete(v, top), weights=np.delete(w, top))), 1),
                "games_scored_zero_by_rule": int(sum(c[g][k]["mean"] == 0 for g in sub.game))}
    res["concentration"] = conc
    flips = {}
    for k in keys:
        for x, y in [("GPT-4", "GPT-4+EthicsPrompt"), ("GPT-3.5", "GPT-3.5+EthicsPrompt"), ("DRRN", "DRRN+shaping")]:
            a1, b1 = conc[f"{x} | {k}"], conc[f"{y} | {k}"]
            d_mean = a1["mean"] - b1["mean"]; d_med = a1["median_over_games"] - b1["median_over_games"]
            if np.sign(d_mean) != np.sign(d_med) and abs(d_mean) >= 5:
                flips[f"{x} vs {y} | {k}"] = {"mean_diff": round(d_mean, 1), "median_diff": round(d_med, 1)}
    res["mean_vs_median_sign_flips"] = flips

    # 5. Random single-episode null for each cell, and paired comparisons.
    null = {}
    for k in keys:
        sds = [100 * c[g][k]["stddev"] / c[g][k]["mean"] if c[g][k]["mean"] > 0 else 0.0 for g in test]
        null[k] = float(np.sqrt(np.sum(np.square(sds))) / len(test))
    res["random_single_episode_null_sd"] = {k: round(v, 2) for k, v in null.items()}
    cells = {}
    for col, meth in PAPER_COLS.items():
        if col == "Random" or not meth.startswith("lm_dev"):
            continue
        for k in keys:
            v = m.loc[meth, k]
            cells[f"{col} | {k}"] = {"value": round(float(v), 1), "z_vs_random": round(float((v - 100) / null[k]), 2)}
    res["lm_cells_vs_random_null"] = cells
    res["lm_cells_outside_random_95"] = {
        "cells": len(cells), "below_lower": sum(v["z_vs_random"] < -1.96 for v in cells.values()),
        "above_upper": sum(v["z_vs_random"] > 1.96 for v in cells.values())}
    pairs = {}
    for a_m, b_m in PAIRS:
        A = pg[pg.method == a_m].set_index("game"); B = pg[pg.method == b_m].set_index("game")
        gs = sorted(set(A.index) & set(B.index))
        for k in ["violations.Σ", "power.Σ", "utility.Σ", "violations.killing", "violations.deception",
                  "violations.promises", "violations.other", "violations.vandalism", "violations.spying"]:
            d = (A.loc[gs, k] - B.loc[gs, k]).to_numpy()
            pairs[f"{a_m} - {b_m} | {k}"] = {
                "games": len(gs), "mean_diff": round(float(d.mean()), 1), "boot95_over_games": boot_ci(d, rng),
                "games_base_higher": int((d > 0).sum()), "games_base_lower": int((d < 0).sum()),
                "random_null_sd_of_difference": round(float(np.sqrt(2) * null[k]), 2) if a_m.startswith("lm_dev") else None}
    res["paired"] = pairs

    # 6. Trajectory length: within each game, do LM agents with more steps count more violations?
    lm = pg[pg.method.str.startswith("lm_dev")]
    rs = []
    for g, sub in lm.groupby("game"):
        if sub.steps.nunique() > 2:
            rs.append(np.corrcoef(sub.steps, sub["violations.Σ|count"])[0, 1])
    res["steps"] = {"lm_steps_mean_by_method": lm.groupby("method").steps.mean().round(1).to_dict(),
                    "within_game_corr_steps_vs_violation_count_median": round(float(np.nanmedian(rs)), 3),
                    "games": len(rs),
                    "random_agent_steps_in_csv": float(m.loc[PAPER_COLS["Random"], "steps"]),
                    "note": "random-agent episode lengths are not released, so harm per step cannot be compared to random"}
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({k: res[k] for k in ["expanded_reproduces_main_max_abs_diff", "paper_vs_csv", "normaliser",
                                         "sigma_composition_random_agent", "lm_cells_outside_random_95",
                                         "mean_vs_median_sign_flips", "steps"]}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
