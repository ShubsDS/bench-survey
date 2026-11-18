"""Item samples for the Haiku runs (seed 0, screened items removed). Writes plans/*.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT, RESULTS, load_items  # noqa: E402

TEXT = ["SeqQA", "ProtocolQA", "CloningScenarios", "LitQA2", "SuppQA", "DbQA"]
VISUAL = ["FigQA", "TableQA"]


def sample(df, subset, n, rng, exclude=()):
    ids = sorted(set(df[df.subset == subset].id) - set(exclude))
    if n >= len(ids):
        return ids
    return sorted(rng.choice(ids, n, replace=False).tolist())


def main() -> None:
    df = load_items(check=False)
    screen = json.loads((RESULTS / "screen.json").read_text())
    excl = {h["id"] for h in screen["hits"] if h["decision"] == "exclude"}
    df = df[~df.id.isin(excl)]
    out = AUDIT / "plans"
    out.mkdir(exist_ok=True)
    rng = np.random.default_rng(0)
    pilot = {"std": [], "blind": [], "opts": []}
    for s in TEXT:
        pilot["std"] += sample(df, s, 10, rng)
    for s in VISUAL:
        pilot["blind"] += sample(df, s, 10, rng)
    for s in TEXT + VISUAL:
        pilot["opts"] += sample(df, s, 10, rng)
    (out / "pilot.json").write_text(json.dumps(pilot, indent=0))
    print({k: len(v) for k, v in pilot.items()})

    # main plan, in batches (prereg.md, Budget)
    rng = np.random.default_rng(0)
    edits = json.loads((AUDIT / "data" / "edits.json").read_text())
    edit_ids = sorted(edits)
    seq = df[df.subset == "SeqQA"]
    s_fams = {v["family"] for v in edits.values()}
    seq10 = []
    for st, g in seq.groupby("subtask"):
        pool = sorted(set(g.id) & set(edit_ids)) if st in s_fams else sorted(g.id)
        seq10 += sorted(rng.choice(pool, 10, replace=False).tolist())
    seq_forced = sorted(set(edit_ids) | set(seq10))
    dbqa = []
    for st, g in df[df.subset == "DbQA"].groupby("subtask"):
        dbqa += sorted(rng.choice(sorted(g.id), 6, replace=False).tolist())
    lit = sample(df, "LitQA2", 60, rng)
    supp = sample(df, "SuppQA", 50, rng)
    prot = sample(df, "ProtocolQA", 999, rng)
    clon = sample(df, "CloningScenarios", 999, rng)
    fig = sample(df, "FigQA", 999, rng)
    tab = sample(df, "TableQA", 120, rng)
    batches = {
        "b1_l4": {"forced": seq_forced, "edit": edit_ids},
        "b2_blind": {"blind": fig + tab, "blindf": fig + tab, "last": fig},
        "b3_protclone": {"std": prot + clon, "forced": prot + clon},
        "b4_opts": {"opts": fig + tab + prot + clon + seq10 + lit + supp + dbqa},
        "b5_seqstd": {"std": seq10},
        "b6_lit": {"std": lit + supp + dbqa, "forced": lit + supp + dbqa},
    }
    for k, v in batches.items():
        (out / f"{k}.json").write_text(json.dumps(v, indent=0))
        print(k, {c: len(i) for c, i in v.items()})


if __name__ == "__main__":
    main()
