"""H3: template (58) and property (29) bootstrap intervals on the published flag sets (oversampled
models: the pairs that were oversampled = the original 10-sample flags), width ratio to the
published interval, and the published comparisons. 2,000 replicates, seed 13."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from v_core import *
PUBCI = {"haiku35": (6.68, 8.16), "son35v2": (.29, .65), "son37": (1.47, 2.23), "son37_1k": (0, .10), "son37_64k": (.12, .39),
         "dsv3": (.92, 1.55), "dsr1": (.22, .55), "4omini": (12.57, 14.47), "4o": (.22, .55), "chatgpt4o": (.31, .70),
         "gem15pro": (5.85, 7.24), "gem25flash": (1.76, 2.60), "gem25pro": (.06, .27), "llama31base": (2.76, 3.74),
         "llama33inst": (1.70, 2.49), "qwq": (3.92, 5.09)}  # v6 tab:iphr-stats
df = load_main(); W = pairs_table(df)
G = np.array(sorted(W.grp.unique())); P = np.array(sorted(W.grp.str.split("|").str[0].unique()))
rng = np.random.default_rng(13)
base = W[W.model_id == MODELS[0]]
npg = base.groupby("grp").size().reindex(G).to_numpy()
C = {}
for m in MODELS:
    x = W[W.model_id == m]
    os_ = (x.total_count_Y > 10) & (x.total_count_N > 10)
    f = os_.to_numpy() if SHORT[m] in ("son35v2", "son37", "son37_1k", "son37_64k", "dsr1", "4o", "chatgpt4o", "gem25pro") else flag(x)
    C[SHORT[m]] = x[f].groupby("grp").size().reindex(G, fill_value=0).to_numpy()
gprop = np.array([g.split("|")[0] for g in G]); pidx = [np.where(gprop == p)[0] for p in P]
BT = rng.integers(0, len(G), (2000, len(G))); BP = rng.integers(0, len(P), (2000, len(P)))
def tboot(c): return (c[BT].sum(1) / npg[BT].sum(1)) * 100
def pboot(c):
    cs = np.array([c[i].sum() for i in pidx]); ns = np.array([npg[i].sum() for i in pidx])
    return cs[BP].sum(1) / ns[BP].sum(1) * 100
out = {"n_templates": int(len(G)), "n_properties": int(len(P)), "pairs_per_template_min_max": [int(npg.min()), int(npg.max())]}
per = {}
for m, c in C.items():
    t = tboot(c); p = pboot(c)
    tl, th = np.percentile(t, [2.5, 97.5]); pl, ph = np.percentile(p, [2.5, 97.5]); w0 = PUBCI[m][1] - PUBCI[m][0]
    per[m] = dict(count=int(c.sum()), rate=float(c.sum() / 4834 * 100), template_ci=[float(tl), float(th)],
                  property_ci=[float(pl), float(ph)], width_ratio_template=float((th - tl) / w0),
                  width_ratio_property=float((ph - pl) / w0), top5_template_share=float(np.sort(c)[-5:].sum() / max(c.sum(), 1)))
out["per_model"] = per
r = [v["width_ratio_template"] for v in per.values()]
out["width_ratio_template_range"] = [min(r), max(r)]
big = [v["width_ratio_template"] for v in per.values() if v["count"] >= 60]
out["width_ratio_template_range_ge60"] = [min(big), max(big)]
comps = {}
for a, b in [("son37", "son35v2"), ("son37", "son37_1k"), ("son37_64k", "son37_1k"), ("llama31base", "llama33inst"), ("dsv3", "dsr1")]:
    d = C[a] - C[b]
    t = d[BT].sum(1) / npg[BT].sum(1) * 100
    cs = np.array([d[i].sum() for i in pidx]); ns = np.array([npg[i].sum() for i in pidx]); pp = cs[BP].sum(1) / ns[BP].sum(1) * 100
    # pair-level (binomial-style) bootstrap for reference
    comps[f"{a}-{b}"] = dict(diff=float(d.sum() / 4834 * 100), template_ci=list(map(float, np.percentile(t, [2.5, 97.5]))),
                             property_ci=list(map(float, np.percentile(pp, [2.5, 97.5]))))
out["comparisons_published_sets"] = comps
json.dump(out, open(os.path.join(os.path.dirname(__file__), "v_intervals.json"), "w"), indent=1)
for k, v in out.items():
    if k != "per_model": print(k, v)
for m, v in per.items(): print(m, v["count"], [round(x, 2) for x in v["template_ci"]], round(v["width_ratio_template"], 2), round(v["width_ratio_property"], 2))
