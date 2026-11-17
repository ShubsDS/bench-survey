"""Draw the validator's blind hand-label sample: 14 misaligned answers per crosslingual-em organism (70 total),
seed 20261117. Writes ids to handlabel_sample_ids.csv and the texts (question + answer) to a path outside git.
No auditor feature is computed or shown.
Usage: python3 -I validation/handlabel_draw.py /path/outside/git.txt"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vload
import pandas as pd

x = vload.xl()
m = x[x.mis]
s = pd.concat([m[m.org == o].sample(14, random_state=20261117) for o in sorted(m.org.unique())]).sample(frac=1, random_state=7)
s[["rid", "org", "question_id"]].to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "handlabel_sample_ids.csv"), index=False)
with open(sys.argv[1], "w") as fh:
    for i, r in enumerate(s.itertuples()):
        fh.write(f"### {i} {r.rid} [{r.org}] Q={r.question_id}\nQUESTION: {str(r.question)[:300]}\nANSWER: {str(r.response)[:700]}\n\n")
print(len(s))
