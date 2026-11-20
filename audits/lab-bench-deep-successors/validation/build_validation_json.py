"""Collect the validator's numbers into validation.json. Run with python3 -I from the audit folder."""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
v1 = json.loads((H / "v1_versions.json").read_text())
v2 = json.loads((H / "v2_bounds.json").read_text())
v3 = json.loads((H / "v3_lb2_format.json").read_text())
v4 = json.loads((H / "v4_peritem_gate.json").read_text())
v5 = json.loads((H / "v5_lenfrags_sets.json").read_text())
rel = {r: {k: v1[r][k] for k in ("date", "seqqa_sha256", "n_items", "carrying", "carrying_generic_rules_only",
                                 "S6_mainrule_mean", "S6_mainrule_ci", "S6_lev_or_num_mean", "all15_mainrule_mean",
                                 "all15_ci", "placebo_sha_all15", "vs_parent", "dbqa_multi_seq")}
       for r in v1 if r != "hfbio_curated"}
cur = v1["hfbio_curated"]
out = {
    "validator": "lab-bench-deep-successors validation, 2026-11-20",
    "claim1_releases": {
        "distinct_seqqa_parquets_on_hf": 7,
        "distinct_item_contents": 6,
        "note": "983956ce (live 2024-07-13 to 2024-07-16, sha 09c7b26e) has the same 600 items, keys and options as 7268767a; only the canary string differs",
        "per_release": rel,
        "orf_transeff_kmer_rule_all_releases": {"value": 0.5, "p": 0.001, "chance": 0.25, "n": 40},
        "re_seq_lenfrags_2024_partial_cue": {"J3": 0.6375, "J3_p": 0.001, "set_rule_post_hoc": v5},
        "hand_read": {"n": 40, "called_centre": 25, "called_centre_correct": 25, "no_centre_seen": 15,
                      "detail": "10 regenerated 2025-02 PCR enzyme items, 8 numfrags (5 from 2024, 3 from 2025), 7 lenfrags (4 from 2024, 3 from 2025), 6 Gibson, 4 geneprimers-enz, 3 seq-primers, 2 transeff"},
    },
    "claim2_curated_subset": {"n": cur["n"], "ids_in_parent_pin": cur["ids_in_parent_pin"],
                              "keys_identical_text": cur["keys_match_parent"],
                              "note": "ORF-transeff options re-encoded RNA->DNA (U->T) in the curated copy",
                              "per_subtask": {k: {kk: v[kk] for kk in ("chance", "J3", "J3_p", "LEV", "LEV_p", "KMER", "KMER_p", "SHA")}
                                              for k, v in cur["per_subtask"].items()},
                              "hfbio_first_commit": "2026-10-26T15:12:53Z (860d9710); text claim in README at c2b04610 (2026-10-26); per-task figures added 2026-10-27 (33e24310)"},
    "claim2_labbench2": v3 | {"mutation_restriction_key_none": "17/20", "unique_ids": 1912,
                              "note": "seqqa2 mutation_restriction asks to pick from a listed enzyme panel (560 cases): a closed candidate list, not lettered options"},
    "claim3_4_human_and_bounds": v2,
    "claim5_peritem_gate": v4,
    "inference": {"calls": 0, "usd": 0.0},
}
(H / "validation.json").write_text(json.dumps(out, indent=1))
print("ok")
