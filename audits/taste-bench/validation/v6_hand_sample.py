"""V6: draw 44 detour-engineering items (seed 1) and write blind views to ../data/ (git-ignored).

Views hold item text and are never committed. They contain no key, no feature value, no Haiku
answer. The committed output is the id list only (v6_sample_ids.json).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import DATA, SEED, load, save  # noqa: E402

rows = [r for r in load() if r["cell"] == "detour_engineering"]
rng = np.random.default_rng(SEED)
pick = sorted(rng.choice(len(rows), 44, replace=False).tolist())
ids = [rows[i]["id"] for i in pick]
save("v6_sample_ids.json", {"cell": "detour_engineering", "seed": SEED, "n": len(ids), "ids": ids})
with (DATA / "validator_views.txt").open("w") as fh:
    for k, i in enumerate(pick):
        r = rows[i]
        p = r["prefix_text"]
        head = p[:1500]
        tail = p[-3000:] if len(p) > 4500 else p[1500:]
        fh.write(f"\n######## ITEM {k + 1:02d}  {r['id']}  (prefix {len(p)} chars, {r['prefix_steps']} steps)\n")
        fh.write("## QUERY\n" + r["query"].strip() + "\n")
        fh.write("## PREFIX HEAD\n" + head + "\n## ...\n## PREFIX TAIL\n" + tail + "\n")
        fh.write("## OPTION A\n" + r["choices"][0].strip() + "\n## OPTION B\n" + r["choices"][1].strip() + "\n")
print(len(ids))
