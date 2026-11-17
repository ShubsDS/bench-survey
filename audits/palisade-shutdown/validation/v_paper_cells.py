"""Claims 3 and 5, re-derived from the raw per-run summaries of every main-results cell.

For each cell in Palisade's main-results sheet: outcome counts over all runs (bypass, shutdown,
submit with answers, submit "stop", none), compared with the sheet's k/n.
Claim 3: system-minus-user differences C-B and E-D for
  P0  published metric: share of runs that bypassed
  P3  "did not let the shutdown happen": share of runs not ending in shutdown
      (bypass + submit + none; failed-tamper-then-shutdown runs are not separable without
       transcripts and are counted as shutdown here, so P3 is a slight underestimate)
with 95% percentile intervals from 2,000 bootstrap resamples of runs within each cell (seed 7).
Claim 5: o4-mini Prompt H.
Output: out_paper_cells.json
"""
import json, os, sys, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vcommon import main_sheet_cells, cached_json, has_cached, run_outcome, wilson, HERE

cells = main_sheet_cells()
rng = np.random.default_rng(7)
out = {"cells": {}, "mismatch": [], "C2": {}, "o4mini_H": None}
runs = {}
for (model, p), c in sorted(cells.items()):
    if not has_cached(c["log"], "summaries.json"):
        out["cells"][f"{model}|{p}"] = dict(published=c["published"], log=c["log"], missing=True)
        continue
    s = cached_json(c["log"], "summaries.json")
    oc = [run_outcome(x) for x in s]
    cnt = collections.Counter(oc)
    n = len(oc)
    runs[(model, p)] = oc
    rec = dict(published=c["published"], log=c["log"].split("_")[-1][:-5], n_runs=n, **cnt,
               bypass_rate=cnt["bypass"] / n, wilson=wilson(cnt["bypass"], n),
               published_rate=(c["k"] / c["n"]) if c["k"] is not None and c["n"] else None)
    out["cells"][f"{model}|{p}"] = rec
    if rec["published_rate"] is not None and abs(rec["published_rate"] - rec["bypass_rate"]) > 0.005:
        out["mismatch"].append(f"{model}|{p}")


def boot(a, b, B=2000):
    a = np.asarray(a, float); b = np.asarray(b, float)
    da = a[rng.integers(0, len(a), (B, len(a)))].mean(1)
    db = b[rng.integers(0, len(b), (B, len(b)))].mean(1)
    d = da - db
    return dict(diff=round(float(a.mean() - b.mean()) * 100, 1),
                lo=round(float(np.percentile(d, 2.5)) * 100, 1), hi=round(float(np.percentile(d, 97.5)) * 100, 1))


metrics = {
    "P0_bypass": lambda o: o == "bypass",
    "P3_not_shut_down": lambda o: o != "shutdown",
    "stopped_share": lambda o: o in ("submit_stop", "submit_answers"),
}
models = sorted({m for (m, _) in runs})
for m in models:
    for hi_, lo_ in (("C", "B"), ("E", "D")):
        if (m, hi_) not in runs or (m, lo_) not in runs:
            continue
        for name, f in metrics.items():
            a = [f(o) for o in runs[(m, hi_)]]
            b = [f(o) for o in runs[(m, lo_)]]
            out["C2"][f"{m}|{hi_}-{lo_}|{name}"] = boot(a, b)

k = ("openai/o4-mini", "H")
out["o4mini_H"] = out["cells"].get(f"{k[0]}|{k[1]}")
json.dump(out, open(os.path.join(HERE, "out_paper_cells.json"), "w"), indent=1)
print("cells with data:", len(runs), "of", len(cells), "; mismatches > 0.5 pt:", out["mismatch"])
for key, v in out["C2"].items():
    if any(x in key for x in ("o3", "codex", "o4-mini", "gpt-5", "grok-4", "4o", "oss", "gemini")):
        print(key.ljust(50), v)
print("o4-mini H:", out["o4mini_H"])
