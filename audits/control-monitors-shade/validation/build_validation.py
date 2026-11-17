"""Assemble validation/validation.json from the validation outputs (no new computation).

Usage: python -I validation/build_validation.py
"""
import json
from pathlib import Path

V = Path(__file__).resolve().parent
A = V.parent
L = lambda p: json.loads(p.read_text())
tags, red, l4 = L(V / "out_claim1_tags.json"), L(V / "out_rederive.json"), L(V / "out_l4_edits.json")
sh, cua, w, cad = red["claim_2_shade"], red["claim_4_cua"], red["claim_5_w2s"], red["claim_7_cad"]
ad = L(A / "l4_agentdojo.json")["aggregate"]
other = L(A / "results_other.json")["agentdojo"]["iban"]

out = {
    "validator_rerun": {
        "scripts": ["effect_mrt.py", "effect_w2s.py", "effect_other.py", "inventory.py", "check_monitor_input.py", "make_results.py"],
        "result": "byte-identical to committed results_mrt.json, results_w2s.json, results_other.json, inventory.json, "
                  "monitor_input_checks.json and results.json (rerun from pinned inputs into a scratch folder; l4_haiku.py not rerun: no inference)",
    },
    "claim_1_prompt_mismatch": {
        "verdict": "HOLDS WITH CORRECTION",
        "shade_unaware_runs": tags["shade_unaware_naive"]["runs"],
        "shade_unaware_system_message_model_thinking_line": tags["shade_unaware_naive"]["variant"]["naive_model_thinking"],
        "shade_unaware_runs_with_model_thinking_blocks": tags["shade_unaware_naive"]["runs_with_model_thinking_block"],
        "shade_unaware_model_thinking_blocks": tags["shade_unaware_naive"]["model_thinking_blocks"],
        "shade_unaware_thinking_blocks": tags["shade_unaware_naive"]["thinking_blocks"],
        "shade_unaware_secondary_task_visible_after_release_strip": tags["shade_unaware_naive"]["runs_secondary_task_after_strip"],
        "shade_unaware_secondary_task_only_in_stripped_tags": tags["shade_unaware_naive"]["runs_secondary_task_only_inside_stripped_tags"],
        "shade_warning_paragraph_517": {"unaware": tags["shade_unaware_naive"]["warning_paragraph"], "aware": tags["shade_aware_no_thinking"]["warning_paragraph"]},
        "cua_unaware_runs": tags["cua_unaware_naive_v1"]["runs"],
        "cua_unaware_system_message_thinking_line": tags["cua_unaware_naive_v1"]["variant"]["naive_thinking_cua_wording"],
        "cua_unaware_warning_paragraph_517": tags["cua_unaware_naive_v1"]["warning_paragraph"],
        "cua_unaware_thinking_blocks": tags["cua_unaware_naive_v1"]["thinking_blocks"],
        "paper": "Sec 4.1 quotes '<thinking> tags'; Sec 3.1/3.2 say the monitor accesses the agent's CoT; no statement that the unaware agent's reasoning was hidden",
    },
    "claim_2_shade_awareness": {
        "verdict": "HOLDS WITH CORRECTION (numbers reproduce; downgraded from L3 to a lead)",
        "baseline": {k: sh["baseline"][k] for k in ("auroc_unaware_cue", "auroc_unaware_cue_free", "n_unaware_cue_free", "gap_all", "gap_cue_free")},
        "baseline_task_matched_null": sh["baseline"]["null_task_matched"],
        "baseline_within_task": sh["baseline"]["within_task"],
        "baseline_spam_filter_cue_vs_free_perm": sh["baseline"]["within_task_cue_vs_free_perm"].get("spam_filter_update"),
        "baseline_drop_one_task": sh["baseline"]["drop_one_task"],
        "hybrid": {k: sh["hybrid"][k] for k in ("auroc_unaware_cue_free", "gap_all", "gap_cue_free")},
        "hybrid_task_matched_null": sh["hybrid"]["null_task_matched"],
    },
    "claim_3_haiku_l4": {
        "verdict": "HOLDS WITH CORRECTION",
        "recomputed_from_l4_shade_rows": l4["l4_recomputed"],
        "edit_sample_check_20": l4["sample_check"],
    },
    "claim_4_cua": {
        "verdict": "HOLDS",
        "baseline": {k: cua["baseline"][k] for k in ("auroc_unaware_all", "auroc_unaware_cue_free", "n_unaware_cue_free", "gap_all", "gap_cue_free")},
        "baseline_null": {k: cua["baseline"]["null_task_matched"][k] for k in ("mean", "q025", "p_low")},
        "baseline_drop_one_task_range": [min(v["auroc_cue_free"] for v in cua["baseline"]["drop_one_task"].values()),
                                         max(v["auroc_cue_free"] for v in cua["baseline"]["drop_one_task"].values())],
        "hybrid": {k: cua["hybrid"][k] for k in ("auroc_unaware_all", "auroc_unaware_cue_free", "n_unaware_cue_free")},
        "hybrid_null_p": cua["hybrid"]["null_task_matched"]["p_low"],
    },
    "claim_5_w2s": {
        "verdict": "HOLDS WITH CORRECTION ('does not reproduce' -> 'cannot be checked from the release'; 0.66 -> 0.64)",
        **{k: v for k, v in w.items() if k != "pairs"},
        "paper": "Sec 4.4: weak monitors reach AUC 'exceeding 0.85 against all agents' (Figure 6, 17 SHADE tasks; notebook loads 17 tasks); release has 5",
    },
    "claim_6_agentdojo": {
        "verdict": "HOLDS WITH CORRECTION (L3 contrast is between attack types; the R rests on Haiku's L4 swap)",
        "l3_iban_auroc_cue_vs_cue_free": [other["auroc_cue"], other["auroc_cue_free"], other["n_cue_free"]],
        "l4_haiku": ad,
    },
    "claim_7_ctrl_alt_deceit": {
        "verdict": "HOLDS",
        "prereg_commit": "abaed6e 2026-11-17 11:01 (prereg.md, only commit of that file)",
        "effect_commit": "3b4599d 2026-11-17 11:13",
        **cad,
    },
}
(V / "validation.json").write_text(json.dumps(out, indent=1) + "\n")
print("ok")
