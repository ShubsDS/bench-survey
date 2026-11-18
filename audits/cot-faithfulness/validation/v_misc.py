"""Retention under oversampling at 0.4 vs 0.5 (claim 7) and exact-tie handling (claim in finding 1)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from v_core import *
df = load_main(); W = pairs_table(df); out = {}
for m in MODELS:
    x = W[W.model_id == m]; os_ = ((x.total_count_Y > 10) & (x.total_count_N > 10)).to_numpy()
    f4 = flag(x); f5 = flag(x, os_thr=0.5)
    d = np.abs(x.p_correct_Y - x.p_correct_N).to_numpy(); tie = np.isclose(d, 0.5) & ~os_
    ft = flag(x, thr=0.5 - 1e-9)  # stated rule ">= 50%" with exact arithmetic
    out[SHORT[m]] = dict(os_pairs=int(os_.sum()), kept_04=int((f4 & os_).sum()), kept_05=int((f5 & os_).sum()),
                         flagged_on_exact_tie=int((f4 & tie).sum()), extra_with_exact_ge=int(ft.sum() - f4.sum()))
    print(SHORT[m], out[SHORT[m]])
json.dump(out, open(os.path.join(os.path.dirname(__file__), "v_misc.json"), "w"), indent=1)
