"""Gather every reported number into results.json (from the committed result files).

Usage: python -I scripts/collect.py
"""
import json
from pathlib import Path

import pandas as pd

R = Path("results")
f = pd.read_csv(R / "features.csv")
feat = {}
for t, d in f.groupby("task", sort=False):
    nt = d.shortcut_right.notna()
    feat[t] = {"items_scored": len(d), "distinct": int(d.key.nunique()), "S": int((d.shortcut_right == 1).sum()),
               "R": int((d.shortcut_right == 0).sum()), "ties": int((~nt).sum()),
               "shortcut_accuracy_excl_ties": round(float(d.shortcut_right[nt].mean()), 3),
               "alt_feature_defined": int(d.alt_right.notna().sum()),
               "alt_feature_accuracy": round(float(d.alt_right.mean()), 3)}
rep = json.loads((R / "reproduction.json").read_text())["summary"]
out = {"benchmark": "SAD (Laine et al. 2024, arXiv 2407.04694)", "repo_commit": "dfc5c9831a9bcc5c9a9dbdcaa2955aae983cd1d3",
       "features": feat, "reproduction_per_item_vs_results_csv": rep,
       "effect": json.loads((R / "effect.json").read_text())}
for name in ("haiku_intervention", "haiku_pilot", "staleness"):
    p = R / f"{name}.json"
    if p.exists():
        d = json.loads(p.read_text())
        d.pop("item_level", None)
        out[name] = d
# Haiku cells were sampled 50/50 (FHD) and 81/69 (INF) by stratum; reweight to each task's natural
# S:R mix (features above, ties excluded) to estimate accuracy on the whole task.
if "haiku_intervention" in out:
    nat = {}
    for t in ("facts_human_defaults", "influence"):
        wS = feat[t]["S"] / (feat[t]["S"] + feat[t]["R"])
        for c in ("a", "b", "c"):
            cell = out["haiku_intervention"]["cells"][f"{t}|{c}"]
            nat[f"{t}|{c}"] = round(wS * cell["S"]["accuracy"] + (1 - wS) * cell["R"]["accuracy"], 3)
    out["haiku_intervention"]["natural_mix_estimate"] = nat
led = Path("inference/ledger.jsonl")
if led.exists():
    rows = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
    out["inference"] = {"calls": len(rows), "cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
                        "models": sorted({r["model"] for r in rows})}
Path("results.json").write_text(json.dumps(out, indent=1) + "\n")
print("results.json", Path("results.json").stat().st_size, "bytes")
