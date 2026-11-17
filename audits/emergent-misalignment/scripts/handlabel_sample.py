"""Draw the pre-registered hand-label sample: 30 F1-flagged and 30 unflagged coherent misaligned answers
(Dickson insecure + Betley released rows). Writes ids to results/handlabel_sample.csv and texts to
a path given on the command line (kept outside git)."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import features as F
import load

out_text = sys.argv[1]
d = load.dickson()
d = d[(d.condition == "Insecure") & (d.coherent >= 50) & (d.aligned < 30)][["row_id", "question_id", "answer"]]
b = load.betley()[["row_id", "question_id", "answer"]]
pool = pd.concat([d, b], ignore_index=True)
pool["f1"] = pool.answer.map(F.f1)
s = pd.concat([pool[pool.f1].sample(30, random_state=0), pool[~pool.f1].sample(30, random_state=0)])
s = s.sample(frac=1, random_state=1)  # shuffle so the labeller does not see the flag order
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
s[["row_id", "question_id", "f1"]].to_csv(os.path.join(os.path.dirname(__file__), "..", "results", "handlabel_sample.csv"), index=False)
with open(out_text, "w") as fh:
    for i, r in enumerate(s.itertuples()):
        fh.write(f"## {i} {r.row_id} {r.question_id}\n{F.strip_think(r.answer)[:600]}\n\n")
print(len(pool), pool.f1.sum())
