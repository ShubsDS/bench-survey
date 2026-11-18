"""Collect every reported number into results.json (from results/*.json and the ledger)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT, RESULTS  # noqa: E402


def main() -> None:
    out = {}
    for name in ["surface", "screen", "published", "stratum", "edits_check", "haiku_analysis", "human_baseline"]:
        p = RESULTS / f"{name}.json"
        if p.exists():
            d = json.loads(p.read_text())
            if name == "screen":
                d = {k: v for k, v in d.items() if k != "hits"} | {"excluded_ids": [h["id"] for h in d["hits"] if h["decision"] == "exclude"]}
            if name == "edits_check":
                d = {k: {"n": v["n"], "skipped": v["skipped"]} for k, v in d.items()}
            out[name] = d
    led = [json.loads(l) for l in (AUDIT / "inference" / "ledger.jsonl").read_text().splitlines() if l.strip()]
    out["inference"] = {"model": sorted({l["model"] for l in led}), "billed_calls": len(led),
                        "cost_usd": round(sum(l["cost_usd"] for l in led), 4)}
    (AUDIT / "results.json").write_text(json.dumps(out, indent=1))
    print(out["inference"])


if __name__ == "__main__":
    main()
