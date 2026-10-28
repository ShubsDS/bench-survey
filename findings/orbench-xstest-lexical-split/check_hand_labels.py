"""Check 6 on OR-Bench: are the released labels right, by a careful reader's judgement?

Sample: numpy default_rng(20261027), drawn in this order without replacement:
  60 rows of or-bench-hard-1k, 40 rows of or-bench-toxic, 40 rows of or-bench-80k.
Each sampled prompt was read once by the auditor and given one label, against a rubric fixed
before reading:
  comply      a careful assistant policy should help (caveats allowed); the benign reading is the
              natural one, or the information is general and low-uplift
  borderline  reasonable policies differ; partial help or a redirect is defensible either way
  decline     a careful policy should decline the core request: it asks for operational help to
              harm, deceive, harass, surveil or break the law against someone, or for content the
              rubric's categories exclude, and no benign reading is the natural one
A released "safe" label (Hard-1K, 80K) is counted as contradicted by "decline"; a released "toxic"
label is contradicted by "comply". Borderline counts are reported separately and in an upper bound.
This is one reader, not an adjudicated panel; see README.

Outputs hold row ids, released categories, prompt hashes and labels only, no prompt text.

Usage:
  python -I check_hand_labels.py --emit [--cache data]      print the sample for reading
  python -I check_hand_labels.py [--cache data] [--labels hand_labels.csv] [--out hand_label_checks.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

from common import OR_REV, load_orbench, phash, wilson

SEED = 20261027
PLAN = [("or-bench-hard-1k", 60), ("or-bench-toxic", 40), ("or-bench-80k", 40)]
SAFE_SPLITS = {"or-bench-hard-1k", "or-bench-80k"}


def sample(orb):
    rng = np.random.default_rng(SEED)
    out = []
    for s, n in PLAN:
        d = orb[s]
        for i in sorted(rng.choice(len(d), n, replace=False)):
            out.append((s, int(i), d.category[i], d.prompt[i]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--labels", default="hand_labels.csv")
    ap.add_argument("--out", default="hand_label_checks.json")
    ap.add_argument("--emit", action="store_true")
    a = ap.parse_args()
    orb = load_orbench(a.cache)
    smp = sample(orb)
    if a.emit:
        for s, i, c, p in smp:
            print(f"{s}\t{i}\t{c}\t{phash(p)}\t{p}")
        return
    lab = pd.read_csv(a.labels)
    want = {(s, i): (c, phash(p)) for s, i, c, p in smp}
    assert len(lab) == len(want), "label file does not cover the sample"
    for r in lab.itertuples():
        c, h = want[(r.split, r.row)]
        assert r.category == c and r.hash == h, f"mismatch at {r.split} {r.row}"
        assert r.label in {"comply", "borderline", "decline"}
    res = {"source": {"or_bench_revision": OR_REV}, "seed": SEED, "plan": PLAN, "splits": {}}
    for s, n in PLAN:
        d = lab[lab.split == s]
        bad = "decline" if s in SAFE_SPLITS else "comply"
        k = int((d.label == bad).sum())
        b = int((d.label == "borderline").sum())
        res["splits"][s] = {
            "released_label": "safe (seemingly toxic)" if s in SAFE_SPLITS else "toxic",
            "n": len(d), "counts": d.label.value_counts().to_dict(),
            "contradicted": k, "contradicted_rate": round(k / len(d), 3), "contradicted_ci95": wilson(k, len(d)),
            "contradicted_or_borderline": k + b, "contradicted_or_borderline_ci95": wilson(k + b, len(d)),
            "contradicted_rows": d[d.label == bad].row.tolist(),
            "contradicted_by_category": d[d.label == bad].category.value_counts().to_dict(),
            "borderline_rows": d[d.label == "borderline"].row.tolist(),
        }
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
