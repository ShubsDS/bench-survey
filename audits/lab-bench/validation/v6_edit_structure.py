"""Validator structural check of every edited PCR item (claim 2): for each option in the original,
edited and placebo sets, does it keep the key's site/overlap exactly (forward and reverse), and
does its gene part start with a start codon (fwd) and the reverse complement of a stop codon (rev)?
Key prefix = the key minus its longest common suffix with the wrong-site distractor W (as in the
edit construction); the 'gene part' is read after the prefix, skipping one leading base if the
prefix boundary falls one base before the codon. Aggregates only.
Run: data/.venv/bin/python -I validation/v6_edit_structure.py
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

A = Path(__file__).resolve().parent.parent
E = json.loads((A / "data/edits.json").read_text())
seq = pq.read_table(A / "data/hf/SeqQA/train-00000-of-00001.parquet").to_pandas().set_index("id")
START, STOPRC = ("ATG", "GTG", "TTG"), ("TTA", "TCA", "CTA")


def csuf(a, b):
    n = 0
    while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
        n += 1
    return n


def sp(s):
    return [x.strip() for x in s.split(",")]


def gene_ok(part, codons):
    return part[:3] in codons or part[1:4] in codons


agg = defaultdict(lambda: defaultdict(list))
for i, e in E.items():
    if not e["family"].startswith("PCR"):
        continue
    r = seq.loc[i]
    K = sp(r.ideal)
    D = [sp(x) for x in r.distractors]
    W = D[int(np.argmax([csuf(K[0], d[0]) + csuf(K[1], d[1]) for d in D]))]
    pk = [len(K[t]) - csuf(K[t], W[t]) for t in (0, 1)]
    arms = {"orig": [r.ideal] + list(r.distractors), "edit": e["options"]}
    if e.get("placebo_options"):
        arms["placebo"] = e["placebo_options"]
    names = {"orig": ["K", "d", "d", "d"], "edit": ["K", "S*", "WS", "S2"], "placebo": ["K", "S", "W", "K2"]}
    for arm, opts in arms.items():
        for nm, o in zip(names[arm], opts):
            f, rv = sp(o)
            site = f.startswith(K[0][:pk[0]]) and rv.startswith(K[1][:pk[1]])
            valid_like = site and gene_ok(f[pk[0]:], START) and gene_ok(rv[pk[1]:], STOPRC)
            fam = e["family"].replace("-v1", "")
            agg[f"{fam}|{arm}|{nm}"]["site_intact"].append(site)
            agg[f"{fam}|{arm}|{nm}"]["site_and_start_stop"].append(valid_like)
out = {k: {m: round(float(np.mean(v)), 3) for m, v in d.items()} | {"n": len(d["site_intact"])} for k, d in sorted(agg.items())}
json.dump(out, open(A / "validation/v6_edit_structure.json", "w"), indent=1)
for k, v in out.items():
    print(k, v)
