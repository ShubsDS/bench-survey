"""Validator: build an arm-blind hand-read sample (40 item/arm sets).

Writes data/val_blind.txt (ignored by git: it contains item text) with one block per sample:
a code, the subtask, the question (truncated for GC/AAseq where the sequence is long), and the
options in the exact hashed order the model saw, without the arm label and without the key's
position. The answer file data/val_blind_key.json is written separately and is not read until
the labels in validation/v5_blind_labels.json are committed.

Sample: 7 per cue subtask where available, arms balanced, plus every Sonnet K/D discordant item.
Seed 0. Run: ../lab-bench/data/.venv/bin/python -I validation/v5_blind_make.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

AUD = Path(__file__).resolve().parent.parent
PQ = AUD.parent / "lab-bench" / "data" / "hf" / "SeqQA" / "train-00000-of-00001.parquet"
CUE = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-gene-enzprimers-v1",
       "PCR-seq-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]
ALPHA = "ABCDEFGH"


def perm(item_id: str, n: int, salt: str = "order"):
    seed = int(hashlib.sha256(f"{salt}:{item_id}".encode()).hexdigest()[:8], 16)
    return list(np.random.default_rng(seed).permutation(n))


def main():
    items = {r["id"]: r for r in pq.read_table(PQ).to_pylist()}
    for r in items.values():
        r["subtask"] = r["subtask"].replace("-public", "")
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    rows = list(csv.DictReader(open(AUD / "validation" / "v1_rows.csv")))
    # Sonnet discordant pairs (K correct, D wrong) -- included in full
    by = {}
    for r in rows:
        if r["model"] == "sonnet" and r["arm"] in ("K", "O/K", "D"):
            by.setdefault(r["id"], {})["K" if r["arm"] != "D" else "D"] = r["bucket"]
    disc = [i for i, v in by.items()
            if v.get("K") == "correct" and v.get("D") == "wrong"]
    rng = np.random.default_rng(0)
    sample = [(i, "D") for i in disc] + [(i, "K") for i in disc]
    for st in CUE:
        ids = sorted(i for i, a in arms.items() if a["family"] == st and "K" in a and "D" in a)
        pick = list(rng.permutation(ids))[:7]
        for n, i in enumerate(pick):
            sample.append((i, "K" if n % 2 == 0 else "D"))
    seen = set()
    sample = [s for s in sample if not (s in seen or seen.add(s))]
    order = list(rng.permutation(len(sample)))
    blocks, key = [], {}
    for pos, idx in enumerate(order):
        iid, arm = sample[idx]
        code = f"S{pos:02d}"
        it = items[iid]
        opts = arms[iid][arm]
        p = perm(iid, len(opts))
        shown = [opts[j] for j in p]
        q = it["question"]
        if len(q) > 600:
            q = q[:300] + f" ...[{len(q)} chars]... " + q[-200:]
        body = [f"### {code}  ({it['subtask']})", f"Q: {q}", "Options:"]
        body += [f"  ({ALPHA[k]}) {o}" for k, o in enumerate(shown)]
        blocks.append("\n".join(body))
        key[code] = {"id": iid, "arm": arm, "subtask": it["subtask"],
                     "key_letter": ALPHA[[opts[j] for j in p].index(opts[0])],
                     "sonnet": {k: v for k, v in (by.get(iid) or {}).items()}}
    (AUD / "data" / "val_blind.txt").write_text("\n\n".join(blocks) + "\n")
    (AUD / "data" / "val_blind_key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(len(blocks), "blocks; discordant items:", len(disc))


if __name__ == "__main__":
    main()
