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


if __name__ == "__main__":
    main()
