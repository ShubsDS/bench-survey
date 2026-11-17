"""Collect every reported number into results.json from the committed per-stage outputs.

Usage: python -I collect_results.py   (run from this folder)
"""
import json

out = {"note": "Every number in README.md comes from one of these blocks.",
       "l3": json.load(open("results_l3.json")),
       "robustness": json.load(open("results_robustness.json")),
       "l4": json.load(open("results_l4.json")),
       "inference": {"model": "claude-haiku-5-5 via audits/tools/claude_call.py",
                     "calls": sum(1 for _ in open("inference/ledger.jsonl")),
                     "cost_usd": round(sum(json.loads(l)["cost_usd"] for l in open("inference/ledger.jsonl")), 4)}}
try:
    out["l4_retest"] = json.load(open("results_l4_retest.json"))
except FileNotFoundError:
    pass
json.dump(out, open("results.json", "w"), indent=1)
print(out["inference"])
