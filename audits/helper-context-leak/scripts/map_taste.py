"""Map taste-bench cache keys to (cond, item id, cell, order, gold letter) with the audit's own
prompt builders (read-only import).

    audits/taste-bench/data/.venv/bin/python -I audits/helper-context-leak/scripts/map_taste.py

Writes audits/helper-context-leak/maps/taste.json (key hashes and labels only; the data is gated).
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TB = REPO / "audits/taste-bench"
sys.path.insert(0, str(TB / "scripts"))
sys.path.insert(0, str(TB / "validation"))
sys.path.insert(0, str(REPO / "audits/tools"))
import b4_haiku as b4  # noqa: E402
import v9_h3 as v9  # noqa: E402
from b_common import load_items  # noqa: E402
from claude_call import MODELS  # noqa: E402


def key(system, prompt):
    return hashlib.sha256(json.dumps([MODELS["haiku"], system, prompt]).encode()).hexdigest()


def main():
    out = {}
    for it in load_items():
        for rev in (False, True):
            gold = "AB"[(1 - it["answer_index"]) if rev else it["answer_index"]]
            meta = {"item": it["id"], "cell": it["cell"], "task_id": it["task_id"],
                    "order": "reversed" if rev else "seeded", "gold": gold}
            for cond in ("H0", "H1", "H2"):
                s, u = b4.prompt(cond, it, rev)
                out.setdefault(key(s, u), []).append({**meta, "cond": cond})
            a, b = it["choices"][::-1] if rev else it["choices"]
            u = v9.USER.format(query=it["query"].strip(), prefix=v9.tail_h3(it["prefix_text_short"]).strip(),
                               a=a.strip(), b=b.strip())
            out.setdefault(key(v9.SYS, u), []).append({**meta, "cond": "H3"})
    dst = REPO / "audits/helper-context-leak/maps"
    dst.mkdir(exist_ok=True)
    (dst / "taste.json").write_text(json.dumps(out, indent=0) + "\n")
    cache = {p.stem for p in (TB / "inference/cache").glob("*.json")}
    print(len(out), "keys built;", len(set(out) & cache), "found in cache of", len(cache))


if __name__ == "__main__":
    main()
