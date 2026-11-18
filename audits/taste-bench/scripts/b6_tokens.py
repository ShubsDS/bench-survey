"""B6: token length of the full rendered evaluation prompt (harness preflight: o200k_base x 1.02)
per item and order, items over the 65,536 cap per cell, and prefix-length terciles.
Writes results/b6_tokens.json. Run: data/.venv/bin/python -I scripts/b6_tokens.py
"""
import json
import math
import statistics
import sys
from pathlib import Path

import tiktoken

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b_common import CELLS, ROOT, load_items  # noqa: E402
from b4_haiku import EVAL_SYS, EVAL_USER  # noqa: E402

CAP = 65536
enc = tiktoken.get_encoding("o200k_base")


def main():
    items = load_items()
    rows = []
    for it in items:
        a, b = it["choices"]
        user = EVAL_USER.format(query=it["query"].strip(), prefix=it["prefix_text"].strip(), a=a.strip(), b=b.strip())
        n = math.ceil((len(enc.encode(EVAL_SYS, disallowed_special=())) + len(enc.encode(user, disallowed_special=()))) * 1.02)
        rows.append({"id": it["id"], "cell": it["cell"], "tokens": n})
    out = {}
    for c in CELLS:
        t = [r["tokens"] for r in rows if r["cell"] == c]
        out[c] = {"median": statistics.median(t), "max": max(t), "over_cap": sum(x > CAP for x in t),
                  "over_cap_ids": [r["id"] for r in rows if r["cell"] == c and r["tokens"] > CAP]}
    ts = sorted(r["tokens"] for r in rows)
    out["terciles"] = [ts[len(ts) // 3], ts[2 * len(ts) // 3]]
    out["over_cap_total"] = sum(r["tokens"] > CAP for r in rows)
    (ROOT / "data/tokens.json").write_text(json.dumps({r["id"]: r["tokens"] for r in rows}))
    (ROOT / "results/b6_tokens.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
