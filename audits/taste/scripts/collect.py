"""Collect every reported number into results.json. Run after desk.py and simulate.py."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
desk = json.loads((HERE / "results/desk.json").read_text())
sim = json.loads((HERE / "results/simulate.json").read_text())

# Interval for Fable 5 (60%, 92 pairs) and for the 77.4 - 60 gap under proposal clustering.
# Assumption (stated in the README): the human estimate (85 pairs) has the same design effect as the
# model; covariance between the two is ignored (it would narrow the gap interval if positive).
gap = {}
for rho, g in sim["T4"]["grid"].items():
    deff = g["design_effect"]
    sd_m = math.sqrt(0.60 * 0.40 / 92 * deff)
    sd_h = math.sqrt(0.774 * 0.226 / 85 * deff)
    sd_gap = math.sqrt(sd_m ** 2 + sd_h ** 2)
    gap[rho] = {"design_effect": deff,
                "fable5_ci95": [round(100 * (0.60 - 1.96 * sd_m), 1), round(100 * (0.60 + 1.96 * sd_m), 1)],
                "gap_ci95": [round(100 * (0.174 - 1.96 * sd_gap), 1), round(100 * (0.174 + 1.96 * sd_gap), 1)],
                "null_p_acc_ge_060": g["null_p_ge_060"],
                "null_p_52_le_296": g["null_magnetfree_p_le_296"],
                "null_p_52_le_11of52": g["null_magnetfree_p_le_21pct"]}

results = {
    "status": "Case B desk audit, 2026-11-17. Published and digitised numbers plus synthetic simulations; no per-pair data.",
    "provenance": {
        "paper": "Table 3, Table 5, Fig. 12, Fig. 13, Fig. 19, App. C.2 (transcribed in scripts/published.py)",
        "critique": "prose numbers and Fig. 2 digitised by marker colour (results/critic_fig2_digitised.json)",
        "simulation": "results/simulate.json; synthetic benchmarks, NOT TASTE data",
    },
    "T0_reproduction": {k: desk["T0"][k] for k in ("median_abs_diff", "max_abs_diff", "n_compared", "r_ties_eci_28_filled",
                                                    "n_above158", "n_above158_below50", "openai_mean_ties",
                                                    "fable5_qshown_table5", "haiku_qshown_table5")},
    "T1_label_blind_placebo_magnet_free": {k: desk["T1"][k] for k in (
        "magnet_free_below50", "critic_ties_below50_paper19", "magnet_free_sig_below", "critic_ties_sig_below_paper19",
        "magnet_free_mean", "critic_ties_mean_paper19", "magnet_free_r_eci", "critic_ties_r_eci_paper19",
        "r_magnetfree_vs_critic_ties", "implied_magnet_mean")},
    "T2_within_prompt": {k: desk["T2"][k] for k in (
        "above158_models", "above158_still_below50_worstcase", "gpt56_still_below50_worstcase",
        "r_eci_within_qshown", "r_eci_within_qhidden", "r_eci_distinct_qshown", "r_eci_distinct_qhidden",
        "r_eci_qshown_overall", "r_eci_qhidden_overall", "r_eci_table3", "mean_within_qshown_above158",
        "sweep_k_within_in_ties")},
    "T3_leverage_families": desk["T3"],
    "T4_effective_sample_size": {"grid": sim["T4"]["grid"], "gap_and_fable5_intervals": gap,
                                 "distinct_winners_mean": sim["T4"]["distinct_winners_mean"],
                                 "pairs_won_by_top8_winners_mean": sim["T4"]["pairs_won_by_top8_winners_mean"],
                                 "min_proposals_carrying_32_decided": 4},
    "T5_tuning_null": sim["T5"],
    "T6_split_artifact": sim["T6"],
    "T6_max_pattern_freq": max(v["freq_critic_pattern"] for v in sim["T6"].values()),
    "T6_min_mean_top14_tie_acc": min(v["mean_top14_tie_acc"] for v in sim["T6"].values()),
    "T7_human": desk["T7"],
    "inference_usd": 0.0,
}
(HERE / "results.json").write_text(json.dumps(results, indent=1, default=lambda o: o.item()))
print(json.dumps(gap, indent=1))
print("T6 max freq", results["T6_max_pattern_freq"], "min top14 tie acc", results["T6_min_mean_top14_tie_acc"])
