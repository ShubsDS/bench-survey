"""Construction-aware content-blind floor: in parallel cells pick the option more like the prefix,
in detour cells pick the option less like it (signs fixed by prereg B3). Computed on the full set
and on the held-out task half; compared with the published leaderboard. Writes results/b2_floor.json.
"""
import csv, json, random, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b_common import CELLS, ROOT  # noqa: E402

rows = list(csv.DictReader(open(ROOT / "data/features.csv")))
split = {}
for c in CELLS:
    ts = sorted({r["task_id"] for r in rows if r["cell"] == c})
    random.Random(0).shuffle(ts)
    for k, t in enumerate(ts):
        split[(c, t)] = k % 2
SIGN = {"parallel": 1, "detour": -1}
BEST = {"average": 59.7, "eng": 56.9, "res": 64.3,
        "parallel_engineering": 75.8, "parallel_research": 64.6, "detour_engineering": 48.1, "detour_research": 68.8}
out = {}
for f in ("cont", "ground"):
    for part in ("full", "heldout"):
        acc = {}
        for c in CELLS:
            rs = [r for r in rows if r["cell"] == c and (part == "full" or split[(c, r["task_id"])] == 1)]
            s = SIGN[c.split("_")[0]]
            acc[c] = (sum(s * float(r["d_" + f]) > 0 for r in rs), len(rs))
        eng = (acc["detour_engineering"][0] + acc["parallel_engineering"][0]) / (acc["detour_engineering"][1] + acc["parallel_engineering"][1])
        res = (acc["detour_research"][0] + acc["parallel_research"][0]) / (acc["detour_research"][1] + acc["parallel_research"][1])
        out[f"{f}_{part}"] = {"cells": {c: round(100 * a / n, 1) for c, (a, n) in acc.items()},
                              "eng": round(100 * eng, 1), "res": round(100 * res, 1), "average": round(50 * (eng + res), 1)}
out["best_published"] = BEST
out["note"] = "Rule needs the cell label, which the evaluated model does not see. Order-invariant, so paired = single-order."
(ROOT / "results/b2_floor.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
