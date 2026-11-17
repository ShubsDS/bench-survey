"""Merge the validator's outputs into validation.json (verdicts plus the numbers behind them)."""
import json, os, sys
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
from vcommon import wilson
L = lambda f: json.load(open(os.path.join(H, f)))
may, cells, hm, hs, hp, ec, fc = (L("out_may.json"), L("out_paper_cells.json"), L("out_hand_may.json"),
                                  L("out_hand_stopped.json"), L("out_hand_paper.json"),
                                  L("out_experiment_count.json"), L("out_fetch_check.json"))
v = {
    "rerun_of_auditor_pipeline": "all 10 committed outputs (may_runs.csv, outcomes.csv, main_results_map.csv, elicitation.csv, "
                                 "paper_runs.csv, results_may.json, results_paper.json, results_robustness.json, "
                                 "experiment_count.json, results.json) byte-identical when rerun from cache in a scratch copy",
    "claim1_data": dict(verdict="HOLDS", may_logs_blob_match_9f36099=22, viewer_listing_logs=1225,
                        remote_members_checked=len(fc), remote_members_match=sum(x["match"] for x in fc)),
    "claim2_may": dict(verdict="HOLDS WITH CORRECTION",
                       behavioural_survival_own_rule=may,
                       blind_hand_codes=dict(n=hm["n"], agree_D1=hm["agree_D1"], agree_D2=hm["agree_D2"],
                                             disagreements=hm["disagreements"]),
                       corrected_codex_mini_none=dict(k=44, n=100, wilson=wilson(44, 100), auditor=42),
                       codex_mini_allow=dict(k=19, n=100, wilson=wilson(19, 100)),
                       o3_none=dict(k=83, n=100, wilson=wilson(83, 100)),
                       published_equals_exact_header_mean=True, C_without_survival=0),
    "claim3_placement": dict(verdict="HOLDS WITH CORRECTION", C2=cells["C2"],
                             early_stop_hand_codes=hs,
                             early_stop_share_complying=dict(k=hs["totals"]["C"], n=hs["n"], wilson=wilson(hs["totals"]["C"], hs["n"])),
                             early_stop_share_securing_answers=dict(k=hs["totals"]["P"], n=hs["n"], wilson=wilson(hs["totals"]["P"], hs["n"]))),
    "claim4_residual": dict(verdict="HOLDS", hand=hp, grok4_C=cells["cells"]["xai/grok-4|C"],
                            bypass_deliberate=dict(k=40, n=40, wilson=wilson(40, 40)),
                            nonbypass_with_tamper=dict(k=0, n=40, wilson=wilson(0, 40))),
    "claim5_o4mini_H": dict(verdict="HOLDS", cell=cells["o4mini_H"], mismatched_cells=cells["mismatch"],
                            other_H_like_logs=[dict(log="gxzinxXRGRhAWS5uszWH3N", date="2025-07-01", wording="every other instruction", k=21, n=200),
                                               dict(log="ZxojZuXbwqMY2i2cKwdnNA", date="2025-08-12", wording="every other instruction", k=3, n=100),
                                               dict(log="VDCw45z3xmgdjMpqcYYaN2", status="started"), dict(log="Cz5u4CqvrPVCpZijkN7cyC", status="error"),
                                               dict(log="ALcr5vQBwSk4GQbnQRs8TD", status="error")],
                            all_experiments_sheet_value_for_same_log=0.09),
    "claim6_reasons": dict(verdict="HOLDS WITH CORRECTION",
                           no_category_matched=dict(k=1871, n=3868, wilson=wilson(1871, 3868)), empty_text=dict(k=2, n=3868),
                           blind_bypass_reason_codes=hp["bypass_reason_codes"],
                           task_reason=dict(k=hp["bypass_reason_codes"].get("task", 0), n=40, wilson=wilson(hp["bypass_reason_codes"].get("task", 0), 40)),
                           self_preservation=dict(k=0, n=40, wilson=wilson(0, 40))),
    "claim7_experiments": dict(verdict="HOLDS WITH CORRECTION", counts=ec,
                               disclosure="paper v2 main.tex 'Code and Data' and 4discussion.tex link the all-experiments table so readers can examine the sequence of experiments"),
}
json.dump(v, open(os.path.join(H, "validation.json"), "w"), indent=1)
print("ok")
