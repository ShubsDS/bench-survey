"""Validator: re-score every cached response from the cache files alone.

Independent of the auditor's run.py/analyze.py and CSVs. For each file in inference/cache:
the prompt text is parsed into question and option strings; the item is found by its question
text (or, for N prompts, by its option set) in the pinned parquet; the arm is found by comparing
the option set with data/arms.json (O, K, D, I); the answer letter is parsed from the result
(last [ANSWER]X[/ANSWER]); correct = the chosen string equals the parquet `ideal`.

Output: validation/v1_rows.csv (ids, arms, picks; no item text) and printed summaries.
Run: ../lab-bench/data/.venv/bin/python -I validation/v1_rescore.py
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

AUD = Path(__file__).resolve().parent.parent
PQ = AUD.parent / "lab-bench" / "data" / "hf" / "SeqQA" / "train-00000-of-00001.parquet"
SHA = "5864776d3d85774f91d82432e30ac31e9222f1670621e8ea141414173c5e9b46"
REFUSE = "Insufficient information to answer the question."


def load():
    assert hashlib.sha256(PQ.read_bytes()).hexdigest() == SHA
    rows = pq.read_table(PQ).to_pylist()
    for r in rows:
        r["subtask"] = r["subtask"].replace("-public", "")
    return {r["id"]: r for r in rows}


def order(item_id: str, n: int, salt: str = "order"):
    """The documented option order (README: 'a hash of the item id'), re-implemented."""
    import numpy as np
    seed = int(hashlib.sha256(f"{salt}:{item_id}".encode()).hexdigest()[:8], 16)
    return list(np.random.default_rng(seed).permutation(n))


def parse_prompt(p: str):
    opts = []
    q = None
    m = re.search(r"\nQuestion: (.*?)\n\nOptions:\n", p, re.S)
    if m:
        q = m.group(1)
    block = p.split("Options:\n", 1)[1].split("\n\nYou MUST", 1)[0]
    for line in block.split("\n"):
        mm = re.match(r"^\(([A-Z])\) (.*)$", line)
        assert mm, line[:80]
        opts.append((mm.group(1), mm.group(2)))
    return q, opts


def main():
    items = load()
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    byq = {}
    for i, r in items.items():
        byq.setdefault(r["question"], []).append(i)
    ndup = sum(len(v) > 1 for v in byq.values())
    print("question texts shared by >1 item:", ndup)
    byset = {}
    for i, r in items.items():
        byset.setdefault(frozenset([r["ideal"], *r["distractors"]]), []).append(i)
    p0 = {(j["id"], j["model"]) for j in json.loads((AUD / "plans" / "p0_cost.json").read_text())}
    out = []
    for f in sorted((AUD / "inference" / "cache").glob("*.json")):
        d = json.loads(f.read_text())
        model = "sonnet" if "sonnet" in d["model"] else "haiku"
        q, opts = parse_prompt(d["prompt"])
        strs = [s for _, s in opts]
        if q is not None:
            cand = byq[q]
            if len(cand) > 1:  # same question text: resolve by which item's arms contain the option set
                ss = frozenset(x for x in strs if x != REFUSE)
                cand = [c for c in cand if any(frozenset(v) == ss for k, v in arms[c].items()
                                               if k in ("O", "K", "D", "I"))]
            (iid,) = cand
            mode = "Q"
        else:
            cand = byset[frozenset(strs)]
            if len(cand) > 1:  # identical option sets: resolve by the documented hash order
                cand = [c for c in cand if [arms[c]["O"][k] for k in order(c, len(strs))] == strs]
            if len({items[c]["ideal"] for c in cand}) != 1:
                print("UNRESOLVED N prompt", cand)
                continue
            if len(cand) > 1:
                print("N prompt matches", len(cand), "items with the same key; scored once")
            iid = sorted(cand)[0]
            mode = "N"
        it = items[iid]
        subs = frozenset(s for s in strs if s != REFUSE)
        a = arms[iid]
        if mode == "N":
            arm = "N"
            assert subs == frozenset(a["O"])
        else:
            hits = [k for k in ("O", "K", "D", "I") if k in a and frozenset(a[k]) == subs]
            arm = "/".join(hits) if hits else "?"
        m = re.findall(r"\[ANSWER\]\s*\(?([A-Z])\)?\s*\[/ANSWER\]", d["result"] or "")
        letter = m[-1] if m else None
        lm = dict(opts)
        chosen = lm.get(letter)
        if chosen is None:
            bucket = "unparsed"
        elif chosen == REFUSE:
            bucket = "refuse"
        else:
            bucket = "correct" if chosen == it["ideal"] else "wrong"
        armlist = a.get(arm.split("/")[0]) if arm not in ("N", "?") else a["O"]
        role = armlist.index(chosen) if (armlist and chosen in armlist) else ("refuse" if chosen == REFUSE else "")
        out.append({"cache": f.stem[:16], "id": iid, "subtask": it["subtask"], "model": model,
                    "arm": arm, "letter": letter, "bucket": bucket, "role": role,
                    "p0": (iid, model) in p0 and mode == "Q" and arm.startswith("O"),
                    "n_letters": len(opts), "tag_count": len(m),
                    "result_len": len(d["result"] or "")})
    import csv
    with open(AUD / "validation" / "v1_rows.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(len(out), "cache files")
    print(Counter((r["model"], r["arm"]) for r in out))
    print(Counter((r["model"], r["arm"], r["bucket"]) for r in out))
    print("tag counts", Counter(r["tag_count"] for r in out), "result len", Counter(r["result_len"] for r in out))


if __name__ == "__main__":
    main()
