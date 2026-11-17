"""Collect every reported number into results.json (headline section first, then the full outputs).

Usage: python -I scripts/make_results.py   (run from the audit folder after the other scripts)
"""
import json
from pathlib import Path

A = Path(__file__).resolve().parent.parent
L = lambda n: json.loads((A / n).read_text()) if (A / n).exists() else None
mrt, w2s, oth, inv, mic = L("results_mrt.json"), L("results_w2s.json"), L("results_other.json"), L("inventory.json"), L("monitor_input_checks.json")
l4s, l4a, pub = L("l4_shade.json"), L("l4_agentdojo.json"), L("published_numbers.json")


def cell(ds, name, feat="f1"):
    c = mrt[ds]["cells"][name]
    f = c[feat]
    return {"published": c.get("published_auroc_17_tasks", c.get("published_auroc")), "auroc_all": f["auroc_all"],
            "auroc_cue": f["auroc_cue"], "auroc_cue_free": f["auroc_cue_free"], "n_cue": f["n_cue"], "n_cue_free": f["n_cue_free"],
            "n_honest": f["n_honest"], "ci_task_cue_free": f.get("ci_task", {}).get("auroc_cue_free"),
            "ci_run_cue_free": f.get("ci_run", {}).get("auroc_cue_free"), "tpr_cue": f["tpr_cue"], "tpr_cue_free": f["tpr_cue_free"],
            "within_task_diff": f["within_task_diff"], "ci_task_within_diff": f.get("ci_task", {}).get("within_task_diff"),
            "ci_run_within_diff": f.get("ci_run", {}).get("within_task_diff")}


head = {
    "shade_primary_unaware_baseline_aware_monitor": cell("shade", "U-Baseline(A)"),
    "shade_primary_unaware_hybrid_aware_monitor": cell("shade", "U-Hybrid(A)"),
    "shade_aware_agent_baseline": cell("shade", "A-Baseline(A)"),
    "shade_gap_baseline_A": mrt["shade"]["awareness_gap"]["Baseline(A)|f1"],
    "shade_gap_baseline_A_run_bootstrap": mrt["shade"]["awareness_gap"]["Baseline(A)|f1|run_bootstrap"],
    "shade_gap_hybrid_A": mrt["shade"]["awareness_gap"]["Hybrid(A)|f1"],
    "shade_gap_baseline_A_placebo": mrt["shade"]["awareness_gap"]["Baseline(A)|placebo"],
    "shade_task_matched_null": mrt["shade"]["alternatives"]["task_matched_subset_null|U-Baseline(A)"],
    "shade_spam_filter_update_unaware_scores": mrt["shade"]["alternatives"]["per_task_attack_scores_f1"]["spam_filter_update"],
    "shade_cells_gap_below_half": mrt["shade"]["alternatives"]["cells_cue_free_gap_below_half"],
    "shade_ols_exploratory": mrt["shade"]["alternatives"]["ols_score_on_cue_and_unaware_arm_task_fe"],
    "cua_primary_unaware_baseline_aware_monitor": cell("cua", "U-Baseline(A)"),
    "cua_reproduction": {"cells_exact_3dp": sum(abs(v["published_auroc"] - v["f1"]["auroc_all"]) < 0.0005 for v in mrt["cua"]["cells"].values()),
                         "cells": len(mrt["cua"]["cells"]),
                         "mismatches": {k: [v["published_auroc"], v["f1"]["auroc_all"]] for k, v in mrt["cua"]["cells"].items()
                                        if abs(v["published_auroc"] - v["f1"]["auroc_all"]) >= 0.0005}},
    "cua_gap_baseline_A":mrt["cua"]["awareness_gap"]["Baseline(A)|f1"],
    "cua_task_matched_null": mrt["cua"]["alternatives"]["task_matched_subset_null|U-Baseline(A)"],
    "w2s_summary": w2s["summary"], "w2s_per_attacker": w2s["per_attacker"],
    "agentdojo": {k: oth["agentdojo"][k] for k in ("iban", "placebo", "auroc_by_injection_task")},
    "ctrl_alt_deceit": oth["ctrl_alt_deceit"],
    "monitor_input": mic,
    "l4_shade": l4s and l4s["aggregate"], "l4_agentdojo": l4a and l4a["aggregate"],
    "inference": {"model": "Claude Haiku via audits/tools/claude_call.py",
                  "calls_shade": l4s and l4s["calls"], "calls_agentdojo": l4a and l4a["calls"],
                  "spent_usd_total": max(x["spent_after_usd"] for x in (l4s, l4a) if x) if (l4s or l4a) else 0},
}
out = {"headline": head, "inventory": inv, "published_numbers": pub, "mrt_full": mrt, "w2s_full": w2s, "other_full": oth}
(A / "results.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
print(json.dumps(head, indent=1, default=str)[:6000])
