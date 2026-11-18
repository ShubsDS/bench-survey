"""Collect every reported number into results.json.

    data/.venv/bin/python -I scripts/build_results.py
"""
import json
import os

import pandas as pd
from sklearn.metrics import cohen_kappa_score

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")


def j(p):
    with open(os.path.join(BASE, p)) as fh:
        return json.load(fh)


def main():
    a0 = j("results/analysis_seed0.json")
    rb = j("results/robust.json")
    k = pd.read_csv(os.path.join(BASE, "data", "handlabel_key.csv"))
    h = pd.read_csv(os.path.join(BASE, "results", "handlabels.csv"))
    m = k.merge(h, on="item")
    hand = {
        "n": int(len(m)),
        "design": "blind to tier and labels; 12+12 free-tier and 8+8 paid-tier PM-compliant outputs, half follows_instructions True; one rater (auditor)",
        "crosstab_fi_by_hand": {str(fi): m[m.fi == fi].hand.value_counts().to_dict() for fi in (True, False)},
        "crosstab_tier_fi_by_hand": {f"{t}|{fi}": g.hand.value_counts().to_dict() for (t, fi), g in m.groupby(["tier", "fi"])},
        "kappa_fi_vs_hand_full": float(cohen_kappa_score(m.fi, m.hand == "F")),
        "agreement": float((m.fi == (m.hand == "F")).mean()),
    }
    sm = pd.read_parquet(os.path.join(BASE, "data", "samples.parquet"))
    inv = sm.groupby("setting").agg(rows=("qid", "size"), variants=("variant", "nunique")).to_dict("index")
    res = {
        "pins": {
            "alignment_faking_public": "8d98bb786893ac44d02f41eb222eabf302c0aab9",
            "json_outputs.zip_sha256": "6e7c3f9915cfc2dfdceff1c4dfdad6b328b845f75f5e10e1b0446c8764b139d7",
            "open-source-alignment-faking": "dc21773fd6b69ae8be3503d51d7412e88aa2f39d",
            "alignment-faking-extensions": "6b3e35cd5842970531148b63dac8e92811ed8b41",
            "hf_human_labels_rev": "3c087f7e385129b417a4e8ef7c0dd58be30b4d65",
            "hf_human_labels_parquet_sha256": "3a203f80a5a0ab3a15ce16918428bba02f8aeaa0665b09ab5de68d5c0f94441d",
        },
        "inventory_rows_by_setting": inv,
        "A1_headline": a0["A1"],
        "A2_unit_of_analysis": a0["A2"],
        "A3_outcome_routes": a0["A3"],
        "A3_hand_validation": hand,
        "A4_reasoning_accounts_for_gap": {"opus_pooled": a0["A4"]["opus_pooled"], "per_variant": a0["A4"]["per_variant"]},
        "A5_which_models": a0["A5"],
        "A6_judge_vocabulary": a0["A6"],
        "A7_variant_spread": a0["A7"],
        "robustness": {k2: rb[k2] for k2 in ("seed0", "seed1", "thr_minus05", "bonferroni", "P5_A3_pooled_ratio_drop_each_variant_min_max")},
        "post_hoc": {k2: rb[k2] for k2 in ("P1_no_gap_cells_vs_opus_like", "P2_opus_vs_sonnet35_default",
                                           "P3_human_label_aurocs", "P4_default_odds_scale")},
        "inference": {"calls": 0, "usd": 0.0},
    }
    with open(os.path.join(BASE, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print("ok", hand)


if __name__ == "__main__":
    main()
