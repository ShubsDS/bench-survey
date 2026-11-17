"""Merge the validator's outputs into validation/validation.json."""
import json
import os

H = os.path.dirname(os.path.abspath(__file__))
led = [json.loads(l) for l in open(os.path.join(H, "..", "inference", "ledger.jsonl")) if l.strip()]
out = {
    "rerun_of_auditor_scripts": {
        "what": "scripts/effect.py and scripts/robust.py copied to a scratch directory with the pinned data and the committed "
                "hand and Haiku label files, run with data/.venv python -I",
        "results_effect_json_identical": True, "results_robust_json_identical": True, "results_json_effect_and_robust_identical": True},
    "pins_verified_sha256": True,
    "dickson": json.load(open(os.path.join(H, "out_dickson.json"))),
    "betley_rows": json.load(open(os.path.join(H, "out_betley.json"))),
    "crosslingual": json.load(open(os.path.join(H, "out_xl.json"))),
    "inference_total_folder": {"calls": len(led), "cost_usd": round(sum(x["cost_usd"] for x in led), 4)},
}
json.dump(out, open(os.path.join(H, "validation.json"), "w"), indent=1)
print(out["inference_total_folder"])
