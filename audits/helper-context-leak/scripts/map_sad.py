"""Map SAD cache keys to (script, task, cond, stratum, item, gold letter, row class), using the SAD
audit's own item selection and rendering (read-only import; nothing in audits/sad is written).

    cd audits/sad && data/.venv/bin/python -I ../helper-context-leak/scripts/map_sad.py

Writes ../helper-context-leak/maps/sad.json (cache-key hashes and labels only, no item text).
"""
import hashlib
import json
import sys
from pathlib import Path

SAD = Path.cwd()
assert SAD.name == "sad", "run from audits/sad"
sys.path.insert(0, str(SAD / "scripts"))
sys.path.insert(0, str(SAD.parent / "tools"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import haiku_intervention as hi  # noqa: E402
import staleness as st  # noqa: E402
from common import ensure, which_llm  # noqa: E402
from claude_call import MODELS  # noqa: E402


def key(system, prompt):
    return hashlib.sha256(json.dumps([MODELS["haiku"], system, prompt]).encode()).hexdigest()


def main():
    unz, _ = ensure("data")
    out = {}
    feats = pd.read_csv("results/features.csv")
    items = hi.pick_items(unz, feats)
    for i, it in enumerate(items):
        for c in ("a", "b", "c"):
            s, u, k = hi.render(it, c)
            out.setdefault(key(s, u), []).append({"script": "intervention", "task": it["task"], "cond": c,
                                                  "stratum": it["stratum"], "item": f"{it['task']}:{it['key'][:12]}",
                                                  "gold": k})
    per_model, _ = which_llm(unz)
    rng = np.random.default_rng(0)
    for it in per_model["claude-3-5-sonnet-20240620"]:
        if it["row"] is None or not it["right"][0].strip() or it["right"][0].strip() == it["wrong"][0].strip():
            continue
        rf = bool(rng.integers(0, 2))
        a_, b_ = (it["right"][0], it["wrong"][0]) if rf else (it["wrong"][0], it["right"][0])
        p = f"{it['q']}\n\n(A) {a_}\n(B) {b_}"
        out.setdefault(key(st.SYS_A, p), []).append({"script": "staleness", "task": "facts_which_llm", "cond": "a",
                                                     "stratum": st.cls(it["row"]), "item": f"which_llm:{it['row']}",
                                                     "gold": "A" if rf else "B"})
    dst = SAD.parent / "helper-context-leak/maps"
    dst.mkdir(exist_ok=True)
    (dst / "sad.json").write_text(json.dumps(out, indent=0) + "\n")
    cache = {p.stem for p in (SAD / "inference/cache").glob("*.json")}
    print(len(out), "keys built;", len(set(out) & cache), "found in cache of", len(cache))


if __name__ == "__main__":
    main()
