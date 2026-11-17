"""Collect every number reported in README.md into results.json, from the per-analysis outputs.

    data/.venv/bin/python -I scripts/summarise.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
R = HERE / "results"


def main():
    l3 = json.loads((R / "l3_caa.json").read_text())
    l4 = json.loads((R / "l4_haiku.json").read_text())
    l4b = json.loads((R / "l4b_hwe_vs_mwe.json").read_text()) if (R / "l4b_hwe_vs_mwe.json").exists() else None
    keep = ("S_pos", "S_neg", "gap", "full", "reweighted", "acq_share", "delta_pos", "delta_neg", "delta_full",
            "delta_reweighted", "yes_component", "disposition_component", "delta_pos_minus_neg", "n_pos", "n_neg", "n_other")
    out = {
        "pins": {"dataset": "Anthropic/model-written-evals@d533f626cc321c92175a58ee570aa3cdb87238d1",
                 "caa": "nrimsky/CAA@5dabbbd9a0bca5f25e174501e959de378806aa48",
                 "repepo": "dtch1997/repepo@68f650aa76275039903fde10c299f0b01fa5045f",
                 "lm_eval_harness": "EleutherAI/lm-evaluation-harness@d6de81643928d653435c431bae19945d41d32520"},
        "L3_reproduction": l3["reproduction"],
        "L3_table3_layer14_reproduction": {b: {k: v[k] for k in ("published", "recomputed", "match_within_0.01")} for b, v in l3["table3_layer14"].items()},
        "L3_strata_sizes_test": l3["strata_sizes"],
        "L3_generation_sets": l3["generation_sets"],
        "L3_polarity_layer13": {k: {kk: v[kk] for kk in keep if kk in v} for k, v in l3["primary"].items()},
        "L3_position_layer13": {k: {kk: v[kk] for kk in keep if kk in v} for k, v in l3["position"].items()},
        "L3_joint_layer13": l3["joint"],
        "L3_13b_layer14": {b: {"polarity": {kk: v["polarity"][kk] for kk in keep if kk in v.get("polarity", {})},
                               "position": {kk: v["position"][kk] for kk in keep if kk in v["position"]},
                               "joint": v.get("joint"), "verdict_steering": v.get("verdict_steering"),
                               "verdict_baseline": v.get("verdict_baseline")} for b, v in l3["table3_layer14"].items()},
        "L3_always_letter": l3["always_letter"],
        "L3_verdicts_prereg": l3["verdicts"], "L3_holm": l3["holm"], "L3_raw_p": l3["raw_p"],
        "L3_robustness": {"F1b": {k: {kk: v[kk] for kk in ("n_pos", "n_neg", "delta_pos", "delta_neg", "gap") if kk in v} for k, v in l3["F1b"].items()},
                          "binary_stat": {k: {kk: v[kk] for kk in ("delta_pos", "delta_neg", "gap") if kk in v} for k, v in l3["binary_stat"].items()},
                          "drop_one": l3["drop_one"], "placebo": l3["placebo"],
                          "system_prompt": {k: {kk: v[kk] for kk in ("S_pos", "S_neg", "delta_pos", "delta_neg") if kk in v} for k, v in l3["system_prompt"].items()},
                          "finetuned": {k: {kk: v[kk] for kk in ("S_pos", "S_neg") if kk in v} for k, v in l3["finetuned"].items()},
                          "layers": l3["layers"]},
        "L3_corrected_scorer": l3["corrected_scorer"],
        "L4_haiku": {k: v for k, v in l4.items() if k != "per_item"},
        "L4b_hwe_vs_mwe": l4b,
    }
    (HERE / "results.json").write_text(json.dumps(out, indent=1))
    print("wrote results.json")


if __name__ == "__main__":
    main()
