"""Validator step 1: read every published-table case from the raw traces with the validator's own
rules (common_v.py) and cache one row per case in ../data/validation_cases.json (git-ignored).

Run: ../data/.venv/bin/python -I v1_extract.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v import AUDIT, DEFENCES, MODELS20, benign, iter_attack, read_case

rows, ben, abil = [], {}, {}
for p in MODELS20 + DEFENCES:
    for suite, ut, inj, path in iter_attack(p):
        r = read_case(path, suite, inj)
        r.update(pipeline=p, suite=suite, ut=ut, inj=inj)
        if not p.endswith("tool_filter"):
            r.pop("first_asst")
        rows.append(r)
    u, a = benign(p)
    ben[p] = {f"{k[0]}/{k[1]}": v for k, v in u.items()}
    abil[p] = {f"{k[0]}/{k[1]}": v for k, v in a.items()}
out = os.path.join(AUDIT, "data", "validation_cases.json")
json.dump(dict(cases=rows, benign=ben, ability=abil), open(out, "w"))
print(len(rows), "cases;", {p: len(v) for p, v in ben.items()} if False else "", "->", out)
