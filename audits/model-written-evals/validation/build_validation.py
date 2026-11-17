"""Collect the validator's numbers and verdicts into validation/validation.json.

Step A (rerun of the auditor's analysis scripts, no inference) was done in a scratch copy of
this folder with audits/tools/claude_call.py replaced by a cache-only stub that raises on any
cache miss; then:
    scripts/l3_caa.py, scripts/l4_run.py, scripts/l4b_hwe_vs_mwe.py, scripts/summarise.py
Pass that copy with --rerun to record the file comparison.

    python3 -I validation/build_validation.py --rerun <scratch>/audits/model-written-evals
"""
import argparse, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerun", default=None)
    a = ap.parse_args()
    c = json.loads((HERE / "validation" / "rederive_caa.json").read_text())
    l4 = json.loads((HERE / "validation" / "l4_recheck.json").read_text())
    out = {"validator_date": "2026-11-17", "inference_spend_usd": 0.0}
    if a.rerun:
        R = Path(a.rerun)
        cmp = {}
        for f in ("results/l3_caa.json", "results/l4_haiku.json", "results/l4b_hwe_vs_mwe.json", "results.json"):
            cmp[f] = "identical" if sha(R / f) == sha(HERE / f) else "differs"
        a4, b4 = json.loads((R / "results/l4_haiku.json").read_text()), json.loads((HERE / "results/l4_haiku.json").read_text())
        cmp["l4_items_differing"] = {k: {"rerun": a4["per_item"][k], "committed": b4["per_item"][k]} for k in a4["per_item"] if a4["per_item"][k] != b4["per_item"][k]}
        cmp["l4_score_o_rerun_vs_committed"] = [a4["all"]["score_o"], b4["all"]["score_o"]]
        out["A_rerun"] = cmp
    co, sv, u = c["coordination_7b"], c["survival"], c["unsteered_13b"]
    out["claims"] = {
        "1_reproduction": {"verdict": "HOLDS WITH CORRECTION", "table10_7b": {k: v for k, v in c["reproduction"].items() if k.startswith("7b")},
                           "table3_13b": {k: v for k, v in c["reproduction"].items() if k.startswith("13b")},
                           "note": "Survival row matches at layer 13 and 14; three rows match only layer 14. CAA section 4.1 says the optimal 13B layer is usually 14 or 15, so the caption is the likely error."},
        "2_coordination_7b": {"verdict": "HOLDS WITH CORRECTION", "delta_Y": co["delta_Y"], "delta_N": co["delta_N"], "delta_N_t_interval": co["delta_N_t_interval"],
                              "equal_weight": co["delta_equal_weight"], "placebo": co["placebo_perm_dY_minus_dN"], "crosstab_pol_letter": co["crosstab_pol_letter"],
                              "yes_is_A_share": co["yes_is_option_A_share_among_YN_items"], "topic_control": co["topic_tag"],
                              "same_items_other_conditions": co["same_items_other_conditions"], "open_ended": co["open_ended_m-1_to_+1"]},
        "3_survival_7b": {"verdict": "HOLDS WITH CORRECTION", "ab_test": sv["7b/L13"], "open_ended_7b": sv["open_ended_7b_L13"], "open_ended_13b": sv["open_ended_13b_L14"],
                          "generation_sets": c["sets"], "position_all": c["position_all"]},
        "4_13b_unsteered": {"verdict": "HOLDS (corrigibility, myopia); README generalisation to all four behaviours FAILS for coordination", "values": u},
        "5_scorer": {"verdict": "HOLDS", "values": c["scorer"]},
        "6_haiku_minimal_pairs": {"verdict": "HOLDS WITH CORRECTION (numbers reproduce; interpretation corrected)", "recheck": l4},
        "7_dev_hobbhahn": {"verdict": "HOLDS WITH CORRECTION (hypothesis now supported by their released code, not by their outputs)",
                           "code": "github.com/Sunishchal/model-written-evals@65eb2faeb0cd5fb5f04511ca11f4243ee7542932 utils.py:99-103 swaps answer_matching_behavior and answer_not_matching_behavior for every power-seeking-inclination and wealth-seeking-inclination row, human-written and LM-written alike"},
    }
    (HERE / "validation" / "validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out.get("A_rerun"), indent=1))


if __name__ == "__main__":
    main()
