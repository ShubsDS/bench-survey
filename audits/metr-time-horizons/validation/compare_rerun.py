"""Task A: compare a fresh rerun of the auditor's scripts (in a scratch directory) with the committed
results/*.json. Usage: python -I validation/compare_rerun.py <scratch_dir_with_results/>
Prints every numeric leaf whose relative difference exceeds 1e-9 and writes validation/rerun_diff.json.
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
scratch = pathlib.Path(sys.argv[1])
diffs, n_leaves, missing = [], 0, []


def walk(a, b, path):
    global n_leaves
    if isinstance(a, dict):
        for k in a:
            if k not in b:
                missing.append(path + "/" + str(k))
            else:
                walk(a[k], b[k], path + "/" + str(k))
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append((path, f"len {len(a)}", f"len {len(b)}"))
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]")
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        n_leaves += 1
        if isinstance(b, (int, float)):
            if (math.isnan(a) and math.isnan(b)):
                return
            if abs(a - b) > 1e-9 * max(1.0, abs(a), abs(b)):
                diffs.append((path, a, b))
        else:
            diffs.append((path, a, b))
    else:
        n_leaves += 1
        if a != b:
            diffs.append((path, a, b))


files = sorted(p.name for p in (ROOT / "results").glob("*.json"))
for f in files:
    p2 = scratch / "results" / f
    if not p2.exists():
        missing.append(f)
        continue
    walk(json.loads((ROOT / "results" / f).read_text()), json.loads(p2.read_text()), f)
out = dict(files=files, leaves_compared=n_leaves, n_diffs=len(diffs), diffs=diffs[:200], missing=missing)
(ROOT / "validation" / "rerun_diff.json").write_text(json.dumps(out, indent=1, default=str))
print(n_leaves, "leaves;", len(diffs), "differ;", "missing:", missing)
for d in diffs[:60]:
    print(d)
