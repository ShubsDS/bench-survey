"""Collect every reported number into results.json (run after the other scripts)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

R = Path("results")


def load(name):
    p = R / name
    return json.loads(p.read_text()) if p.exists() else None


def main():
    a = load("analyse.json")
    out = {
        "status": "2026-11-17; see README for evidence levels",
        "pins": {**a["pins"], "chainscope_commit": "bb128ac0f22dd60ab3d876a78e1c6c22fff7e830",
                 "paper_eprint_sha256": {"v1": "6e29fa5fecba1af426d9de8933def8cfeb1a8b1e159c7e52d5d77d97d09c0a26",
                                         "v4": "ab7bf596dc0914d8e453f9edaa44e14c6b6aec621d078f8f1184d825b79bf363",
                                         "v6": "4bcfb23b73e8837327416701c866c250f0802418be0e918035f5d103abe4eab6"}},
        "preregistered": {k: a[k] for k in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "C2_comparisons")},
        "posthoc": {
            "P1_P2_dispersion": load("posthoc.json"),
            "P3_hedge": load("posthoc_hedge.json"),
            "P4_answer_flipping_authors_autorater": load("posthoc_flip.json"),
            "P5_route_handcheck": load("handcheck_routes.json"),
            "P6_route_shares": load("posthoc_routes.json"),
            "P7_C2_without_flip_dominated": load("posthoc_c2.json"),
            "P8_rule_on_partner": load("posthoc_sr_partner.json"),
        },
        "A9_ground_truth": pd.read_csv("gt_labels.csv").label.value_counts().to_dict(),
        "A10_haiku": load("l4_haiku.json"),
    }
    Path("results.json").write_text(json.dumps(out, indent=1))
    print("wrote results.json", len(json.dumps(out)))


if __name__ == "__main__":
    main()
