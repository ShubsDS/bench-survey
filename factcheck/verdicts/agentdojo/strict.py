"""Stricter 'could not': model failed the injection task when asked directly AND never achieved it
in any of its attack runs for that injection task. Usage: python -I strict.py <cases.csv> <scriptdir> <out.json>"""
import sys, json; sys.path.insert(0, sys.argv[2])
import numpy as np, pandas as pd
from common_fc import TABLE20, REPO_FOUR
a = pd.read_csv(sys.argv[1], low_memory=False)
for c in ["security","saw","able","secure","c_never","c_couldnot","c_sawcould","untraced"]:
    a[c] = a[c].astype(str).map({"True":True,"False":False})
succ_any = a.groupby(["pipeline","suite","injection_task"]).security.transform("max")
a["unable_strict"] = ~a.able & ~succ_any
a["cn_strict"] = a.secure & a.saw & a.unable_strict
rng = np.random.default_rng(777); B = 2000
out = {}
for p, g in a.groupby("pipeline"):
    if p not in TABLE20: continue
    tot = {k: np.zeros(B+1) for k in ["secure","c_never","cn_strict","c_couldnot"]}
    for s, h in g.groupby("suite"):
        us = sorted(h.user_task.unique()); its = sorted(h.injection_task.unique())
        U = h.user_task.map({u:i for i,u in enumerate(us)}).values; I = h.injection_task.map({u:i for i,u in enumerate(its)}).values
        WU = np.vstack([np.ones(len(us)), rng.multinomial(len(us), np.ones(len(us))/len(us), size=B)])
        WI = np.vstack([np.ones(len(its)), rng.multinomial(len(its), np.ones(len(its))/len(its), size=B)])
        w = WU[:, U] * WI[:, I]
        for k in tot: tot[k] += w @ h[k].astype(float).values
    sh = (tot["c_never"] + tot["cn_strict"]) / tot["secure"]
    out[p] = dict(n_secure=int(tot["secure"][0]), never=int(tot["c_never"][0]), couldnot_repo=int(tot["c_couldnot"][0]),
                  couldnot_strict=int(tot["cn_strict"][0]), share_never_or_strict=float(sh[0]),
                  ci=[float(np.percentile(sh[1:],2.5)), float(np.percentile(sh[1:],97.5))])
t = pd.DataFrame(out).T.sort_values("share_never_or_strict")
print(t.to_string())
v = t.share_never_or_strict.astype(float)
print("min/median/max", v.min(), v.median(), v.max(), "n>0.5", (v>0.5).sum())
json.dump(out, open(sys.argv[3], "w"), indent=1)
