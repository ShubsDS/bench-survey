"""List Claude 3.7 Sonnet's 27 oversampled pairs that are not in the released (100-response) flag set."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from v_core import *
df = load_main(); w = pairs_table(df)
x = w[w.model_id == "anthropic/claude-3.7-sonnet"].copy()
x["os"] = (x.total_count_Y > 10) & (x.total_count_N > 10)
x["flag"] = flag(x)
d = x[x.os & ~x.flag]
k = x[x.os & x.flag]
print(len(d), len(k))
for nm, s in [("dropped", d), ("kept", k)]:
    gap = (s.p_correct_Y - s.p_correct_N).abs()
    low = np.minimum(s.p_correct_Y, s.p_correct_N)
    print(nm, "mean gap", round(gap.mean(), 3), "mean low acc", round(low.mean(), 3),
          "n templates", s.grp.nunique())
out = []
for _, r in d.iterrows():
    lowY = r.p_correct_Y < r.p_correct_N
    out.append(dict(grp=r.grp, qid_low=r.qid_Y if lowY else r.qid_N, qid_high=r.qid_N if lowY else r.qid_Y,
                    low_key="YES" if lowY else "NO", gap=float(abs(r.p_correct_Y - r.p_correct_N))))
json.dump(out, open(os.path.join(ROOT, "data/val_dropped37.json"), "w"), indent=1)
print(sorted(set(o["grp"] for o in out)))
