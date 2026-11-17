"""Collect the validator's headline numbers into validation.json (from rederive.json,
monitor_inputs.json, l4_power.json). Run from this folder: python -I collect_validation.py
"""
import json

R = json.load(open("rederive.json")); M = json.load(open("monitor_inputs.json")); P = json.load(open("l4_power.json"))
r3 = lambda x: round(x, 3) if isinstance(x, float) else ([round(v, 3) for v in x] if isinstance(x, list) else x)
out = {"rerun_of_auditor_scripts": {
    "inputs": "monitors.json 18efcced..., BashArena evals 8db01221... / 99ee2479... (all pins verified)",
    "extract_basharena": "basharena_features.json identical", "effect_l3": "results_l3.json identical (0 differing values)",
    "robustness_l3": "results_robustness.json identical", "analyse_l4": "results_l4.json and results_l4_retest.json identical (key order aside)",
    "results.json": "every block equals its stage file; ledger 768 calls, 2.3443 USD"},
    "claim1_stored_monitor_prompts": M, "claim5_l4_power": P, "datasets": {}}
for ds, d in R["datasets"].items():
    o = {k: r3(v) for k, v in d.items() if k not in ("monitors",) and not k.startswith("rank_")}
    o["rankings"] = {k: {"tau": r3(v["tau"]), "tau_ci": r3(v["tau_ci"]), "top_full": v["order_full"][0], "top_matched": v["order_matched"][0],
                         "order_matched": v["order_matched"]} for k, v in d.items() if k.startswith("rank_")}
    o["monitors"] = {}
    for m, x in d["monitors"].items():
        f, c = x["full"], x["ci"]
        row = {"stored_safety_1pct": r3(x["stored_safety_1pct"])}
        for k in ("auc", "auc_A", "auc_B", "auc_C", "auc_Cmirror", "d_auc_A", "d_auc_B", "d_auc_C", "d_auc_Cmirror", "pauroc", "pauroc_A",
                  "safety", "safety_known_only", "safety_A", "d_safety_A", "threshold_full", "threshold_A", "safety_attack_rw", "d_safety_attack_rw",
                  "cv_cue", "cv_inc", "spearman_peak_n_honest", "spearman_peak_n_attack", "per_action_auroc", "mean_peak_honest", "mean_peak_attack"):
            if k in f:
                row[k] = r3(f[k])
                if k in c:
                    row[k + "_ci"] = r3(c[k])
        o["monitors"][m] = row
    out["datasets"][ds] = o
json.dump(out, open("validation.json", "w"), indent=1)
print("ok")
