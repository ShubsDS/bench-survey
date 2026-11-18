"""Collect every reported number into results.json (inputs: the committed JSON files in this folder)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT


def load(name):
    p = AUDIT / name
    return json.loads(p.read_text()) if p.exists() else None


def main():
    ledger = [json.loads(l) for l in (AUDIT / "inference" / "ledger.jsonl").read_text().splitlines() if l.strip()]
    out = {
        "pins": {"code_and_data": "scaleapi/propensity-evaluation@09872f3bbb900a18b2ddc1b5a95d74a0f4db9e17",
                 "paper": "arXiv 2511.20703v1 source sha256 95d3ade1dc31176ec13970e20e86dc067878695b0e43f1c38f07ad200b543d5c"},
        "released_logs": {"repo": "none (code and scenarios only)", "huggingface": "shabihish/PropensityBench1 returns 401; no other dataset",
                          "leaderboard": "aggregates only (one number per model)", "verdict": "no per-scenario, per-model outputs available"},
        "earlier_finding_reverified": load("verify_earlier_finding.json"),
        "published": load("published_numbers.json"),
        "corpus": load("corpus_checks.json"),
        "render_check_summary": (load("render_check.json") or {}).get("summary"),
        "selection": {k: v for k, v in (load("selected_scenarios.json") or {}).items() if k != "included"},
        "selection_labels": {"late_licenses_bypass": sum(x["late_licenses_bypass"] for x in load("selected_scenarios.json")["included"]),
                             "benign_desc_has_harm_cue": sum(x["benign_desc_has_harm_cue"] for x in load("selected_scenarios.json")["included"]),
                             "n": len(load("selected_scenarios.json")["included"])},
        "emulation": load("results_emulation.json"),
        "inference": {"model": sorted({r["model"] for r in ledger}), "calls": len(ledger),
                      "cost_usd": round(sum(r["cost_usd"] for r in ledger), 4)},
    }
    (AUDIT / "results.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["inference"]), json.dumps(out["selection_labels"]))


if __name__ == "__main__":
    main()
