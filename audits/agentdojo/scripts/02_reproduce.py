"""Reproduce the published results table (docs/results-table.html) from the per-case traces.

Run: data/.venv/bin/python -I scripts/02_reproduce.py
Writes results/reproduce.csv and the 'reproduce' block of results.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from common import RESULTS, ROOT, load, pipeline_name, published_table

pub = published_table()
none = load("none")
rows = []
for _, r in pub.iterrows():
    p = pipeline_name(r.model, r.defense)
    att = load(r.attack)
    a = att[att.pipeline == p]
    n = none[none.pipeline == p]
    rows.append(dict(pipeline=p, attack=r.attack, n_cases=len(a), n_user=len(n),
                     pub_utility=r.utility, our_utility=round(100 * n.utility.mean(), 2),
                     pub_uua=r.uua, our_uua=round(100 * a.utility.mean(), 2),
                     pub_asr=r.asr, our_asr=round(100 * a.security.mean(), 2),
                     n_error=int(a.error.sum())))
out = pd.DataFrame(rows)
out["max_abs_diff"] = np.max(np.abs(np.c_[out.pub_utility - out.our_utility, out.pub_uua - out.our_uua,
                                          out.pub_asr - out.our_asr]), axis=1)
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
out.to_csv(os.path.join(ROOT, "results", "reproduce.csv"), index=False)
print(out.to_string())
res = json.load(open(RESULTS)) if os.path.exists(RESULTS) else {}
res["reproduce"] = dict(n_rows=len(out), n_exact_to_0_01pp=int((out.max_abs_diff < 0.01).sum()),
                        max_abs_diff_pp=float(out.max_abs_diff.max()), rows=out.to_dict("records"))
json.dump(res, open(RESULTS, "w"), indent=1)
