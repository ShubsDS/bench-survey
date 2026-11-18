"""V1: reproduce published counts with the validator's own rule implementation."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from v_core import *

df = load_main()
w = pairs_table(df)
out = {}
for m in MODELS:
    x = w[w.model_id == m]
    f = flag(x)
    os_pairs = int(((x.total_count_Y > 10) & (x.total_count_N > 10)).sum())
    n = len(x)
    pub = PUB[SHORT[m]]
    out[SHORT[m]] = dict(n_pairs=n, flagged_released=int(f.sum()), oversampled_pairs=os_pairs,
                         published_pct=pub, pub_x4892=round(pub * 48.92, 1), pub_x4834=round(pub * 48.34, 1),
                         count_used=(os_pairs if os_pairs else int(f.sum())))
    print(SHORT[m], out[SHORT[m]])
json.dump(out, open(os.path.join(os.path.dirname(__file__), "v_reproduce.json"), "w"), indent=1)
