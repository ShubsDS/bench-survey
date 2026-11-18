"""Collect the validator's numbers into validation.json and add a `validation` block to ../results.json.

The auditor's original blocks in results.json are kept unchanged; corrections live under `validation`.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import AUD, HERE  # noqa: E402

parts = {}
for p in sorted(HERE.glob("v*_*.json")):
    if p.name == "validation.json":
        continue
    d = json.loads(p.read_text())
    if p.name == "v6_hand_compare.json":
        d = {k: v for k, v in d.items() if k != "per_item"}  # per-item labels stay in the CSV
    parts[p.stem] = d
c9 = {"gpt41_options_only_released_peng": 63.7,
      "models_at_or_below_all_presentations": ["gpt-5.4-mini", "gpt-5.4-nano", "grok-4.20-reasoning",
                                               "mistral-medium-3.5"],
      "models_at_or_below_parsed": ["gpt-5.4-mini", "mistral-medium-3.5"]}
sab = {"auditor_ids": 5, "state_sabotage_or_sandbag_plan": 4,
       "declines_sabotage": ["det-malt-ba219d49df84fe38-v3"], "paper_mentions_filter": False}
summary = {
    "C1": {"verdict": "corrected", "auditor": {"floor_average": 60.4, "heldout": 61.4},
           "validator_full_set": parts["v1_floor_null"]["cont"]["full_set_fixed_sign_average"],
           "validator_heldout_split_distribution": parts["v1_floor_null"]["cont"]["real_heldout_fixed_signs"],
           "null_placebo_fitted": parts["v1_floor_null"]["cont"]["placebo_feature_fitted_signs"],
           "null_flip_fitted": parts["v1_floor_null"]["cont"]["task_flip_fitted_signs"],
           "models_single_order_above_60.4": parts["v1_floor_null"]["models_single_order_above_60.4"],
           "inferred_cell_average": {"cont": parts["v2_cell_inference"]["floor_cont"]["average_inferred_cell"],
                                     "ground": parts["v2_cell_inference"]["floor_ground"]["average_inferred_cell"]},
           "cell_inference_accuracy": {"engineering": parts["v2_cell_inference"]["engineering"]["lam1"]["oof_accuracy"],
                                       "research": parts["v2_cell_inference"]["research"]["lam1"]["oof_accuracy"]}},
    "C2": {"verdict": "reproduced, caveated", "h2_contrast": parts["v8_h2"]["contrast_detour_minus_parallel"],
           "placebo_construction_shuffle_p": parts["v8_h2"]["placebo_construction_shuffle"]["share_ge_observed"],
           "h3": parts.get("v12_h3_score")},
    "C3": {"verdict": "downgraded", "below50_parsed": parts["v5_detour_eng"]["below50_single_parsed"],
           "distinguishably_below50_haiku_icc": parts["v5_detour_eng"]["upper_below50_parsed_haikuicc"],
           "selection_carryover": {k: {kk: v[kk] for kk in ("residual_related_minus_unrelated", "one_sided_p_related_lower",
                                                           "slope_de_on_other")}
                                   for k, v in parts["v5_detour_eng"]["selection_carryover"].items()},
           "blind_labels_vs_key": parts["v6_hand_compare"]["all"]["me_vs_key"],
           "blind_labels_vs_key_ci": parts["v6_hand_compare"]["all"]["me_vs_key_ci_task_boot"]},
    "C4": {"verdict": "confirmed, reworded (disclosed counts)",
           "glm": parts["v7_parse"]["models"]["glm-5.2"], "grok420_parsed_pooled": parts["v7_parse"]["grok420_parsed_single_order"],
           "sol_pooled": parts["v7_parse"]["sol_single_order"]},
    "C5": {"verdict": "confirmed", "research": parts["v10_secondary"]["C5_research"]},
    "C6": {"verdict": "corrected", "average_gaps_below": parts["v10_secondary"]["C6"]["average_gaps_below_rerun_diff"],
           "pooled_gaps_below": parts["v10_secondary"]["C6"]["pooled_gaps_below_rerun_diff"],
           "sol_reasoning_tokens_per_presentation": parts["v10_secondary"]["C6"]["sol_main_reasoning_tokens_per_presentation"]},
    "C7": {"verdict": "confirmed, caveat corrected", **parts["v10_secondary"]["C7"]},
    "C8": {"verdict": "confirmed", **{k: v for k, v in parts["v10_secondary"]["C8"].items() if k != "residuals"}},
    "C9": {"verdict": "confirmed, narrowed", **c9},
    "C10": {"sabotage": sab, "human_review": parts["v10_secondary"]["C10_human"],
            "e2e": parts["v10_secondary"]["C10_e2e"]},
    "leak_scan": parts.get("v11_leak_scan"),
}
val = {"validator": "independent validation, 2026-11-17", "summary": summary, "parts": parts}
(HERE / "validation.json").write_text(json.dumps(val, indent=1) + "\n")
res = json.loads((AUD / "results.json").read_text())
res["validation"] = summary
(AUD / "results.json").write_text(json.dumps(res, indent=1))
print("ok", list(summary))
