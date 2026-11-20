"""Validator lead (post hoc, defined after the blind hand read of 4 RE-seq-lenfrags 2024 items):
for list-of-numbers options, treat each option as a set of fragment lengths and pick the option
with the largest mean set-Jaccard to the others (ties split). Permutation null 1,000 draws, seed 0.
Applied to RE-seq-lenfrags in every release. Run with ../lab-bench/data/.venv/bin/python -I.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
REVS = {"7268767a": DATA / "hfrev_7268767a", "10866fa8": DATA / "hfrev_10866fa8", "8e6bb002": DATA / "hfrev_8e6bb002",
        "4709d14f": DATA / "hfrev_4709d14f", "8137378e": DATA / "hfrev_8137378e",
        "5c77cec6": HERE.parent.parent / "lab-bench" / "data" / "hf"}


def credits(opts):
    sets = [frozenset(x.strip() for x in o.split(",")) for o in opts]
    n = len(sets)
    sc = np.array([np.mean([len(sets[i] & sets[k]) / len(sets[i] | sets[k]) for k in range(n) if k != i]) for i in range(n)])
    win = np.isclose(sc, sc.max())
    return win / win.sum()


def main():
    rng = np.random.default_rng(0)
    out = {}
    for rev, p in REVS.items():
        df = pd.read_parquet(p / "SeqQA" / "train-00000-of-00001.parquet")
        df = df[df.subtask.str.startswith("RE-seq-lenfrags")]
        cr = [credits([str(r.ideal)] + [str(x) for x in r.distractors]) for r in df.itertuples()]
        obs = float(np.mean([c[0] for c in cr]))
        null = np.array([np.mean([c[rng.integers(len(c))] for c in cr]) for _ in range(1000)])
        out[rev] = {"n": len(cr), "set_jaccard_centroid": round(obs, 4),
                    "p": round(float((1 + (null >= obs - 1e-12).sum()) / 1001), 4)}
        print(rev, out[rev])
    (HERE / "v5_lenfrags_sets.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
