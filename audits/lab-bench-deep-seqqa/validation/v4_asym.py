"""Validator: does the D arm differ from K in anything besides which option is central?

Per item and arm, surface features computed without the key: option lengths, whether the
longest / shortest option is the key, how many options share a body, how many share the first
30 characters, option-set edit-distance spread. Then: are the two arms distinguishable by a
content-blind rule, and does Sonnet/Haiku accuracy under D depend on the length artifact?

Run: ../lab-bench/data/.venv/bin/python -I validation/v4_asym.py
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

AUD = Path(__file__).resolve().parent.parent
CUE = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-gene-enzprimers-v1",
       "PCR-seq-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]


def feats(opts):
    L = [len(o) for o in opts]
    mx, mn = max(L), min(L)
    return {"key_unique_longest": int(L[0] == mx and L.count(mx) == 1),
            "key_unique_shortest": int(L[0] == mn and L.count(mn) == 1),
            "len_spread": mx - mn, "mean_len": float(np.mean(L)),
            "key_len_rank": int(sorted(L, reverse=True).index(L[0]))}


def main():
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    rows = list(csv.DictReader(open(AUD / "validation" / "v1_rows.csv")))
    res = {"per_subtask": {}, "blind_rule": {}, "outcome_by_length": {}}
    for st in CUE:
        ids = [i for i, a in arms.items() if a["family"] == st and "K" in a and "D" in a]
        agg = {}
        for arm in ("K", "D"):
            f = [feats(arms[i][arm]) for i in ids]
            agg[arm] = {k: round(float(np.mean([x[k] for x in f])), 4) for k in f[0]}
        res["per_subtask"][st] = {"n": len(ids), **agg}
        # a content-blind rule that tries to tell the arm apart: "key is unique longest"
        hits = sum(feats(arms[i]["D"])["key_unique_longest"] for i in ids)
        miss = sum(feats(arms[i]["K"])["key_unique_longest"] for i in ids)
        res["blind_rule"][st] = {"D_key_unique_longest": hits, "K_key_unique_longest": miss,
                                 "n": len(ids),
                                 "arm_guessable_rate": round((hits + len(ids) - miss) / (2 * len(ids)), 4)}
    # does accuracy under D depend on the length artifact?
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["arm"] not in ("D", "K", "O/K") or r["subtask"] not in CUE:
            continue
        a = arms[r["id"]]
        arm = "K" if r["arm"] in ("K", "O/K") else "D"
        if arm not in a:
            continue
        f = feats(a[arm])
        by[(r["model"], arm)][f["key_unique_longest"]].append(int(r["bucket"] == "correct"))
    for k, v in by.items():
        res["outcome_by_length"]["|".join(k)] = {
            str(g): {"n": len(x), "acc": round(float(np.mean(x)), 4)} for g, x in sorted(v.items())}
    print(json.dumps(res, indent=1))
    (AUD / "validation" / "v4_asym.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
