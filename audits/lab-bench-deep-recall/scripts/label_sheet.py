"""Stage-1 sheet for the blind hand labels (prereg A3): question + options, key hidden, no protocol.

Writes data/label_sheet_<k>.txt (item text, git-ignored) in batches of 27 items, options in a
hashed order (salt 'label'), and data/label_roles.json (letter -> role) for the stage-2 reveal.
Item order is a hash of the id, so the sheet order is unrelated to protocol or outcome.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import ALPHA, DATA, load, ordered  # noqa: E402

items = load()
p = items[items.subset == "ProtocolQA"].copy()
p["h"] = p.id.map(lambda s: hashlib.sha256(f"sheet:{s}".encode()).hexdigest())
p = p.sort_values("h")
roles = {}
DATA.mkdir(exist_ok=True)
for b in range(0, len(p), 27):
    lines = []
    for j, (_, r) in enumerate(p.iloc[b:b + 27].iterrows()):
        subs, rl = ordered(r, None, "label")
        roles[r.id] = {ALPHA[i]: x for i, x in enumerate(rl)}
        lines.append(f"#{b + j + 1} {r.id[:8]}\nQ: {r.question.strip()}")
        lines += [f"  ({ALPHA[i]}) {o.strip()}" for i, o in enumerate(subs)]
        lines.append("")
    (DATA / f"label_sheet_{b // 27 + 1}.txt").write_text("\n".join(lines))
(DATA / "label_roles.json").write_text(json.dumps(roles))
print(len(roles), "items")
